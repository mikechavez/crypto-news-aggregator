#!/usr/bin/env python3
"""
Check all signals in MongoDB to see what data exists.
"""
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

async def main():
    mongo_uri = os.getenv('MONGODB_URI')
    db_name = os.getenv('MONGODB_DB_NAME', 'crypto_news')
    
    print(f"Connecting to: {mongo_uri}")
    print(f"Database: {db_name}")
    print()
    
    client = AsyncIOMotorClient(mongo_uri)
    db = client[db_name]
    
    # List all collections
    print("=" * 70)
    print("AVAILABLE COLLECTIONS")
    print("=" * 70)
    collections = await db.list_collection_names()
    for coll in collections:
        count = await db[coll].count_documents({})
        print(f"  {coll}: {count} documents")
    print()
    
    # Get all signal_scores
    print("=" * 70)
    print("ALL SIGNAL_SCORES (showing all)")
    print("=" * 70)
    print()
    
    signals = await db.signal_scores.find({}).sort("signal_strength", -1).to_list(length=100)
    
    if signals:
        print(f"Found {len(signals)} signal scores:")
        for i, signal in enumerate(signals, 1):
            print(f"\n{i}. {signal.get('normalized_name', 'UNKNOWN')}")
            print(f"   - entity_type: {signal.get('entity_type')}")
            print(f"   - signal_strength: {signal.get('signal_strength')}")
            print(f"   - mention_count: {signal.get('mention_count')}")
            print(f"   - last_updated: {signal.get('last_updated')}")
            if signal.get('sources'):
                print(f"   - sources: {list(signal['sources'].keys())}")
    else:
        print("No signal scores found")
    
    print()
    print("=" * 70)
    print("SAMPLE ENTITY_MENTIONS (showing first 10)")
    print("=" * 70)
    print()
    
    mentions = await db.entity_mentions.find({}).limit(10).to_list(length=10)
    
    if mentions:
        print(f"Found entity mentions (showing first 10):")
        for i, mention in enumerate(mentions, 1):
            print(f"\n{i}. {mention.get('entity_name', 'UNKNOWN')}")
            print(f"   - normalized_name: {mention.get('normalized_name')}")
            print(f"   - entity_type: {mention.get('entity_type')}")
            print(f"   - article_id: {mention.get('article_id')}")
    else:
        print("No entity mentions found")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(main())
