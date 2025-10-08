"""
Clean up duplicate narratives in the database.

This script removes old duplicate narratives that were created before
the deduplication feature was deployed.
"""

import asyncio
from datetime import datetime, timezone
from crypto_news_aggregator.db.mongodb import initialize_mongodb, mongo_manager


async def clean_duplicate_narratives():
    """Remove duplicate narratives from the database."""
    await initialize_mongodb()
    db = await mongo_manager.get_async_database()
    collection = db.narratives
    
    # Get all narratives
    narratives = []
    async for narrative in collection.find({}):
        narratives.append(narrative)
    
    print(f"Found {len(narratives)} total narratives")
    
    # Group by entity sets (to find duplicates)
    entity_groups = {}
    for narrative in narratives:
        entities = tuple(sorted(narrative.get("entities", [])))
        if entities not in entity_groups:
            entity_groups[entities] = []
        entity_groups[entities].append(narrative)
    
    # Find and remove duplicates
    deleted_count = 0
    for entities, group in entity_groups.items():
        if len(group) > 1:
            print(f"\nFound {len(group)} duplicates for entities: {list(entities)}")
            
            # Sort by article_count (keep the one with most articles)
            group.sort(key=lambda n: n.get("article_count", 0), reverse=True)
            
            # Keep the first one, delete the rest
            keep = group[0]
            print(f"  Keeping: {keep['theme']} ({keep['article_count']} articles)")
            
            for duplicate in group[1:]:
                print(f"  Deleting: {duplicate['theme']} ({duplicate['article_count']} articles)")
                await collection.delete_one({"_id": duplicate["_id"]})
                deleted_count += 1
    
    print(f"\n✅ Cleaned up {deleted_count} duplicate narratives")
    print(f"Remaining narratives: {len(narratives) - deleted_count}")
    
    await mongo_manager.aclose()


if __name__ == "__main__":
    asyncio.run(clean_duplicate_narratives())
