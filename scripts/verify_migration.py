#!/usr/bin/env python3
"""Verify the source field migration."""

import asyncio
from crypto_news_aggregator.db.mongodb import mongo_manager


async def verify_migration():
    """Verify that entity mentions now have source field."""
    db = await mongo_manager.get_async_database()
    collection = db.entity_mentions
    
    # Count total mentions
    total = await collection.count_documents({})
    print(f"Total entity mentions: {total}")
    
    # Count mentions with source
    with_source = await collection.count_documents({"source": {"$exists": True, "$ne": None}})
    print(f"Mentions with source: {with_source}")
    
    # Count mentions without source
    without_source = await collection.count_documents({
        "$or": [
            {"source": {"$exists": False}},
            {"source": None}
        ]
    })
    print(f"Mentions without source: {without_source}")
    
    # Show sample mentions
    print("\nSample entity mentions:")
    async for mention in collection.find({}).limit(5):
        print(f"  - Entity: {mention.get('entity')}, Type: {mention.get('entity_type')}, Source: {mention.get('source')}")
    
    await mongo_manager.close()


if __name__ == "__main__":
    asyncio.run(verify_migration())
