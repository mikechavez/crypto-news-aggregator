#!/usr/bin/env python3
"""
Debug entity extraction in detail.
"""

import asyncio
import sys
import os
from pathlib import Path
from bson import ObjectId

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from crypto_news_aggregator.db.mongodb import initialize_mongodb, mongo_manager


async def debug_extraction():
    """Debug entity extraction step by step."""
    print("\n🔍 DEBUGGING ENTITY EXTRACTION")
    print("="*80)
    
    db = await mongo_manager.get_async_database()
    articles_collection = db.articles
    entity_mentions_collection = db.entity_mentions
    
    # Get one article with a theme
    article = await articles_collection.find_one({
        "themes": {"$exists": True, "$ne": []}
    })
    
    if not article:
        print("❌ No articles with themes found")
        return
    
    article_id = article.get("_id")
    print(f"\n📄 Test Article:")
    print(f"   ID: {article_id}")
    print(f"   Type: {type(article_id)}")
    print(f"   Title: {article.get('title', 'N/A')[:60]}...")
    print(f"   Themes: {article.get('themes', [])}")
    
    # Try to find entity mentions
    print(f"\n🔍 Searching for entity mentions...")
    
    # Method 1: Direct ObjectId query
    print(f"\n   Method 1: Query with ObjectId directly")
    cursor = entity_mentions_collection.find({"article_id": article_id})
    mentions_1 = []
    async for mention in cursor:
        mentions_1.append(mention.get("entity"))
    print(f"   Found {len(mentions_1)} mentions: {mentions_1[:5]}")
    
    # Method 2: String query
    print(f"\n   Method 2: Query with string")
    cursor = entity_mentions_collection.find({"article_id": str(article_id)})
    mentions_2 = []
    async for mention in cursor:
        mentions_2.append(mention.get("entity"))
    print(f"   Found {len(mentions_2)} mentions: {mentions_2[:5]}")
    
    # Check what article_ids exist in entity_mentions
    print(f"\n🔍 Checking entity_mentions collection...")
    sample = await entity_mentions_collection.find_one({})
    if sample:
        sample_article_id = sample.get("article_id")
        print(f"   Sample entity mention:")
        print(f"      Entity: {sample.get('entity')}")
        print(f"      article_id: {sample_article_id}")
        print(f"      article_id type: {type(sample_article_id)}")
    
    # Count total entity mentions
    total_mentions = await entity_mentions_collection.count_documents({})
    print(f"\n   Total entity mentions in DB: {total_mentions}")
    
    # Check if any entity mentions match our article
    print(f"\n🔍 Checking if article {article_id} has ANY entity mentions...")
    
    # Try both ObjectId and string
    count_obj = await entity_mentions_collection.count_documents({"article_id": article_id})
    count_str = await entity_mentions_collection.count_documents({"article_id": str(article_id)})
    
    print(f"   Matches with ObjectId: {count_obj}")
    print(f"   Matches with string: {count_str}")
    
    if count_obj == 0 and count_str == 0:
        print(f"\n   ⚠️  This article has NO entity mentions!")
        print(f"   This could mean:")
        print(f"   1. Entity extraction hasn't run for this article")
        print(f"   2. Entity extraction failed for this article")
        print(f"   3. The article_id format changed between entity extraction and now")


async def check_entity_mention_coverage():
    """Check what percentage of articles have entity mentions."""
    print("\n\n📊 CHECKING ENTITY MENTION COVERAGE")
    print("="*80)
    
    db = await mongo_manager.get_async_database()
    articles_collection = db.articles
    entity_mentions_collection = db.entity_mentions
    
    # Get all unique article_ids from entity_mentions
    pipeline = [
        {"$group": {"_id": "$article_id"}},
        {"$count": "total"}
    ]
    
    result = await entity_mentions_collection.aggregate(pipeline).to_list(length=1)
    articles_with_mentions = result[0]["total"] if result else 0
    
    # Get total articles
    total_articles = await articles_collection.count_documents({})
    
    print(f"\n📊 Coverage:")
    print(f"   Total articles: {total_articles}")
    print(f"   Articles with entity mentions: {articles_with_mentions}")
    
    if total_articles > 0:
        coverage = (articles_with_mentions / total_articles) * 100
        print(f"   Coverage: {coverage:.1f}%")
        
        if coverage < 50:
            print(f"\n   ⚠️  LOW COVERAGE! Many articles don't have entity mentions.")


async def main():
    """Run debug."""
    await initialize_mongodb()
    
    try:
        await debug_extraction()
        await check_entity_mention_coverage()
        
        print("\n" + "="*80)
        print("DEBUG COMPLETE")
        print("="*80)
        
    finally:
        await mongo_manager.aclose()


if __name__ == "__main__":
    asyncio.run(main())
