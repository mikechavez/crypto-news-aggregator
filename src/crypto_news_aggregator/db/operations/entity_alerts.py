"""
Database operations for entity alerts.

Entity alerts track trending entity events like:
- New entities appearing
- Velocity spikes
- Sentiment divergence
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from crypto_news_aggregator.db.mongodb import mongo_manager


async def create_alert(
    alert_type: str,
    entity: str,
    entity_type: str,
    severity: str,
    details: Dict[str, Any],
    signal_score: float
) -> str:
    """
    Create a new entity alert.
    
    Args:
        alert_type: Type of alert (NEW_ENTITY, VELOCITY_SPIKE, SENTIMENT_DIVERGENCE)
        entity: Entity name
        entity_type: Type of entity (ticker, project, event)
        severity: Alert severity (high, medium, low)
        details: Additional alert details
        signal_score: Current signal score
    
    Returns:
        The ID of the created alert
    """
    db = await mongo_manager.get_async_database()
    collection = db.entity_alerts
    
    now = datetime.now(timezone.utc)
    
    alert_data = {
        "type": alert_type,
        "entity": entity,
        "entity_type": entity_type,
        "severity": severity,
        "details": details,
        "signal_score": signal_score,
        "triggered_at": now,
        "resolved_at": None,
        "created_at": now
    }
    
    result = await collection.insert_one(alert_data)
    return str(result.inserted_id)


async def get_recent_alerts(
    hours: int = 24,
    severity: Optional[str] = None,
    unresolved_only: bool = True
) -> List[Dict[str, Any]]:
    """
    Get recent entity alerts.
    
    Args:
        hours: Number of hours to look back (default 24)
        severity: Filter by severity (high, medium, low) - optional
        unresolved_only: Only return unresolved alerts (default True)
    
    Returns:
        List of alert documents
    """
    db = await mongo_manager.get_async_database()
    collection = db.entity_alerts
    
    # Build query
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
    query = {"triggered_at": {"$gte": cutoff_time}}
    
    if severity:
        query["severity"] = severity
    
    if unresolved_only:
        query["resolved_at"] = None
    
    # Get alerts sorted by triggered_at (most recent first)
    cursor = collection.find(query).sort("triggered_at", -1)
    
    results = []
    async for alert in cursor:
        alert["_id"] = str(alert["_id"])
        results.append(alert)
    
    return results


async def resolve_alert(alert_id: str, resolved_at: Optional[datetime] = None) -> bool:
    """
    Mark an alert as resolved.
    
    Args:
        alert_id: ID of the alert to resolve
        resolved_at: Resolution timestamp (default: now)
    
    Returns:
        True if alert was resolved, False if not found
    """
    db = await mongo_manager.get_async_database()
    collection = db.entity_alerts
    
    from bson import ObjectId
    
    if not ObjectId.is_valid(alert_id):
        return False
    
    resolved_time = resolved_at or datetime.now(timezone.utc)
    
    result = await collection.update_one(
        {"_id": ObjectId(alert_id)},
        {"$set": {"resolved_at": resolved_time}}
    )
    
    return result.modified_count > 0


async def alert_exists(
    alert_type: str,
    entity: str,
    hours: int = 24
) -> bool:
    """
    Check if an alert of the same type for the same entity already exists.
    
    Prevents duplicate alerts within the specified time window.
    
    Args:
        alert_type: Type of alert
        entity: Entity name
        hours: Time window to check (default 24)
    
    Returns:
        True if alert exists, False otherwise
    """
    db = await mongo_manager.get_async_database()
    collection = db.entity_alerts
    
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    query = {
        "type": alert_type,
        "entity": entity,
        "triggered_at": {"$gte": cutoff_time}
    }
    
    count = await collection.count_documents(query, limit=1)
    return count > 0


async def ensure_indexes():
    """
    Ensure indexes exist for entity_alerts collection.
    
    Creates indexes on:
    - triggered_at (for time-based queries)
    - entity + type (for duplicate detection)
    - severity (for filtering)
    """
    db = await mongo_manager.get_async_database()
    collection = db.entity_alerts
    
    # Index on triggered_at for time-based queries
    await collection.create_index("triggered_at", background=True)
    
    # Compound index on entity + type for duplicate detection
    await collection.create_index(
        [("entity", 1), ("type", 1), ("triggered_at", -1)],
        background=True
    )
    
    # Index on severity for filtering
    await collection.create_index("severity", background=True)
    
    # Index on resolved_at for filtering unresolved alerts
    await collection.create_index("resolved_at", background=True)
