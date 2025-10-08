"""
Signal detection service for identifying trending crypto entities.

This service calculates signal scores based on:
- Velocity: Rate of mentions over time
- Source diversity: Number of unique sources mentioning the entity
- Sentiment metrics: Average sentiment and divergence

Note: All entity queries use the entity name as stored in entity_mentions,
which should already be normalized to canonical form by the RSS fetcher.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from crypto_news_aggregator.db.mongodb import mongo_manager
from crypto_news_aggregator.services.entity_normalization import normalize_entity_name

logger = logging.getLogger(__name__)


async def calculate_mentions_and_velocity(entity: str, timeframe_hours: int) -> Dict[str, float]:
    """
    Calculate mention count and velocity (growth rate) for an entity over a timeframe.
    
    Velocity = (current_period - previous_period) / previous_period * 100
    Example: 50 mentions this week vs 30 last week = (50-30)/30 = 67% growth
    
    Args:
        entity: The entity to calculate metrics for
        timeframe_hours: Timeframe in hours (24, 168 for 7d, 720 for 30d)
    
    Returns:
        Dict with 'mentions' (count) and 'velocity' (growth % as decimal)
    """
    db = await mongo_manager.get_async_database()
    collection = db.entity_mentions
    
    # MongoDB stores datetimes as UTC but returns them as naive
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    current_period_start = now - timedelta(hours=timeframe_hours)
    previous_period_start = now - timedelta(hours=timeframe_hours * 2)
    
    # Count mentions in current period (primary entities only)
    current_mentions = await collection.count_documents({
        "entity": entity,
        "is_primary": True,
        "created_at": {"$gte": current_period_start}
    })
    
    # Count mentions in previous period (primary entities only)
    previous_mentions = await collection.count_documents({
        "entity": entity,
        "is_primary": True,
        "created_at": {"$gte": previous_period_start, "$lt": current_period_start}
    })
    
    # Calculate velocity as growth rate
    if previous_mentions == 0:
        # If no previous data, velocity is 100% if we have current mentions, else 0%
        velocity = 1.0 if current_mentions > 0 else 0.0
    else:
        # Growth rate: (current - previous) / previous
        velocity = (current_mentions - previous_mentions) / previous_mentions
    
    return {
        "mentions": float(current_mentions),
        "velocity": velocity
    }


async def calculate_velocity(entity: str, timeframe_hours: int = 24) -> float:
    """
    Calculate mention velocity for an entity (legacy method for backward compatibility).
    
    Velocity = (mentions in last 1 hour) / (mentions in last 24 hours / 24)
    This gives us a ratio showing if mentions are accelerating.
    
    Args:
        entity: The entity to calculate velocity for
        timeframe_hours: Timeframe for baseline calculation (default 24)
    
    Returns:
        Velocity score (higher = more acceleration)
    """
    db = await mongo_manager.get_async_database()
    collection = db.entity_mentions
    
    # MongoDB stores datetimes as UTC but returns them as naive
    # Use naive datetimes for comparison
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    one_hour_ago = now - timedelta(hours=1)
    timeframe_ago = now - timedelta(hours=timeframe_hours)
    
    # Count mentions in last hour (primary entities only)
    mentions_1h = await collection.count_documents({
        "entity": entity,
        "is_primary": True,
        "created_at": {"$gte": one_hour_ago}
    })
    
    # Count mentions in full timeframe (primary entities only)
    mentions_timeframe = await collection.count_documents({
        "entity": entity,
        "is_primary": True,
        "created_at": {"$gte": timeframe_ago}
    })
    
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
    
    Counts the number of unique sources that have mentioned this entity.
    Entity mentions have a 'source' field directly.
    
    Args:
        entity: The entity to calculate diversity for
    
    Returns:
        Number of unique sources
    """
    db = await mongo_manager.get_async_database()
    entity_mentions_collection = db.entity_mentions
    
    # Get unique sources directly from entity mentions (primary mentions only)
    sources = await entity_mentions_collection.distinct(
        "source",
        {"entity": entity, "is_primary": True}
    )
    
    return len(sources)


async def calculate_sentiment_metrics(entity: str) -> Dict[str, float]:
    """
    Calculate sentiment metrics for an entity.
    
    Args:
        entity: The entity to calculate sentiment for
    
    Returns:
        Dict with avg, min, max, and divergence (std deviation approximation)
    """
    db = await mongo_manager.get_async_database()
    collection = db.entity_mentions
    
    # Map sentiment labels to numeric scores
    sentiment_map = {
        "positive": 1.0,
        "neutral": 0.0,
        "negative": -1.0,
    }
    
    # Get all mentions with sentiment (primary mentions only)
    cursor = collection.find({"entity": entity, "is_primary": True})
    
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
    
    Measures what percentage of mentions occurred in the most recent 20% of the timeframe.
    
    Args:
        entity: The entity to calculate recency for
        timeframe_hours: Timeframe in hours
    
    Returns:
        Recency factor (0.0 to 1.0)
    """
    db = await mongo_manager.get_async_database()
    collection = db.entity_mentions
    
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    timeframe_start = now - timedelta(hours=timeframe_hours)
    recent_window_hours = timeframe_hours * 0.2  # Most recent 20%
    recent_start = now - timedelta(hours=recent_window_hours)
    
    # Count total mentions in timeframe
    total_mentions = await collection.count_documents({
        "entity": entity,
        "is_primary": True,
        "created_at": {"$gte": timeframe_start}
    })
    
    if total_mentions == 0:
        return 0.0
    
    # Count mentions in recent window
    recent_mentions = await collection.count_documents({
        "entity": entity,
        "is_primary": True,
        "created_at": {"$gte": recent_start}
    })
    
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
        # - Velocity (growth rate as decimal, e.g., 0.67 for 67%) weighted at 50%
        # - Diversity weighted at 30%
        # - Recency factor weighted at 20%
        velocity_component = metrics["velocity"] * 0.5
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
            "velocity": round(metrics["velocity"], 3),
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
