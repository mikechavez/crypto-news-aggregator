"""
Database operations for narrative tracking.

Narratives represent theme-based clusters of articles
with AI-generated summaries and lifecycle tracking.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from crypto_news_aggregator.db.mongodb import mongo_manager


def _should_append_timeline_snapshot(existing: Optional[Dict[str, Any]]) -> bool:
    """
    Determine if we should append a new timeline snapshot.
    
    Only append if:
    - No existing timeline data, OR
    - Last snapshot is from a different day (UTC)
    
    Args:
        existing: Existing narrative document or None
    
    Returns:
        True if we should append a new snapshot
    """
    if not existing:
        return True
    
    timeline_data = existing.get("timeline_data", [])
    if not timeline_data:
        return True
    
    # Get the last snapshot date
    last_snapshot = timeline_data[-1]
    last_date_str = last_snapshot.get("date")
    
    if not last_date_str:
        return True
    
    # Check if today is different from last snapshot date
    today = datetime.now(timezone.utc).date().isoformat()
    return today != last_date_str


def _calculate_days_active(first_seen: datetime) -> int:
    """
    Calculate number of days a narrative has been active.
    
    Args:
        first_seen: When narrative was first detected
    
    Returns:
        Number of days (minimum 1)
    """
    now = datetime.now(timezone.utc)
    # Ensure first_seen is timezone-aware
    if first_seen.tzinfo is None:
        first_seen = first_seen.replace(tzinfo=timezone.utc)
    delta = now - first_seen
    return max(1, delta.days + 1)  # +1 to count partial days


async def upsert_narrative(
    theme: str,
    title: str,
    summary: str,
    entities: List[str],
    article_ids: List[str],
    article_count: int,
    mention_velocity: float,
    lifecycle: str,
    momentum: str = "unknown",
    recency_score: float = 0.0,
    entity_relationships: Optional[List[Dict[str, Any]]] = None,
    first_seen: Optional[datetime] = None,
    lifecycle_state: Optional[str] = None,
    lifecycle_history: Optional[List[Dict[str, Any]]] = None,
    reawakening_count: Optional[int] = None,
    reawakened_from: Optional[datetime] = None,
    resurrection_velocity: Optional[float] = None
) -> str:
    """
    Create or update a narrative record with full structure and timeline tracking.
    
    Upserts based on theme to avoid duplicates. Updates all fields
    if the narrative already exists. Appends daily snapshots to timeline_data.
    
    Args:
        theme: Theme category (e.g., "regulatory", "defi_adoption")
        title: Generated narrative title
        summary: AI-generated narrative summary
        entities: List of entity names in this narrative
        article_ids: List of article IDs supporting this narrative
        article_count: Number of articles supporting this narrative
        mention_velocity: Articles per day rate
        lifecycle: Lifecycle stage (emerging, rising, hot, heating, mature, cooling, declining)
        momentum: Momentum indicator (growing, declining, stable, unknown)
        recency_score: Freshness score (0-1, higher = more recent)
        entity_relationships: Top 5 entity co-occurrence pairs with weights: [{"a": "SEC", "b": "Binance", "weight": 3}]
        first_seen: When narrative was first detected (optional)
        lifecycle_state: Lifecycle state (emerging, rising, hot, cooling, dormant) - optional
        lifecycle_history: History of lifecycle state transitions - optional
        reawakening_count: Number of times narrative has been reactivated (optional)
        reawakened_from: Timestamp when narrative went dormant before reactivation (optional)
        resurrection_velocity: Articles per day in last 48 hours during reactivation (optional)
    
    Returns:
        The ID of the upserted narrative
    """
    db = await mongo_manager.get_async_database()
    collection = db.narratives
    
    now = datetime.now(timezone.utc)
    today = now.date().isoformat()
    
    # Check if narrative with this theme exists
    existing = await collection.find_one({"theme": theme})
    
    # Create today's timeline snapshot
    timeline_snapshot = {
        "date": today,
        "article_count": article_count,
        "entities": entities[:10],  # Limit to top 10
        "velocity": round(mention_velocity, 2)
    }
    
    if existing:
        # Update existing narrative
        first_seen_date = existing.get("first_seen", now)
        days_active = _calculate_days_active(first_seen_date)
        
        # Get existing timeline data and peak activity
        timeline_data = existing.get("timeline_data", [])
        peak_activity = existing.get("peak_activity", {})
        
        # Check if we should append a new snapshot (once per day)
        if _should_append_timeline_snapshot(existing):
            timeline_data.append(timeline_snapshot)
        else:
            # Update today's snapshot if it already exists
            if timeline_data:
                timeline_data[-1] = timeline_snapshot
        
        # Update peak activity if today exceeds previous peak
        peak_article_count = peak_activity.get("article_count", 0)
        if article_count > peak_article_count:
            peak_activity = {
                "date": today,
                "article_count": article_count,
                "velocity": round(mention_velocity, 2)
            }
        
        update_data = {
            "title": title,
            "summary": summary,
            "entities": entities,
            "article_ids": article_ids,
            "article_count": article_count,
            "mention_velocity": mention_velocity,
            "lifecycle": lifecycle,
            "momentum": momentum,
            "recency_score": recency_score,
            "entity_relationships": entity_relationships or [],
            "last_updated": now,
            "timeline_data": timeline_data,
            "peak_activity": peak_activity,
            "days_active": days_active
        }
        
        # Add lifecycle_state if provided
        if lifecycle_state is not None:
            update_data["lifecycle_state"] = lifecycle_state
        
        # Add lifecycle_history if provided
        if lifecycle_history is not None:
            update_data["lifecycle_history"] = lifecycle_history
        
        # Add resurrection tracking fields if provided
        if reawakening_count is not None:
            update_data["reawakening_count"] = reawakening_count
        if reawakened_from is not None:
            update_data["reawakened_from"] = reawakened_from
        if resurrection_velocity is not None:
            update_data["resurrection_velocity"] = resurrection_velocity
        
        await collection.update_one(
            {"theme": theme},
            {"$set": update_data}
        )
        return str(existing["_id"])
    else:
        # Create new narrative with initial timeline data
        first_seen_date = first_seen or now
        days_active = _calculate_days_active(first_seen_date)
        
        narrative_data = {
            "theme": theme,
            "title": title,
            "summary": summary,
            "entities": entities,
            "article_ids": article_ids,
            "first_seen": first_seen_date,
            "last_updated": now,
            "article_count": article_count,
            "mention_velocity": mention_velocity,
            "lifecycle": lifecycle,
            "momentum": momentum,
            "recency_score": recency_score,
            "entity_relationships": entity_relationships or [],
            "timeline_data": [timeline_snapshot],
            "peak_activity": {
                "date": today,
                "article_count": article_count,
                "velocity": round(mention_velocity, 2)
            },
            "days_active": days_active
        }
        
        # Add lifecycle_state if provided
        if lifecycle_state is not None:
            narrative_data["lifecycle_state"] = lifecycle_state
        
        # Add lifecycle_history if provided
        if lifecycle_history is not None:
            narrative_data["lifecycle_history"] = lifecycle_history
        
        # Add resurrection tracking fields if provided
        if reawakening_count is not None:
            narrative_data["reawakening_count"] = reawakening_count
        if reawakened_from is not None:
            narrative_data["reawakened_from"] = reawakened_from
        if resurrection_velocity is not None:
            narrative_data["resurrection_velocity"] = resurrection_velocity
        
        result = await collection.insert_one(narrative_data)
        return str(result.inserted_id)


async def get_active_narratives(
    limit: int = 10,
    lifecycle_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get active narratives sorted by most recently updated.
    
    Args:
        limit: Maximum number of narratives to return (default 10)
        lifecycle_filter: Optional filter by lifecycle stage
    
    Returns:
        List of narrative documents
    """
    db = await mongo_manager.get_async_database()
    collection = db.narratives
    
    # Build query filter
    query = {}
    if lifecycle_filter:
        query["lifecycle"] = lifecycle_filter
    
    # Get narratives sorted by last_updated (most recent first)
    cursor = collection.find(query).sort("last_updated", -1).limit(limit)
    
    narratives = []
    async for narrative in cursor:
        narrative["_id"] = str(narrative["_id"])
        narratives.append(narrative)
    
    return narratives


