#!/usr/bin/env python3
"""
Check article themes status.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from crypto_news_aggregator.db.mongodb import mongo_manager


async def check_themes():
    """Check article themes status."""
    
    await mongo_manager.initialize()
    
    db = await mongo_manager.get_async_database()
    articles_collection = db.articles
    
    # Count total articles
    total = await articles_collection.count_documents({})
    print(f"Total articles: {total}")
    
    # Count articles with themes
    with_themes = await articles_collection.count_documents({"themes": {"$exists": True, "$ne": []}})
    print(f"Articles with themes: {with_themes}")
    
    # Count recent articles (last 48 hours)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
    recent = await articles_collection.count_documents({"published_at": {"$gte": cutoff}})
    print(f"Recent articles (48h): {recent}")
    
    # Count recent articles with themes
    recent_with_themes = await articles_collection.count_documents({
        "published_at": {"$gte": cutoff},
        "themes": {"$exists": True, "$ne": []}
    })
    print(f"Recent articles with themes: {recent_with_themes}")
    
    # Sample a few recent articles
    print("\nSample recent articles:")
    cursor = articles_collection.find({"published_at": {"$gte": cutoff}}).limit(5)
    async for article in cursor:
        print(f"\nTitle: {article.get('title', 'N/A')[:80]}")
        print(f"  Published: {article.get('published_at')}")
        print(f"  Themes: {article.get('themes', 'None')}")
    
    await mongo_manager.close()


if __name__ == "__main__":
    asyncio.run(check_themes())
