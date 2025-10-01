import asyncio
import logging
import re
import time
from collections import Counter
from datetime import datetime, timezone
from typing import Iterable, List, Sequence, Dict, Any, Optional

from ..services.rss_service import RSSService
from ..db.operations.articles import create_or_update_articles
from ..db.operations.entity_mentions import create_entity_mentions_batch
from ..llm.factory import get_llm_provider
from ..db.mongodb import mongo_manager
from ..core.config import settings

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


def _select_keywords(
    tokens: Sequence[str], max_keywords: int = _MAX_KEYWORDS
) -> List[str]:
    if not tokens:
        return []
    counter = Counter(tokens)
    sorted_tokens = sorted(
        counter.items(), key=lambda item: (-item[1], item[0].lower())
    )
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


def _normalize_entity(entity_value: str, entity_type: str) -> str:
    """Normalize entity values for consistency.

    Args:
        entity_value: Raw entity value from extraction
        entity_type: Type of entity (ticker, project, event)

    Returns:
        Normalized entity value
    """
    if not entity_value:
        return entity_value

    # Normalize tickers to uppercase
    if entity_type == "ticker":
        # Ensure $ prefix and uppercase
        if not entity_value.startswith("$"):
            entity_value = f"${entity_value}"
        return entity_value.upper()

    # Normalize project names to title case
    if entity_type == "project":
        # Common crypto project names that should be capitalized
        canonical_names = {
            "bitcoin": "Bitcoin",
            "ethereum": "Ethereum",
            "solana": "Solana",
            "cardano": "Cardano",
            "polkadot": "Polkadot",
            "avalanche": "Avalanche",
            "polygon": "Polygon",
            "chainlink": "Chainlink",
            "uniswap": "Uniswap",
            "aave": "Aave",
        }
        lower_value = entity_value.lower()
        if lower_value in canonical_names:
            return canonical_names[lower_value]
        # Default to title case
        return entity_value.title()

    # Normalize event types to lowercase
    if entity_type == "event":
        return entity_value.lower()

    return entity_value


