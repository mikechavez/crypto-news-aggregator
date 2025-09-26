import asyncio
import logging
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Iterable, List, Sequence

from ..services.rss_service import RSSService
from ..db.operations.articles import create_or_update_articles
from ..llm.factory import get_llm_provider
from ..db.mongodb import mongo_manager

logger = logging.getLogger(__name__)

_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "this",
    "that",
    "from",
    "have",
    "will",
    "into",
    "been",
    "after",
    "their",
    "about",
    "there",
    "would",
    "could",
    "should",
    "while",
    "where",
    "which",
    "among",
    "using",
    "against",
    "across",
    "still",
    "other",
    "between",
    "taking",
    "because",
    "until",
    "during",
    "under",
    "whose",
    "however",
    "today",
    "yesterday",
    "tomorrow",
    "news",
    "crypto",
    "cryptocurrency",
    "market",
    "markets",
    "price",
}

_MAX_KEYWORDS = 10


async def fetch_and_process_rss_feeds():
    """Fetches RSS feeds, processes articles, and stores them."""
    rss_service = RSSService()
    articles = await rss_service.fetch_all_feeds()
    await create_or_update_articles(articles)
    
    # Run LLM analysis on the newly fetched articles
    await process_new_articles_from_mongodb()


def _tokenize_for_keywords(text: str) -> Iterable[str]:
    for token in re.findall(r"\b[A-Za-z][A-Za-z0-9\-\$]{2,}\b", text):
        lowered = token.lower()
        if lowered in _STOPWORDS:
            continue
        if lowered.isdigit():
            continue
        yield token.strip("$#")


def _select_keywords(tokens: Sequence[str], max_keywords: int = _MAX_KEYWORDS) -> List[str]:
    if not tokens:
        return []
    counter = Counter(tokens)
    sorted_tokens = sorted(counter.items(), key=lambda item: (-item[1], item[0].lower()))
    keywords: List[str] = []
    for word, _ in sorted_tokens:
        normalized = word.upper() if word.isupper() else word.title()
        if normalized not in keywords:
            keywords.append(normalized)
        if len(keywords) >= max_keywords:
            break
    return keywords


def _derive_sentiment_label(score: float) -> str:
    """Derive sentiment label from sentiment score."""
    if score is None:
        return "neutral"
    if score >= 0.4:
        return "positive"
    if score <= -0.4:
        return "negative"
    return "neutral"


async def process_new_articles_from_mongodb():
    """Analyzes and enriches new articles from MongoDB that haven't been processed yet."""
    db = await mongo_manager.get_async_database()
    collection = db.articles
    llm_client = get_llm_provider()

enrichment_query = {
        '': [
            {'relevance_score': {'': False}},
            {'relevance_score': None},
            {'relevance_score': 0.0},
            {'sentiment_score': {'': False}},
            {'sentiment_score': None},
            {'sentiment_score': 0.0},
            {'sentiment': {'': False}},
        ]
    }

    new_articles = collection.find(enrichment_query)

    processed = 0
    async for article in new_articles:
        article_id = article.get("_id")
        try:
            title = article.get("title") or ""
            body_parts = [
                article.get("text") or "",
                article.get("content") or "",
                article.get("description") or "",
            ]
            combined_text = " ".join(part.strip() for part in [title, *body_parts] if part).strip()

            if not combined_text:
                logger.debug("Skipping article %s due to missing text", article_id)
                continue

            try:
                relevance_score = float(llm_client.score_relevance(combined_text))
            except Exception as exc:
                logger.warning("Relevance scoring failed for %s: %s", article_id, exc)
                relevance_score = 0.0

            try:
                sentiment_score = float(llm_client.analyze_sentiment(combined_text))
            except Exception as exc:
                logger.warning("Sentiment analysis failed for %s: %s", article_id, exc)
                sentiment_score = 0.0

            try:
                extracted_themes = llm_client.extract_themes([combined_text])
                themes: List[str] = [str(theme) for theme in extracted_themes] if isinstance(extracted_themes, list) else []
            except Exception as exc:
                logger.warning("Theme extraction failed for %s: %s", article_id, exc)
                themes = []

            sentiment_label = _derive_sentiment_label(sentiment_score)


            keyword_tokens = list(_tokenize_for_keywords(combined_text))
            keywords = _select_keywords(keyword_tokens)

            if themes:
                for theme in themes:
                    normalized_theme = theme.strip()
                    if normalized_theme and normalized_theme not in keywords:
                        keywords.append(normalized_theme)
                        if len(keywords) >= _MAX_KEYWORDS:
                            break

            sentiment_payload = {
                "score": sentiment_score,
                "magnitude": abs(sentiment_score),
                "label": sentiment_label,
                "provider": str(getattr(llm_client, "model_name", llm_client.__class__.__name__)),
                "updated_at": datetime.now(timezone.utc),
            }

            update_operations = {
                "$set": {
                    "relevance_score": relevance_score,
                    "sentiment_score": sentiment_score,
                    "sentiment_label": sentiment_label,
                    "sentiment": sentiment_payload,
                    "themes": themes,
                    "keywords": keywords,
                    "updated_at": datetime.now(timezone.utc),
                }
            }

            await collection.update_one({"_id": article_id}, update_operations)
            processed += 1
        except Exception as exc:
            logger.exception("Failed to enrich article %s: %s", article_id, exc)

    if processed:
        logger.info("Enriched %s article(s) with sentiment, themes, and keywords", processed)

    return processed


async def schedule_rss_fetch(interval_seconds: int) -> None:
    """Continuously run the RSS fetcher on a fixed interval."""
    logger.info("Starting RSS fetcher schedule with interval %s seconds", interval_seconds)
    while True:
        try:
            await fetch_and_process_rss_feeds()
            logger.info("RSS ingestion cycle completed")
        except asyncio.CancelledError:
            logger.info("RSS fetcher schedule cancelled")
            raise
        except Exception as exc:
            logger.exception("RSS ingestion cycle failed: %s", exc)
        await asyncio.sleep(interval_seconds)
