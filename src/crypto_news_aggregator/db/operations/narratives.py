"""
Database operations for narrative tracking.

Narratives represent theme-based clusters of articles
with AI-generated summaries and lifecycle tracking.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from crypto_news_aggregator.db.mongodb import mongo_manager


async def upsert_narrative(
    theme: str,
    title: str,
    summary: str,
    entities: List[str],
    article_ids: List[str],
    article_count: int,
    mention_velocity: float,
    lifecycle: str,
    first_seen: Optional[datetime] = None
) -> str:
    """
    Create or update a narrative record with full structure.
    
    Upserts based on theme to avoid duplicates. Updates all fields
    if the narrative already exists.
    
    Args:
        theme: Theme category (e.g., "regulatory", "defi_adoption")
        title: Generated narrative title
        summary: AI-generated narrative summary
        entities: List of entity names in this narrative
        article_ids: List of article IDs supporting this narrative
        article_count: Number of articles supporting this narrative
        mention_velocity: Articles per day rate
        lifecycle: Lifecycle stage (emerging, hot, mature, declining)
        first_seen: When narrative was first detected (optional)
    
    Returns:
        The ID of the upserted narrative
    """
    db = await mongo_manager.get_async_database()
    collection = db.narratives
    
    now = datetime.now(timezone.utc)
    
    # Check if narrative with this theme exists
    existing = await collection.find_one({"theme": theme})
    
    if existing:
        # Update existing narrative
        update_data = {
            "title": title,
            "summary": summary,
            "entities": entities,
            "article_ids": article_ids,
            "article_count": article_count,
            "mention_velocity": mention_velocity,
            "lifecycle": lifecycle,
            "last_updated": now,
        }
        
        await collection.update_one(
            {"theme": theme},
            {"$set": update_data}
        )
        return str(existing["_id"])
    else:
        # Create new narrative
        narrative_data = {
            "theme": theme,
            "title": title,
            "summary": summary,
            "entities": entities,
            "article_ids": article_ids,
            "first_seen": first_seen or now,
            "last_updated": now,
            "article_count": article_count,
            "mention_velocity": mention_velocity,
            "lifecycle": lifecycle,
        }
        
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
