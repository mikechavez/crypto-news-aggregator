"""
Database operations for signal scores.

Signal scores track trending entities based on mention velocity,
source diversity, and sentiment metrics.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from crypto_news_aggregator.db.mongodb import mongo_manager


async def upsert_signal_score(
    entity: str,
    entity_type: str,
    score: float,
    velocity: float,
    source_count: int,
    sentiment: Dict[str, float],
    first_seen: datetime = None,
) -> str:
    """
    Create or update a signal score record.
    
    Args:
        entity: The entity name/value
        entity_type: Type of entity (ticker, project, event)
        score: Overall signal score (0-10)
        velocity: Mention velocity metric
        source_count: Number of unique sources
        sentiment: Sentiment metrics dict
        first_seen: When entity was first detected (optional)
    
    Returns:
        The ID of the upserted signal score record
    """
    db = await mongo_manager.get_async_database()
    collection = db.signal_scores
    
    now = datetime.now(timezone.utc)
    
    # Check if record exists
    existing = await collection.find_one({"entity": entity})
    
    if existing:
        # Update existing record
        update_data = {
            "entity_type": entity_type,
            "score": score,
            "velocity": velocity,
            "source_count": source_count,
            "sentiment": sentiment,
            "last_updated": now,
        }
        
        await collection.update_one(
            {"entity": entity},
            {"$set": update_data}
        )
        return str(existing["_id"])
    else:
        # Create new record
        signal_data = {
            "entity": entity,
            "entity_type": entity_type,
            "score": score,
            "velocity": velocity,
            "source_count": source_count,
            "sentiment": sentiment,
            "first_seen": first_seen or now,
            "last_updated": now,
            "created_at": now,
        }
        
        result = await collection.insert_one(signal_data)
        return str(result.inserted_id)


async def get_trending_entities(
    limit: int = 20,
    min_score: float = 0.0,
    entity_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Get trending entities sorted by signal score.
    
    Args:
        limit: Maximum number of results (default 20)
        min_score: Minimum signal score threshold (default 0.0)
        entity_type: Filter by entity type (optional)
    
    Returns:
        List of signal score documents
    """
    db = await mongo_manager.get_async_database()
    collection = db.signal_scores
    
    # Build query
    query = {"score": {"$gte": min_score}}
    if entity_type:
        query["entity_type"] = entity_type
    
    # Get trending entities sorted by score
    cursor = collection.find(query).sort("score", -1).limit(limit)
    
    results = []
    async for signal in cursor:
        signal["_id"] = str(signal["_id"])
        results.append(signal)
    
    return results


async def get_entity_signal(entity: str) -> Optional[Dict[str, Any]]:
    """
    Get signal score for a specific entity.
    
    Args:
        entity: The entity to get signal for
    
    Returns:
        Signal score document or None if not found
    """
    db = await mongo_manager.get_async_database()
    collection = db.signal_scores
    
    signal = await collection.find_one({"entity": entity})
    
    if signal:
        signal["_id"] = str(signal["_id"])
        return signal
    
    return None


async def delete_old_signals(days: int = 7) -> int:
    """
    Delete signal scores older than specified days.
    
    Args:
        days: Number of days to keep (default 7)
    
    Returns:
        Number of deleted records
    """
    db = await mongo_manager.get_async_database()
    collection = db.signal_scores
    
    from datetime import timedelta
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    result = await collection.delete_many({
        "last_updated": {"$lt": cutoff_date}
    })
    
    return result.deleted_count
