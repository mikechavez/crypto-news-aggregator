#!/usr/bin/env python3
"""
Diagnostic script to investigate why entities aren't being linked to narratives.

Checks:
1. Recent narratives and their linked entities
2. Entities that should be linked but aren't (SEC, Ripple, Binance, BlackRock, Tether)
3. Articles mentioning these entities and their themes
4. Theme extraction quality
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from crypto_news_aggregator.db.mongodb import initialize_mongodb, mongo_manager


async def check_narratives():
    """Check existing narratives and their entities."""
    print("\n" + "="*80)
    print("CHECKING NARRATIVES")
    print("="*80)
    
    db = await mongo_manager.get_async_database()
    narratives_collection = db.narratives
    
    cursor = narratives_collection.find({}).sort("last_updated", -1).limit(10)
    
    narratives = []
    async for narrative in cursor:
        narratives.append(narrative)
    
    if not narratives:
        print("❌ NO NARRATIVES FOUND IN DATABASE")
        return
    
    print(f"\n✅ Found {len(narratives)} recent narratives:\n")
    
    for i, narrative in enumerate(narratives, 1):
        print(f"{i}. Theme: {narrative.get('theme', 'N/A')}")
        print(f"   Title: {narrative.get('title', 'N/A')}")
        print(f"   Lifecycle: {narrative.get('lifecycle', 'N/A')}")
        print(f"   Article Count: {narrative.get('article_count', 0)}")
        print(f"   Entities ({len(narrative.get('entities', []))}): {', '.join(narrative.get('entities', [])[:5])}")
        print(f"   Last Updated: {narrative.get('last_updated', 'N/A')}")
        print()


async def check_entity_mentions(entity_name: str):
    """Check entity mentions for a specific entity."""
    db = await mongo_manager.get_async_database()
    entity_mentions_collection = db.entity_mentions
    
    # Get recent mentions
    cursor = entity_mentions_collection.find({"entity": entity_name}).sort("created_at", -1).limit(5)
    
    mentions = []
    async for mention in cursor:
        mentions.append(mention)
    
    if not mentions:
        print(f"   ❌ No mentions found for '{entity_name}'")
        return None
    
    print(f"   ✅ Found {len(mentions)} recent mentions")
    
    # Get article IDs
    article_ids = [m.get("article_id") for m in mentions if m.get("article_id")]
    return article_ids


async def check_article_themes(article_id: str):
    """Check themes for a specific article."""
    db = await mongo_manager.get_async_database()
    articles_collection = db.articles
    
    article = await articles_collection.find_one({"_id": article_id})
    
    if not article:
        return None
    
    return {
        "title": article.get("title", "N/A"),
        "themes": article.get("themes", []),
        "published_at": article.get("published_at", "N/A")
    }


async def check_problem_entities():
    """Check entities that should be linked to narratives but aren't."""
    print("\n" + "="*80)
    print("CHECKING PROBLEM ENTITIES")
    print("="*80)
    
    problem_entities = [
        ("Ripple", "Should be 'regulatory' (SEC lawsuit)"),
        ("SEC", "Should be 'regulatory' (enforcement actions)"),
        ("Binance", "Should be 'regulatory' (legal cases)"),
        ("BlackRock", "Should be 'institutional_investment' (Bitcoin ETF)"),
        ("Tether", "Should be 'stablecoin' (it IS a stablecoin)"),
    ]
    
    for entity, expected in problem_entities:
        print(f"\n🔍 Checking: {entity}")
        print(f"   Expected: {expected}")
        
        # Check if entity has mentions
        article_ids = await check_entity_mentions(entity)
        
        if not article_ids:
            continue
        
        # Check themes of articles mentioning this entity
        print(f"   Checking themes of {len(article_ids)} articles...")
        
        themes_found = set()
        for article_id in article_ids[:3]:  # Check first 3 articles
            article_info = await check_article_themes(article_id)
            if article_info:
                print(f"      - '{article_info['title'][:60]}...'")
                print(f"        Themes: {article_info['themes'] or 'NONE'}")
                themes_found.update(article_info['themes'] or [])
        
        if themes_found:
            print(f"   📊 Themes found across articles: {', '.join(themes_found)}")
        else:
            print(f"   ⚠️  NO THEMES EXTRACTED for this entity's articles!")


