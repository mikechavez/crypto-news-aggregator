#!/usr/bin/env python3
"""
Debug script to check article_id format mismatch between articles and entity_mentions.
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


async def check_article_id_formats():
    """Check if article_id formats match between collections."""
    print("\n🔍 CHECKING ARTICLE_ID FORMAT MISMATCH")
    print("="*80)
    
    db = await mongo_manager.get_async_database()
    narratives_collection = db.narratives
    entity_mentions_collection = db.entity_mentions
    articles_collection = db.articles
    
    # Get regulatory narrative
    regulatory_narrative = await narratives_collection.find_one({"theme": "regulatory"})
    
    if not regulatory_narrative:
        print("❌ No regulatory narrative found")
        return
    
    article_ids = regulatory_narrative.get('article_ids', [])
    print(f"\n📋 Regulatory narrative has {len(article_ids)} articles:")
    
    for article_id in article_ids[:3]:
        print(f"\n   Article ID: {article_id}")
        print(f"   Type: {type(article_id)}")
        print(f"   Length: {len(article_id)}")
        
        # Try to find the article
        article = await articles_collection.find_one({"_id": ObjectId(article_id)})
        if article:
            print(f"   ✅ Article found in articles collection")
            print(f"      Title: {article.get('title', 'N/A')[:60]}...")
            print(f"      Themes: {article.get('themes', [])}")
        else:
            print(f"   ❌ Article NOT found in articles collection")
        
        # Try to find entity mentions with string article_id
        print(f"\n   Searching entity_mentions with article_id='{article_id}' (string):")
        cursor = entity_mentions_collection.find({"article_id": article_id})
        mentions_str = []
        async for mention in cursor:
            mentions_str.append(mention.get("entity"))
        print(f"      Found {len(mentions_str)} mentions: {mentions_str[:5]}")
        
        # Try to find entity mentions with ObjectId article_id
        print(f"\n   Searching entity_mentions with article_id=ObjectId('{article_id}'):")
        try:
            cursor = entity_mentions_collection.find({"article_id": ObjectId(article_id)})
            mentions_obj = []
            async for mention in cursor:
                mentions_obj.append(mention.get("entity"))
            print(f"      Found {len(mentions_obj)} mentions: {mentions_obj[:5]}")
        except Exception as e:
            print(f"      ❌ Error: {e}")
        
        # Check what article_id format is actually in entity_mentions
        print(f"\n   Checking actual article_id formats in entity_mentions:")
        sample_mention = await entity_mentions_collection.find_one({})
        if sample_mention:
            sample_article_id = sample_mention.get("article_id")
            print(f"      Sample article_id: {sample_article_id}")
            print(f"      Type: {type(sample_article_id)}")
        
        print()


async def check_all_entity_mentions():
    """Check a sample of entity mentions to see article_id format."""
    print("\n📊 SAMPLING ENTITY_MENTIONS COLLECTION")
    print("="*80)
    
    db = await mongo_manager.get_async_database()
    entity_mentions_collection = db.entity_mentions
    
    cursor = entity_mentions_collection.find({}).limit(10)
    
    print("\nFirst 10 entity mentions:")
    async for i, mention in enumerate(cursor, 1):
        article_id = mention.get("article_id")
        entity = mention.get("entity")
        print(f"{i}. Entity: {entity}, article_id: {article_id} (type: {type(article_id).__name__})")


async def main():
    """Run diagnostics."""
    await initialize_mongodb()
    
    try:
        await check_article_id_formats()
        await check_all_entity_mentions()
    finally:
        await mongo_manager.aclose()


if __name__ == "__main__":
    asyncio.run(main())
