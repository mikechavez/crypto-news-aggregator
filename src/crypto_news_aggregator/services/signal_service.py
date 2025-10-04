"""
Signal detection service for identifying trending crypto entities.

This service calculates signal scores based on:
- Velocity: Rate of mentions over time
- Source diversity: Number of unique sources mentioning the entity
- Sentiment metrics: Average sentiment and divergence
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from crypto_news_aggregator.db.mongodb import mongo_manager

logger = logging.getLogger(__name__)


async def calculate_velocity(entity: str, timeframe_hours: int = 24) -> float:
    """
    Calculate mention velocity for an entity.
    
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
    
    now = datetime.now(timezone.utc)
    one_hour_ago = now - timedelta(hours=1)
    timeframe_ago = now - timedelta(hours=timeframe_hours)
    
    # Count mentions in last hour (primary entities only)
    mentions_1h = await collection.count_documents({
        "entity": entity,
        "is_primary": True,
        "timestamp": {"$gte": one_hour_ago}
    })
    
    # Count mentions in full timeframe (primary entities only)
    mentions_timeframe = await collection.count_documents({
        "entity": entity,
        "is_primary": True,
        "timestamp": {"$gte": timeframe_ago}
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
    
    Counts the number of unique RSS sources that have mentioned this entity.
    
    Args:
        entity: The entity to calculate diversity for
    
    Returns:
        Number of unique sources
    """
    db = await mongo_manager.get_async_database()
    entity_mentions_collection = db.entity_mentions
    articles_collection = db.articles
    
    # Get all article IDs that mention this entity (primary mentions only)
    pipeline = [
        {"$match": {"entity": entity, "is_primary": True}},
        {"$group": {"_id": "$article_id"}},
    ]
    
    article_ids = []
    async for result in entity_mentions_collection.aggregate(pipeline):
        article_ids.append(result["_id"])
    
    if not article_ids:
        return 0
    
    # Count unique sources from these articles
    source_pipeline = [
        {"$match": {"_id": {"$in": article_ids}}},
        {"$group": {"_id": "$source"}},
    ]
    
    unique_sources = 0
    async for _ in articles_collection.aggregate(source_pipeline):
        unique_sources += 1
    
    return unique_sources


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


async def calculate_signal_score(entity: str) -> Dict[str, Any]:
    """
    Calculate overall signal score for an entity.
    
    Formula: (velocity * 0.4) + (diversity * 0.3) + (abs(sentiment_avg) * 30)
    Normalized to 0-10 scale.
    
    Args:
        entity: The entity to score
    
    Returns:
        Dict with score and component metrics
    """
    # Get all component metrics
    velocity = await calculate_velocity(entity)
    diversity = await calculate_source_diversity(entity)
    sentiment_metrics = await calculate_sentiment_metrics(entity)
    
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
    }
