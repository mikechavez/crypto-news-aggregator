#!/usr/bin/env python3
"""
Migrate old narrative documents to new schema.

Updates old narratives with:
- Rename updated_at -> last_updated
- Rename created_at -> first_seen
- Rename story -> summary
- Add missing fields (title, mention_velocity, lifecycle)
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from crypto_news_aggregator.db.mongodb import mongo_manager


async def migrate_narratives():
    """Migrate old narrative documents to new schema."""
    
    await mongo_manager.initialize()
    
    db = await mongo_manager.get_async_database()
    narratives_collection = db.narratives
    
    # Find all narratives
    cursor = narratives_collection.find({})
    
    migrated_count = 0
    skipped_count = 0
    
    async for narrative in cursor:
        narrative_id = narrative.get("_id")
        theme = narrative.get("theme", "unknown")
        
        # Check if already migrated (has last_updated field)
        if "last_updated" in narrative:
            print(f"Skipping {theme} - already migrated")
            skipped_count += 1
            continue
        
        print(f"Migrating narrative: {theme}")
        
        # Build update document
        update_doc = {}
        rename_doc = {}
        
        # Rename fields
        if "updated_at" in narrative:
            rename_doc["updated_at"] = "last_updated"
        
        if "created_at" in narrative:
            rename_doc["created_at"] = "first_seen"
        
        if "story" in narrative:
            rename_doc["story"] = "summary"
        
        # Add missing fields
        if "title" not in narrative:
            # Use theme as title
            update_doc["title"] = theme.replace("_", " ").title()
        
        if "mention_velocity" not in narrative:
            # Calculate basic velocity from article count
            article_count = narrative.get("article_count", 0)
            update_doc["mention_velocity"] = round(article_count / 2.0, 2)  # Assume 2-day window
        
        if "lifecycle" not in narrative:
            # Determine lifecycle from article count
            article_count = narrative.get("article_count", 0)
            if article_count <= 4:
                update_doc["lifecycle"] = "emerging"
            elif article_count <= 10:
                update_doc["lifecycle"] = "hot"
            else:
                update_doc["lifecycle"] = "mature"
        
        # Ensure first_seen exists
        if "first_seen" not in narrative and "created_at" not in narrative:
            update_doc["first_seen"] = narrative.get("updated_at", datetime.now(timezone.utc))
        
        # Ensure last_updated exists
        if "last_updated" not in narrative and "updated_at" not in narrative:
            update_doc["last_updated"] = datetime.now(timezone.utc)
        
        # Apply updates
        update_operations = {}
        if update_doc:
            update_operations["$set"] = update_doc
        if rename_doc:
            update_operations["$rename"] = rename_doc
        
        if update_operations:
            result = await narratives_collection.update_one(
                {"_id": narrative_id},
                update_operations
            )
            
            if result.modified_count > 0:
                print(f"  ✓ Migrated {theme}")
                migrated_count += 1
            else:
                print(f"  ✗ Failed to migrate {theme}")
        else:
            print(f"  - No changes needed for {theme}")
            skipped_count += 1
    
    print(f"\n{'='*60}")
    print(f"Migration complete!")
    print(f"  Migrated: {migrated_count}")
    print(f"  Skipped: {skipped_count}")
    print(f"{'='*60}")
    
    await mongo_manager.close()


if __name__ == "__main__":
    asyncio.run(migrate_narratives())
