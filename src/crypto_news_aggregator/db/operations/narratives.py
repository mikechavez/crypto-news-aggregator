"""
Database operations for narrative tracking.

Narratives represent groups of co-occurring crypto entities
with AI-generated summaries of their thematic connections.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from crypto_news_aggregator.db.mongodb import mongo_manager


async def upsert_narrative(
    theme: str,
    entities: List[str],
    story: str,
    article_count: int
) -> str:
    """
    Create or update a narrative record.
    
    Upserts based on theme to avoid duplicates. Updates the story
    and article_count if the narrative already exists.
    
    Args:
        theme: Short title for the narrative
        entities: List of entity names in this narrative
        story: 1-2 sentence summary of the narrative
        article_count: Number of articles supporting this narrative
    
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
            "entities": entities,
            "story": story,
            "article_count": article_count,
            "updated_at": now,
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
            "entities": entities,
            "story": story,
            "article_count": article_count,
            "created_at": now,
            "updated_at": now,
        }
        
        result = await collection.insert_one(narrative_data)
        return str(result.inserted_id)


async def get_active_narratives(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get active narratives sorted by most recently updated.
    
    Args:
        limit: Maximum number of narratives to return (default 10)
    
    Returns:
        List of narrative documents
    """
    db = await mongo_manager.get_async_database()
    collection = db.narratives
    
    # Get narratives sorted by updated_at (most recent first)
    cursor = collection.find({}).sort("updated_at", -1).limit(limit)
    
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
        "updated_at": {"$lt": cutoff_date}
    })
    
    return result.deleted_count


async def ensure_indexes():
    """
    Ensure required indexes exist on the narratives collection.
    
    Creates indexes for:
    - updated_at (for sorting and cleanup)
    - theme (for upsert uniqueness)
    """
    db = await mongo_manager.get_async_database()
    collection = db.narratives
    
    # Index on updated_at for sorting and cleanup
    await collection.create_index("updated_at", name="idx_updated_at")
    
    # Index on theme for upsert operations
    await collection.create_index("theme", unique=True, name="idx_theme_unique")
