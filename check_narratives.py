import asyncio
import os
from src.crypto_news_aggregator.db.mongodb import mongo_manager

async def check_narratives():
    # Get database from existing mongo manager
    db = await mongo_manager.get_async_database()
    narratives = db.narratives
    
    # Get first 5 narratives
    cursor = narratives.find(
        {"lifecycle_state": {"$in": ["emerging", "rising", "hot", "cooling", "reactivated"]}}
    ).limit(5)
    
    async for narrative in cursor:
        print(f"\nNarrative: {narrative.get('theme')}")
        print(f"  Title: {narrative.get('title')}")
        print(f"  Article count: {narrative.get('article_count')}")
        article_ids = narrative.get('article_ids', [])
        print(f"  Article IDs count: {len(article_ids)}")
        if article_ids:
            print(f"  Article IDs (first 3): {article_ids[:3]}")
        else:
            print(f"  ⚠️ NO ARTICLE_IDS!")

asyncio.run(check_narratives())
