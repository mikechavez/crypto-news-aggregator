#!/usr/bin/env python3
"""Quick script to verify signal scores backfill."""

import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from crypto_news_aggregator.db.mongodb import initialize_mongodb, mongo_manager


async def main():
    await initialize_mongodb()
    db = await mongo_manager.get_async_database()
    
    # Count total signal scores
    count = await db.signal_scores.count_documents({})
    print(f"Total signal scores: {count}")
    
    # Get a sample record
    sample = await db.signal_scores.find_one({})
    if sample:
        print(f"\nSample record fields: {list(sample.keys())}")
        print(f"\nSample entity: {sample.get('entity')}")
        print(f"  - 24h score: {sample.get('score_24h')}")
        print(f"  - 7d score: {sample.get('score_7d')}")
        print(f"  - 30d score: {sample.get('score_30d')}")
    
    # Count records with multi-timeframe data
    with_24h = await db.signal_scores.count_documents({"score_24h": {"$exists": True}})
    with_7d = await db.signal_scores.count_documents({"score_7d": {"$exists": True}})
    with_30d = await db.signal_scores.count_documents({"score_30d": {"$exists": True}})
    
    print(f"\nRecords with multi-timeframe scores:")
    print(f"  - 24h: {with_24h}")
    print(f"  - 7d: {with_7d}")
    print(f"  - 30d: {with_30d}")
    
    await mongo_manager.aclose()


if __name__ == "__main__":
    asyncio.run(main())