def _deduplicate_entities(entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deduplicate entities, keeping highest confidence for duplicates.

    Args:
        entities: List of entity dicts with type, value, confidence

    Returns:
        Deduplicated list of entities
    """
    # Group by (type, normalized_value)
    entity_map = {}

    for entity in entities:
        entity_type = entity.get("type")
        entity_value = entity.get("value")
        confidence = entity.get("confidence", 1.0)

        # Normalize the value
        normalized_value = _normalize_entity(entity_value, entity_type)
        key = (entity_type, normalized_value)

        # Keep entity with highest confidence
        if key not in entity_map or confidence > entity_map[key]["confidence"]:
            entity_map[key] = {
                "type": entity_type,
                "value": normalized_value,
                "confidence": confidence,
            }

    return list(entity_map.values())


async def _process_entity_extraction_batch(
    articles_batch: List[Dict[str, Any]], llm_client, retry_individual: bool = True
) -> Dict[str, Any]:
    """
    Processes a batch of articles for entity extraction with partial failure handling.

    Args:
        articles_batch: List of article dicts with _id, title, and text
        llm_client: LLM provider instance
        retry_individual: If True, retry failed articles individually

    Returns:
        Dict with extraction results, usage stats, and metrics
    """
    if not articles_batch:
        return {
            "results": [],
            "usage": {},
            "metrics": {"articles_processed": 0, "entities_extracted": 0},
        }

    start_time = time.time()

    # Prepare articles for batch processing
    batch_input = []
    article_id_map = {}

    for article in articles_batch:
        article_id = str(article.get("_id"))
        title = article.get("title") or ""
        body_parts = [
            article.get("text") or "",
            article.get("content") or "",
            article.get("description") or "",
        ]
        combined_text = " ".join(part.strip() for part in body_parts if part).strip()

        # Truncate text if too long (keep first 2000 chars)
        if len(combined_text) > 2000:
            combined_text = combined_text[:2000] + "..."

        batch_input.append(
            {
                "id": article_id,
                "title": title,
                "text": combined_text,
            }
        )
        article_id_map[article_id] = article

    # Call batch entity extraction
    try:
        result = llm_client.extract_entities_batch(batch_input)

        # Normalize and deduplicate entities in results
        for article_result in result.get("results", []):
            if "entities" in article_result:
                article_result["entities"] = _deduplicate_entities(
                    article_result["entities"]
                )

        processing_time = time.time() - start_time

        # Calculate metrics
        total_entities = sum(
            len(r.get("entities", [])) for r in result.get("results", [])
        )
        result["metrics"] = {
            "articles_processed": len(result.get("results", [])),
            "entities_extracted": total_entities,
            "processing_time": processing_time,
        }

        return result

    except Exception as exc:
        logger.exception("Batch entity extraction failed: %s", exc)

        # If retry_individual is enabled, try processing articles one by one
        if retry_individual and len(articles_batch) > 1:
            logger.info(
                "Retrying %d articles individually after batch failure",
                len(articles_batch),
            )
            return await _retry_individual_extractions(
                articles_batch, llm_client, start_time
            )

        return {
            "results": [],
            "usage": {},
            "metrics": {"articles_processed": 0, "entities_extracted": 0},
        }


async def _retry_individual_extractions(
    articles_batch: List[Dict[str, Any]], llm_client, start_time: float
) -> Dict[str, Any]:
    """
    Retry failed articles individually.

    Args:
        articles_batch: List of article dicts
        llm_client: LLM provider instance
        start_time: Start time of the original batch

    Returns:
        Combined results from individual extractions
    """
    all_results = []
    total_usage = {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "input_cost": 0.0,
        "output_cost": 0.0,
        "total_cost": 0.0,
    }
    failed_articles = []

    for article in articles_batch:
        article_id = str(article.get("_id"))
        try:
            # Process single article
            result = await _process_entity_extraction_batch(
                [article], llm_client, retry_individual=False
            )

            if result.get("results"):
                all_results.extend(result["results"])

                # Aggregate usage
                usage = result.get("usage", {})
                for key in total_usage:
                    total_usage[key] += usage.get(key, 0)
            else:
                failed_articles.append(article_id)
                logger.warning(
                    "Individual extraction failed for article %s", article_id
                )

        except Exception as exc:
            failed_articles.append(article_id)
            logger.error(
                "Individual extraction failed for article %s: %s", article_id, exc
            )

    processing_time = time.time() - start_time
    total_entities = sum(len(r.get("entities", [])) for r in all_results)

    if failed_articles:
        logger.warning(
            "Failed to extract entities from %d articles: %s",
            len(failed_articles),
            ", ".join(failed_articles[:5]),
        )

    return {
        "results": all_results,
        "usage": total_usage,
        "metrics": {
            "articles_processed": len(all_results),
            "entities_extracted": total_entities,
            "processing_time": processing_time,
            "failed_articles": failed_articles,
        },
    }


async def process_new_articles_from_mongodb():
    """Analyzes and enriches new articles from MongoDB that haven't been processed yet."""
    db = await mongo_manager.get_async_database()
    collection = db.articles
    llm_client = get_llm_provider()

    enrichment_query = {
        "$or": [
            {"relevance_score": {"$exists": False}},
            {"relevance_score": None},
            {"relevance_score": 0.0},
            {"sentiment_score": {"$exists": False}},
            {"sentiment_score": None},
            {"sentiment_score": 0.0},
            {"sentiment": {"$exists": False}},
        ]
    }

    # Collect articles into batches for entity extraction
    articles_list = []
    async for article in collection.find(enrichment_query):
        articles_list.append(article)

    if not articles_list:
        logger.debug("No articles to enrich")
        return 0

    # Process entity extraction in batches
    batch_size = settings.ENTITY_EXTRACTION_BATCH_SIZE
    total_entity_cost = 0.0
    entity_extraction_results = {}

    for i in range(0, len(articles_list), batch_size):
        batch = articles_list[i : i + batch_size]
        logger.info(
            "Processing entity extraction batch %d-%d of %d articles",
            i,
            min(i + batch_size, len(articles_list)),
            len(articles_list),
        )

        extraction_result = await _process_entity_extraction_batch(batch, llm_client)

        # Log usage stats and metrics
        usage = extraction_result.get("usage", {})
        metrics = extraction_result.get("metrics", {})

        if usage:
            batch_cost = usage.get("total_cost", 0.0)
            total_entity_cost += batch_cost

            # Log comprehensive batch metrics
            logger.info(
                "Batch metrics: articles_processed=%d, entities_extracted=%d, "
                "cost_per_batch=$%.6f, processing_time=%.2fs",
                metrics.get("articles_processed", 0),
                metrics.get("entities_extracted", 0),
                batch_cost,
                metrics.get("processing_time", 0.0),
            )

            logger.info(
                "Token usage: model=%s, input=%d, output=%d, total=%d",
                usage.get("model", "unknown"),
                usage.get("input_tokens", 0),
                usage.get("output_tokens", 0),
                usage.get("total_tokens", 0),
            )

            # Log any failed articles
            failed = metrics.get("failed_articles", [])
            if failed:
                logger.warning("Failed articles in batch: %s", ", ".join(failed[:10]))

        # Map results by article_id
        for result in extraction_result.get("results", []):
            article_id = result.get("article_id")
            if article_id:
                entity_extraction_results[article_id] = result

    # Now process articles individually for other enrichments
    processed = 0
    async for article in collection.find(enrichment_query):
        article_id = article.get("_id")
        try:
            title = article.get("title") or ""
            body_parts = [
                article.get("text") or "",
                article.get("content") or "",
                article.get("description") or "",
            ]
            combined_text = " ".join(
                part.strip() for part in [title, *body_parts] if part
            ).strip()

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
                themes: List[str] = (
                    [str(theme) for theme in extracted_themes]
                    if isinstance(extracted_themes, list)
                    else []
                )
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
                "provider": str(
                    getattr(llm_client, "model_name", llm_client.__class__.__name__)
                ),
                "updated_at": datetime.now(timezone.utc),
            }

            # Get entity extraction results for this article
            article_id_str = str(article_id)
            entity_data = entity_extraction_results.get(article_id_str, {})
            entities = entity_data.get("entities", [])
            entity_sentiment = entity_data.get("sentiment", sentiment_label)

            update_operations = {
                "$set": {
                    "relevance_score": relevance_score,
                    "sentiment_score": sentiment_score,
                    "sentiment_label": sentiment_label,
                    "sentiment": sentiment_payload,
                    "themes": themes,
                    "keywords": keywords,
                    "entities": entities,
                    "updated_at": datetime.now(timezone.utc),
                }
            }

            await collection.update_one({"_id": article_id}, update_operations)

            # Create entity mentions for tracking
            if entities:
                mentions_to_create = []
                for entity in entities:
                    mentions_to_create.append(
                        {
                            "entity": entity.get("value"),
                            "entity_type": entity.get("type"),
                            "article_id": article_id_str,
                            "sentiment": entity_sentiment,
                            "confidence": entity.get("confidence", 1.0),
                            "metadata": {
                                "article_title": title,
                                "extraction_batch": True,
                            },
                        }
                    )

                try:
                    await create_entity_mentions_batch(mentions_to_create)
                except Exception as exc:
                    logger.warning(
                        "Failed to create entity mentions for article %s: %s",
                        article_id,
                        exc,
                    )

            processed += 1
        except Exception as exc:
            logger.exception("Failed to enrich article %s: %s", article_id, exc)

    if processed:
        logger.info(
            "Enriched %s article(s) with sentiment, themes, keywords, and entities",
            processed,
        )

    if total_entity_cost > 0:
        logger.info("Total entity extraction cost: $%.6f", total_entity_cost)

    return processed


async def schedule_rss_fetch(interval_seconds: int) -> None:
    """Continuously run the RSS fetcher on a fixed interval."""
    logger.info(
        "Starting RSS fetcher schedule with interval %s seconds", interval_seconds
    )
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
