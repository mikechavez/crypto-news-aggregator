#!/usr/bin/env python3
"""
Force rebuild narratives with the fix applied.
This will delete old narratives and regenerate them.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from crypto_news_aggregator.db.mongodb import initialize_mongodb, mongo_manager
from crypto_news_aggregator.services.narrative_service import detect_narratives


async def rebuild_narratives():
    """Delete old narratives and rebuild with the fix."""
    print("\n🔄 FORCING NARRATIVE REBUILD")
    print("="*80)
    
    db = await mongo_manager.get_async_database()
    narratives_collection = db.narratives
    
    # Count existing narratives
    old_count = await narratives_collection.count_documents({})
    print(f"\n📊 Found {old_count} existing narratives")
    
    # Delete all narratives
    print("\n🗑️  Deleting old narratives...")
    result = await narratives_collection.delete_many({})
    print(f"   Deleted {result.deleted_count} narratives")
    
    # Regenerate narratives
    print("\n🔍 Regenerating narratives with fix applied...")
    narratives = await detect_narratives(hours=48, min_articles=2)
    
    print(f"\n✅ Generated {len(narratives)} new narratives")
    
    # Check results
    narratives_with_entities = [n for n in narratives if n.get('entities')]
    narratives_without_entities = [n for n in narratives if not n.get('entities')]
    
    print(f"\n📊 Results:")
    print(f"   Narratives with entities: {len(narratives_with_entities)}")
    print(f"   Narratives without entities: {len(narratives_without_entities)}")
    
    if narratives_with_entities:
        print(f"\n✅ SUCCESS: Narratives now have entities!")
        print(f"\nSample narratives with entities:")
        for i, narrative in enumerate(narratives_with_entities[:5], 1):
            entities = narrative.get('entities', [])
            print(f"\n{i}. Theme: {narrative.get('theme', 'N/A')}")
            print(f"   Title: {narrative.get('title', 'N/A')}")
            print(f"   Entities ({len(entities)}): {', '.join(entities[:10])}")
            if len(entities) > 10:
                print(f"      ... and {len(entities) - 10} more")
    
    if narratives_without_entities:
        print(f"\n⚠️  {len(narratives_without_entities)} narratives still have no entities:")
        for narrative in narratives_without_entities:
            print(f"   - {narrative.get('theme', 'N/A')}: {narrative.get('article_count', 0)} articles")


async def main():
    """Run rebuild."""
    await initialize_mongodb()
    
    try:
        await rebuild_narratives()
        
        print("\n" + "="*80)
        print("REBUILD COMPLETE")
        print("="*80)
        
    finally:
        await mongo_manager.aclose()


if __name__ == "__main__":
    asyncio.run(main())
