import asyncio
import logging
from typing import List
from ..services.rss_service import RSSService
from ..db.operations.articles import create_or_update_articles
from ..llm.factory import get_llm_provider
from ..db.mongodb import mongo_manager

logger = logging.getLogger(__name__)


async def fetch_and_process_rss_feeds():
    """Fetches RSS feeds, processes articles, and stores them."""
    rss_service = RSSService()
    articles = await rss_service.fetch_all_feeds()
    await create_or_update_articles(articles)
    
    # Run LLM analysis on the newly fetched articles
    await process_new_articles_from_mongodb()


async def process_new_articles_from_mongodb():
    """Analyzes new articles from MongoDB that haven't been processed yet."""
    db = await mongo_manager.get_async_database()
    collection = db.articles
    llm_client = get_llm_provider()
    # Find articles that need analysis
    new_articles = collection.find({"relevance_score": None})

    async for article in new_articles:
        try:
            title = article.get("title") or ""
            text = article.get("text") or ""
            combined_text = f"{title}. {text}".strip()

            if not combined_text:
                logger.debug("Skipping article %s due to missing text", article.get("_id"))
                continue

            relevance_score = llm_client.score_relevance(combined_text)
            sentiment_score = llm_client.analyze_sentiment(combined_text)
            themes: List[str] = llm_client.extract_themes([combined_text])

            if not isinstance(themes, list):
                themes = []

            sentiment_label = _derive_sentiment_label(sentiment_score)

            await collection.update_one(
                {"_id": article["_id"]},
                {"$set": {
                    "relevance_score": relevance_score,
                    "sentiment_score": sentiment_score,
                    "sentiment_label": sentiment_label,
                    "themes": themes,
                }}
            )
        except Exception as exc:
            logger.exception("Failed to enrich article %s: %s", article.get("_id"), exc)


def _derive_sentiment_label(score: float) -> str:
    if score is None:
        return "neutral"
    if score >= 0.4:
        return "positive"
    if score <= -0.4:
        return "negative"
    return "neutral"


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
