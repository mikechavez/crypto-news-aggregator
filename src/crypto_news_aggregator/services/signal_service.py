"""
Signal detection service for identifying trending crypto entities.

This service calculates signal scores based on:
- Velocity: Rate of mentions over time
- Source diversity: Number of unique sources mentioning the entity
- Sentiment metrics: Average sentiment and divergence

Note: All entity queries use the entity name as stored in entity_mentions,
which should already be normalized to canonical form by the RSS fetcher.

IMPORTANT: Signal calculations only include mentions from articles with
relevance_tier <= 2 (high and medium signal). Low-signal articles (tier 3)
are excluded to reduce noise.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from bson import ObjectId
from crypto_news_aggregator.db.mongodb import mongo_manager
from crypto_news_aggregator.services.entity_normalization import normalize_entity_name

logger = logging.getLogger(__name__)

# Maximum relevance tier to include in signal calculations
# Tier 1 = high signal, Tier 2 = medium, Tier 3 = low (excluded)
MAX_RELEVANCE_TIER = 2


async def _get_high_signal_article_ids(
    db,
    start_time: datetime = None,
    end_time: datetime = None
) -> set:
    """
    Get article IDs that have relevance_tier <= MAX_RELEVANCE_TIER.

    Args:
        db: Database instance
        start_time: Optional start time filter (published_at)
        end_time: Optional end time filter (published_at)

    Returns:
        Set of article IDs (as strings) that are high/medium signal
    """
    query = {
        "$or": [
            {"relevance_tier": {"$lte": MAX_RELEVANCE_TIER}},
            {"relevance_tier": {"$exists": False}},  # Include unclassified articles
            {"relevance_tier": None},
        ]
    }

    if start_time or end_time:
        time_filter = {}
        if start_time:
            time_filter["$gte"] = start_time
        if end_time:
            time_filter["$lt"] = end_time
        if time_filter:
            query["created_at"] = time_filter

    cursor = db.articles.find(query, {"_id": 1})
    article_ids = set()
    async for doc in cursor:
        article_ids.add(str(doc["_id"]))

    return article_ids


async def _count_filtered_mentions(
    db,
    entity: str,
    start_time: datetime = None,
    end_time: datetime = None,
    high_signal_article_ids: set = None
) -> int:
    """
    Count entity mentions, filtering by relevance tier.

    Args:
        db: Database instance
        entity: Entity to count mentions for
        start_time: Optional start time filter
        end_time: Optional end time filter
        high_signal_article_ids: Pre-fetched set of high-signal article IDs

    Returns:
        Count of mentions from high/medium signal articles
    """
    collection = db.entity_mentions

    # Build base query
    query = {
        "entity": entity,
        "is_primary": True,
    }

    if start_time or end_time:
        time_filter = {}
        if start_time:
            time_filter["$gte"] = start_time
        if end_time:
            time_filter["$lt"] = end_time
        if time_filter:
            query["created_at"] = time_filter

    # If we have a pre-fetched set of article IDs, use it
    if high_signal_article_ids is not None:
        query["article_id"] = {"$in": list(high_signal_article_ids)}
        return await collection.count_documents(query)

    # Otherwise, use aggregation to join and filter
    pipeline = [
        {"$match": query},
        {
            "$lookup": {
                "from": "articles",
                "let": {"article_id": {"$toObjectId": "$article_id"}},
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {"$eq": ["$_id", "$$article_id"]},
                        }
                    },
                    {
                        "$match": {
                            "$or": [
                                {"relevance_tier": {"$lte": MAX_RELEVANCE_TIER}},
                                {"relevance_tier": {"$exists": False}},
                                {"relevance_tier": None},
                            ]
                        }
                    }
                ],
                "as": "article"
            }
        },
        {"$match": {"article": {"$ne": []}}},  # Only keep mentions with matching articles
        {"$count": "total"}
    ]

    result = await collection.aggregate(pipeline).to_list(length=1)
    return result[0]["total"] if result else 0


async def calculate_mentions_and_velocity(entity: str, timeframe_hours: int) -> Dict[str, float]:
    """
    Calculate mention count and velocity (growth rate) for an entity over a timeframe.

    Only includes mentions from high/medium signal articles (relevance_tier <= 2).

    Velocity = (current_period - previous_period) / previous_period * 100
    Example: 50 mentions this week vs 30 last week = (50-30)/30*100 = 67% growth

    Args:
        entity: The entity to calculate metrics for
        timeframe_hours: Timeframe in hours (24, 168 for 7d, 720 for 30d)

    Returns:
        Dict with 'mentions' (count) and 'velocity' (growth rate as percentage, e.g., 67.0 for 67%)
    """
    db = await mongo_manager.get_async_database()

    # MongoDB stores datetimes as UTC but returns them as naive
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    current_period_start = now - timedelta(hours=timeframe_hours)
    previous_period_start = now - timedelta(hours=timeframe_hours * 2)

    # Get high-signal article IDs for the full time range (for efficiency)
    high_signal_ids = await _get_high_signal_article_ids(
        db,
        start_time=previous_period_start
    )

    # Count mentions in current period (primary entities only, high-signal articles only)
    current_mentions = await _count_filtered_mentions(
        db, entity,
        start_time=current_period_start,
        high_signal_article_ids=high_signal_ids
    )

    # Count mentions in previous period (primary entities only, high-signal articles only)
    previous_mentions = await _count_filtered_mentions(
        db, entity,
        start_time=previous_period_start,
        end_time=current_period_start,
        high_signal_article_ids=high_signal_ids
    )

    # Calculate velocity as growth rate percentage
    if previous_mentions == 0:
        # If no previous data, velocity is 100% if we have current mentions, else 0%
        velocity = 100.0 if current_mentions > 0 else 0.0
    else:
        # Growth rate as percentage: (current - previous) / previous * 100
        velocity = ((current_mentions - previous_mentions) / previous_mentions) * 100

    return {
        "mentions": float(current_mentions),
        "velocity": velocity
    }


async def calculate_velocity(entity: str, timeframe_hours: int = 24) -> float:
    """
    Calculate mention velocity for an entity (legacy method for backward compatibility).

    Only includes mentions from high/medium signal articles (relevance_tier <= 2).

    Velocity = (mentions in last 1 hour) / (mentions in last 24 hours / 24)
    This gives us a ratio showing if mentions are accelerating.

    Args:
        entity: The entity to calculate velocity for
        timeframe_hours: Timeframe for baseline calculation (default 24)

    Returns:
        Velocity score (higher = more acceleration)
    """
    db = await mongo_manager.get_async_database()

    # MongoDB stores datetimes as UTC but returns them as naive
    # Use naive datetimes for comparison
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    one_hour_ago = now - timedelta(hours=1)
    timeframe_ago = now - timedelta(hours=timeframe_hours)

    # Get high-signal article IDs for efficiency
    high_signal_ids = await _get_high_signal_article_ids(db, start_time=timeframe_ago)

    # Count mentions in last hour (primary entities only, high-signal only)
    mentions_1h = await _count_filtered_mentions(
        db, entity,
        start_time=one_hour_ago,
        high_signal_article_ids=high_signal_ids
    )

    # Count mentions in full timeframe (primary entities only, high-signal only)
    mentions_timeframe = await _count_filtered_mentions(
        db, entity,
        start_time=timeframe_ago,
        high_signal_article_ids=high_signal_ids
    )

    # Calculate velocity
    if mentions_timeframe == 0:
        # No historical data, return current hour count as baseline
        return float(mentions_1h)

    # Expected mentions per hour based on timeframe average
    expected_per_hour = mentions_timeframe / timeframe_hours

    if expected_per_hour == 0:
        return float(mentions_1h)

    # Velocity ratio: actual vs expected
    velocity = mentions_1h / expected_per_hour

    return velocity


async def calculate_source_diversity(entity: str) -> int:
    """
    Calculate source diversity for an entity.

    Only includes mentions from high/medium signal articles (relevance_tier <= 2).

    Counts the number of unique sources that have mentioned this entity.
    Entity mentions have a 'source' field directly.

    Args:
        entity: The entity to calculate diversity for

    Returns:
        Number of unique sources
    """
    db = await mongo_manager.get_async_database()

    # Get high-signal article IDs
    high_signal_ids = await _get_high_signal_article_ids(db)

    # Use aggregation to get unique sources from high-signal articles only
    pipeline = [
        {
            "$match": {
                "entity": entity,
                "is_primary": True,
                "article_id": {"$in": list(high_signal_ids)} if high_signal_ids else {"$exists": True}
            }
        },
        {
            "$group": {
                "_id": "$source"
            }
        },
        {
            "$count": "unique_sources"
        }
    ]

    result = await db.entity_mentions.aggregate(pipeline).to_list(length=1)
    return result[0]["unique_sources"] if result else 0


async def calculate_sentiment_metrics(entity: str) -> Dict[str, float]:
    """
    Calculate sentiment metrics for an entity.

    Only includes mentions from high/medium signal articles (relevance_tier <= 2).

    Args:
        entity: The entity to calculate sentiment for

    Returns:
        Dict with avg, min, max, and divergence (std deviation approximation)
    """
    db = await mongo_manager.get_async_database()
    collection = db.entity_mentions

    # Get high-signal article IDs
    high_signal_ids = await _get_high_signal_article_ids(db)

    # Map sentiment labels to numeric scores
    sentiment_map = {
        "positive": 1.0,
        "neutral": 0.0,
        "negative": -1.0,
    }

    # Build query with article filter
    query = {"entity": entity, "is_primary": True}
    if high_signal_ids:
        query["article_id"] = {"$in": list(high_signal_ids)}

    # Get all mentions with sentiment (primary mentions only, high-signal only)
    cursor = collection.find(query)

    sentiment_scores = []
    async for mention in cursor:
        sentiment = mention.get("sentiment", "neutral")
        score = sentiment_map.get(sentiment, 0.0)
        sentiment_scores.append(score)

    if not sentiment_scores:
        return {
            "avg": 0.0,
            "min": 0.0,
            "max": 0.0,
            "divergence": 0.0,
        }

    # Calculate metrics
    avg = sum(sentiment_scores) / len(sentiment_scores)
    min_score = min(sentiment_scores)
    max_score = max(sentiment_scores)

    # Calculate divergence (variance approximation)
    variance = sum((x - avg) ** 2 for x in sentiment_scores) / len(sentiment_scores)
    divergence = variance ** 0.5  # Standard deviation

    return {
        "avg": avg,
        "min": min_score,
        "max": max_score,
        "divergence": divergence,
    }


async def get_narratives_for_entity(entity: str) -> list:
    """
    Find all narratives that contain this entity.
    
    Args:
        entity: The entity to search for
    
    Returns:
        List of narrative IDs (as strings)
    """
    db = await mongo_manager.get_async_database()
    collection = db.narratives
    
    # Find narratives where this entity is in the entities array
    cursor = collection.find({"entities": entity})
    
    narrative_ids = []
    async for narrative in cursor:
        narrative_ids.append(str(narrative["_id"]))
    
    return narrative_ids


async def calculate_recency_factor(entity: str, timeframe_hours: int) -> float:
    """
    Calculate recency factor - boost for recent activity.

    Only includes mentions from high/medium signal articles (relevance_tier <= 2).

    Measures what percentage of mentions occurred in the most recent 20% of the timeframe.

    Args:
        entity: The entity to calculate recency for
        timeframe_hours: Timeframe in hours

    Returns:
        Recency factor (0.0 to 1.0)
    """
    db = await mongo_manager.get_async_database()

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    timeframe_start = now - timedelta(hours=timeframe_hours)
    recent_window_hours = timeframe_hours * 0.2  # Most recent 20%
    recent_start = now - timedelta(hours=recent_window_hours)

    # Get high-signal article IDs for the timeframe
    high_signal_ids = await _get_high_signal_article_ids(db, start_time=timeframe_start)

    # Count total mentions in timeframe (high-signal only)
    total_mentions = await _count_filtered_mentions(
        db, entity,
        start_time=timeframe_start,
        high_signal_article_ids=high_signal_ids
    )

    if total_mentions == 0:
        return 0.0

    # Count mentions in recent window (high-signal only)
    recent_mentions = await _count_filtered_mentions(
        db, entity,
        start_time=recent_start,
        high_signal_article_ids=high_signal_ids
    )

    # Recency factor is the proportion of mentions that are recent
    recency = recent_mentions / total_mentions
    return recency


async def calculate_signal_score(
    entity: str,
    timeframe_hours: Optional[int] = None
) -> Dict[str, Any]:
    """
    Calculate overall signal score for an entity.
    
    If timeframe_hours is provided, calculates score for that specific timeframe
    with the new formula:
    - velocity (growth %) × 0.5
    - source_diversity × 0.3
    - recency_factor × 0.2
    
    If timeframe_hours is None, uses legacy calculation for backward compatibility.
    
    Args:
        entity: The entity to score (will be normalized to canonical form)
        timeframe_hours: Timeframe in hours (24, 168, 720) or None for legacy
    
    Returns:
        Dict with score, component metrics, narrative_ids, and is_emerging flag
    """
    # Normalize entity name to canonical form (defensive measure)
    canonical_entity = normalize_entity_name(entity)
    if canonical_entity != entity:
        logger.info(f"Signal score calculation: normalized '{entity}' -> '{canonical_entity}'")
    
    if timeframe_hours is not None:
        # New multi-timeframe calculation
        metrics = await calculate_mentions_and_velocity(canonical_entity, timeframe_hours)
        diversity = await calculate_source_diversity(canonical_entity)
        recency = await calculate_recency_factor(canonical_entity, timeframe_hours)
        sentiment_metrics = await calculate_sentiment_metrics(canonical_entity)
        
        # New formula:
        # - Velocity (growth rate as percentage, e.g., 67.0 for 67%) weighted at 50%
        # - Diversity weighted at 30%
        # - Recency factor weighted at 20%
        # Note: velocity is now a percentage (0-300+), so we scale it down
        velocity_component = (metrics["velocity"] / 100) * 0.5
        diversity_component = diversity * 0.3
        recency_component = recency * 0.2
        
        raw_score = velocity_component + diversity_component + recency_component
        
        # Normalize to 0-10 scale
        # Max realistic: velocity=3.0 (300% growth), diversity=20, recency=1.0
        # Max raw: (3.0*0.5) + (20*0.3) + (1.0*0.2) = 1.5 + 6.0 + 0.2 = 7.7
        max_expected_score = 7.7
        normalized_score = min(10.0, (raw_score / max_expected_score) * 10.0)
        
        # Query narratives containing this entity
        narrative_ids = await get_narratives_for_entity(canonical_entity)
        is_emerging = len(narrative_ids) == 0
        
        return {
            "score": round(normalized_score, 2),
            "velocity": round(metrics["velocity"], 2),  # Percentage value (e.g., 67.50)
            "mentions": int(metrics["mentions"]),
            "source_count": diversity,
            "recency_factor": round(recency, 3),
            "sentiment": {
                "avg": round(sentiment_metrics["avg"], 3),
                "min": round(sentiment_metrics["min"], 3),
                "max": round(sentiment_metrics["max"], 3),
                "divergence": round(sentiment_metrics["divergence"], 3),
            },
            "narrative_ids": narrative_ids,
            "is_emerging": is_emerging,
        }
    else:
        # Legacy calculation for backward compatibility
        velocity = await calculate_velocity(canonical_entity)
        diversity = await calculate_source_diversity(canonical_entity)
        sentiment_metrics = await calculate_sentiment_metrics(canonical_entity)
        
        sentiment_avg = sentiment_metrics["avg"]
        
        # Calculate raw score
        # - Velocity weighted at 40%
        # - Diversity weighted at 30% 
        # - Sentiment strength (absolute value) weighted at 30%, scaled by 30x
        raw_score = (velocity * 0.4) + (diversity * 0.3) + (abs(sentiment_avg) * 30)
        
        # Normalize to 0-10 scale
        # Assuming max realistic values: velocity=10, diversity=20, sentiment=1
        # Max raw score would be: (10*0.4) + (20*0.3) + (1*30) = 4 + 6 + 30 = 40
        max_expected_score = 40.0
        normalized_score = min(10.0, (raw_score / max_expected_score) * 10.0)
        
        # Query narratives containing this entity
        narrative_ids = await get_narratives_for_entity(canonical_entity)
        is_emerging = len(narrative_ids) == 0
        
        return {
            "score": round(normalized_score, 2),
            "velocity": round(velocity, 2),
            "source_count": diversity,
            "sentiment": {
                "avg": round(sentiment_avg, 3),
                "min": round(sentiment_metrics["min"], 3),
                "max": round(sentiment_metrics["max"], 3),
                "divergence": round(sentiment_metrics["divergence"], 3),
            },
            "narrative_ids": narrative_ids,
            "is_emerging": is_emerging,
        }