async def check_theme_coverage():
    """Check how many recent articles have themes extracted."""
    print("\n" + "="*80)
    print("CHECKING THEME EXTRACTION COVERAGE")
    print("="*80)
    
    db = await mongo_manager.get_async_database()
    articles_collection = db.articles
    
    # Get recent articles (last 48 hours)
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=48)
    
    total_cursor = articles_collection.find({
        "published_at": {"$gte": cutoff_time}
    })
    total_count = await articles_collection.count_documents({
        "published_at": {"$gte": cutoff_time}
    })
    
    with_themes_cursor = articles_collection.find({
        "published_at": {"$gte": cutoff_time},
        "themes": {"$exists": True, "$ne": []}
    })
    with_themes_count = await articles_collection.count_documents({
        "published_at": {"$gte": cutoff_time},
        "themes": {"$exists": True, "$ne": []}
    })
    
    print(f"\n📊 Recent articles (last 48 hours):")
    print(f"   Total: {total_count}")
    print(f"   With themes: {with_themes_count}")
    print(f"   Without themes: {total_count - with_themes_count}")
    
    if total_count > 0:
        coverage = (with_themes_count / total_count) * 100
        print(f"   Coverage: {coverage:.1f}%")
        
        if coverage < 50:
            print(f"\n   ⚠️  LOW THEME COVERAGE! Many articles don't have themes extracted.")
            print(f"   This is likely why entities aren't being linked to narratives.")


async def check_narrative_entity_linking():
    """Check how narrative-entity linking works."""
    print("\n" + "="*80)
    print("CHECKING NARRATIVE-ENTITY LINKING LOGIC")
    print("="*80)
    
    db = await mongo_manager.get_async_database()
    narratives_collection = db.narratives
    entity_mentions_collection = db.entity_mentions
    
    # Get a regulatory narrative if it exists
    regulatory_narrative = await narratives_collection.find_one({"theme": "regulatory"})
    
    if regulatory_narrative:
        print(f"\n✅ Found 'regulatory' narrative:")
        print(f"   Title: {regulatory_narrative.get('title', 'N/A')}")
        print(f"   Entities: {regulatory_narrative.get('entities', [])}")
        print(f"   Article Count: {regulatory_narrative.get('article_count', 0)}")
        print(f"   Article IDs: {regulatory_narrative.get('article_ids', [])}")
        
        # Check entity mentions for these articles
        article_ids = regulatory_narrative.get('article_ids', [])
        if article_ids:
            print(f"\n   🔍 Checking entity mentions for {len(article_ids)} articles...")
            
            for article_id in article_ids[:3]:  # Check first 3
                # Find entity mentions for this article
                cursor = entity_mentions_collection.find({"article_id": article_id})
                mentions = []
                async for mention in cursor:
                    mentions.append(mention.get("entity"))
                
                print(f"      Article {article_id[:8]}... has {len(mentions)} entity mentions: {mentions[:5]}")
        
        # Check if SEC, Ripple, Binance are in the entities list
        entities = regulatory_narrative.get('entities', [])
        for entity in ['SEC', 'Ripple', 'Binance']:
            if entity in entities:
                print(f"   ✅ {entity} is linked to this narrative")
            else:
                print(f"   ❌ {entity} is NOT linked to this narrative")
    else:
        print("\n❌ No 'regulatory' narrative found!")
        print("   This could mean:")
        print("   1. Not enough articles with 'regulatory' theme")
        print("   2. Theme extraction isn't working properly")
        print("   3. Narrative detection hasn't run recently")


async def main():
    """Run all diagnostic checks."""
    print("\n🔍 NARRATIVE LINKING DIAGNOSTIC TOOL")
    print("="*80)
    
    await initialize_mongodb()
    
    try:
        await check_narratives()
        await check_problem_entities()
        await check_theme_coverage()
        await check_narrative_entity_linking()
        
        print("\n" + "="*80)
        print("DIAGNOSIS COMPLETE")
        print("="*80)
        
    finally:
        await mongo_manager.aclose()


if __name__ == "__main__":
    asyncio.run(main())
