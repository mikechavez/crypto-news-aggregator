#!/usr/bin/env python3
"""Quick script to verify narrative count after merge."""
import asyncio
import sys
import os

# Add src to path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, os.path.join(project_root, "src"))

from crypto_news_aggregator.db.mongodb import mongo_manager


async def main():
    await mongo_manager.initialize()
    db = await mongo_manager.get_async_database()
    
    count = await db.narratives.count_documents({})
    print(f"✅ Current narrative count: {count}")
    
    await mongo_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