async def delete_old_narratives(days: int = 7) -> int:
    """
    Delete narratives older than specified days.
    
    Args:
        days: Number of days to keep (default 7)
    
    Returns:
        Number of deleted narratives
    """
    db = await mongo_manager.get_async_database()
    collection = db.narratives
    
    from datetime import timedelta
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    result = await collection.delete_many({
        "last_updated": {"$lt": cutoff_date}
    })
    
    return result.deleted_count


async def get_narrative_timeline(narrative_id: str) -> Optional[List[Dict[str, Any]]]:
    """
    Get timeline data for a specific narrative.
    
    Args:
        narrative_id: MongoDB ObjectId as string
    
    Returns:
        List of timeline snapshots or None if narrative not found
    """
    from bson import ObjectId
    
    db = await mongo_manager.get_async_database()
    collection = db.narratives
    
    try:
        narrative = await collection.find_one({"_id": ObjectId(narrative_id)})
        if not narrative:
            return None
        
        return narrative.get("timeline_data", [])
    except Exception:
        return None


async def ensure_indexes():
    """
    Ensure required indexes exist on the narratives collection.
    
    Creates indexes for:
    - last_updated (for sorting and cleanup)
    - theme (for upsert uniqueness)
    - lifecycle (for filtering)
    """
    db = await mongo_manager.get_async_database()
    collection = db.narratives
    
    # Index on last_updated for sorting and cleanup
    await collection.create_index("last_updated", name="idx_last_updated")
    
    # Index on theme for upsert operations
    await collection.create_index("theme", unique=True, name="idx_theme_unique")
    
    # Index on lifecycle for filtering
    await collection.create_index("lifecycle", name="idx_lifecycle")
