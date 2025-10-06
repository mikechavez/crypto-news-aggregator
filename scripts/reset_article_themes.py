#!/usr/bin/env python3
"""
Reset article themes to allow re-extraction with new theme categories.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from crypto_news_aggregator.db.mongodb import mongo_manager


async def reset_themes():
    """Reset all article themes."""
    
    await mongo_manager.initialize()
    
    db = await mongo_manager.get_async_database()
    articles_collection = db.articles
    
    # Remove themes field from all articles
    result = await articles_collection.update_many(
        {},
        {"$unset": {"themes": "", "themes_extracted_at": ""}}
    )
    
    print(f"Reset themes for {result.modified_count} articles")
    
    await mongo_manager.close()


if __name__ == "__main__":
    asyncio.run(reset_themes())
