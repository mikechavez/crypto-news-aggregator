#!/usr/bin/env python3
"""
Test script to verify the narrative-entity linking fix.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from crypto_news_aggregator.db.mongodb import initialize_mongodb, mongo_manager
from crypto_news_aggregator.services.narrative_service import extract_entities_from_articles


async def test_entity_extraction():
    """Test that entity extraction now works correctly."""
    print("\n🧪 TESTING ENTITY EXTRACTION FIX")
    print("="*80)
    
    db = await mongo_manager.get_async_database()
    articles_collection = db.articles
    
    # Get a few recent articles with themes
    cursor = articles_collection.find({
        "themes": {"$exists": True, "$ne": []}
    }).limit(5)
    
    articles = []
    async for article in cursor:
        articles.append(article)
    
    if not articles:
        print("❌ No articles found with themes")
        return
    
    print(f"\n✅ Found {len(articles)} articles to test")
    
    # Test entity extraction
    print("\n🔍 Extracting entities from articles...")
    entities = await extract_entities_from_articles(articles)
    
    print(f"\n✅ Extracted {len(entities)} unique entities:")
    for i, entity in enumerate(entities[:10], 1):
        print(f"   {i}. {entity}")
    
    if len(entities) > 10:
        print(f"   ... and {len(entities) - 10} more")
    
    if entities:
        print("\n✅ SUCCESS: Entity extraction is working!")
    else:
        print("\n❌ FAILURE: No entities extracted (bug still present)")


async def test_narrative_detection():
    """Test full narrative detection with the fix."""
    print("\n\n🧪 TESTING FULL NARRATIVE DETECTION")
    print("="*80)
    
    from crypto_news_aggregator.services.narrative_service import detect_narratives
    
    print("\n🔍 Running narrative detection (this may take a minute)...")
    narratives = await detect_narratives(hours=48, min_articles=2)
    
    print(f"\n✅ Generated {len(narratives)} narratives")
    
    # Check if narratives have entities now
    narratives_with_entities = [n for n in narratives if n.get('entities')]
    narratives_without_entities = [n for n in narratives if not n.get('entities')]
    
    print(f"\n📊 Results:")
    print(f"   Narratives with entities: {len(narratives_with_entities)}")
    print(f"   Narratives without entities: {len(narratives_without_entities)}")
    
    if narratives_with_entities:
        print(f"\n✅ SUCCESS: Narratives now have entities linked!")
        print(f"\nExample narratives:")
        for i, narrative in enumerate(narratives_with_entities[:3], 1):
            print(f"\n{i}. {narrative.get('title', 'N/A')}")
            print(f"   Theme: {narrative.get('theme', 'N/A')}")
            print(f"   Entities ({len(narrative.get('entities', []))}): {', '.join(narrative.get('entities', [])[:5])}")
    else:
        print(f"\n⚠️  WARNING: No narratives have entities linked")


async def check_specific_entities():
    """Check if problem entities are now linked to narratives."""
    print("\n\n🧪 CHECKING PROBLEM ENTITIES")
    print("="*80)
    
    db = await mongo_manager.get_async_database()
    narratives_collection = db.narratives
    
    problem_entities = ["Ripple", "SEC", "Binance", "BlackRock", "Tether"]
    
    for entity in problem_entities:
        # Find narratives containing this entity
        cursor = narratives_collection.find({"entities": entity})
        narratives = []
        async for narrative in cursor:
            narratives.append(narrative)
        
        if narratives:
            print(f"\n✅ {entity}: Found in {len(narratives)} narrative(s)")
            for narrative in narratives:
                print(f"   - {narrative.get('theme', 'N/A')}: {narrative.get('title', 'N/A')[:60]}...")
        else:
            print(f"\n❌ {entity}: Not found in any narratives")


async def main():
    """Run all tests."""
    await initialize_mongodb()
    
    try:
        await test_entity_extraction()
        await test_narrative_detection()
        await check_specific_entities()
        
        print("\n" + "="*80)
        print("TESTING COMPLETE")
        print("="*80)
        
    finally:
        await mongo_manager.aclose()


if __name__ == "__main__":
    asyncio.run(main())
