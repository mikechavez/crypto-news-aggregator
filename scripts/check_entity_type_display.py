#!/usr/bin/env python3
"""
Check entity_type values in MongoDB signal_scores collection.
This script queries production MongoDB to see what entity_type values are stored.
"""
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

async def main():
    client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))
    db = client[os.getenv('MONGODB_DB_NAME', 'crypto_news')]
    
    print("=" * 70)
    print("CHECKING ENTITY_TYPE VALUES IN SIGNAL_SCORES")
    print("=" * 70)
    print()
    
    # Query for Bitcoin
    print("🔍 Searching for Bitcoin...")
    bitcoin_signals = await db.signal_scores.find({
        "normalized_name": "bitcoin"
    }).sort("last_updated", -1).limit(1).to_list(length=1)
    
    if bitcoin_signals:
        signal = bitcoin_signals[0]
        print(f"✓ Found Bitcoin signal:")
        print(f"  - normalized_name: {signal.get('normalized_name')}")
        print(f"  - entity_type: {signal.get('entity_type')}")
        print(f"  - signal_strength: {signal.get('signal_strength')}")
        print(f"  - mention_count: {signal.get('mention_count')}")
        print(f"  - last_updated: {signal.get('last_updated')}")
        print()
    else:
        print("✗ No Bitcoin signal found")
        print()
    
    # Query for FTX
    print("🔍 Searching for FTX...")
    ftx_signals = await db.signal_scores.find({
        "normalized_name": "ftx"
    }).sort("last_updated", -1).limit(1).to_list(length=1)
    
    if ftx_signals:
        signal = ftx_signals[0]
        print(f"✓ Found FTX signal:")
        print(f"  - normalized_name: {signal.get('normalized_name')}")
        print(f"  - entity_type: {signal.get('entity_type')}")
        print(f"  - signal_strength: {signal.get('signal_strength')}")
        print(f"  - mention_count: {signal.get('mention_count')}")
        print(f"  - last_updated: {signal.get('last_updated')}")
        print()
    else:
        print("✗ No FTX signal found")
        print()
    
    # Get a sample of all entity_type values in the collection
    print("=" * 70)
    print("ENTITY_TYPE DISTRIBUTION IN SIGNAL_SCORES")
    print("=" * 70)
    print()
    
    pipeline = [
        {"$group": {
            "_id": "$entity_type",
            "count": {"$sum": 1}
        }},
        {"$sort": {"count": -1}}
    ]
    
    entity_type_counts = await db.signal_scores.aggregate(pipeline).to_list(length=100)
    
    for item in entity_type_counts:
        entity_type = item['_id'] if item['_id'] else "NULL"
        count = item['count']
        print(f"  {entity_type}: {count}")
    
    print()
    print("=" * 70)
    print("CHECKING ENTITY_MENTIONS FOR COMPARISON")
    print("=" * 70)
    print()
    
    # Check entity_mentions for Bitcoin
    print("🔍 Checking entity_mentions for Bitcoin...")
    bitcoin_mentions = await db.entity_mentions.find({
        "normalized_name": "bitcoin"
    }).limit(3).to_list(length=3)
    
    if bitcoin_mentions:
        print(f"✓ Found {len(bitcoin_mentions)} Bitcoin mentions (showing first 3):")
        for i, mention in enumerate(bitcoin_mentions, 1):
            print(f"  Mention {i}:")
            print(f"    - entity_name: {mention.get('entity_name')}")
            print(f"    - normalized_name: {mention.get('normalized_name')}")
            print(f"    - entity_type: {mention.get('entity_type')}")
            print(f"    - article_id: {mention.get('article_id')}")
        print()
    else:
        print("✗ No Bitcoin mentions found")
        print()
    
    # Check entity_mentions for FTX
    print("🔍 Checking entity_mentions for FTX...")
    ftx_mentions = await db.entity_mentions.find({
        "normalized_name": "ftx"
    }).limit(3).to_list(length=3)
    
    if ftx_mentions:
        print(f"✓ Found {len(ftx_mentions)} FTX mentions (showing first 3):")
        for i, mention in enumerate(ftx_mentions, 1):
            print(f"  Mention {i}:")
            print(f"    - entity_name: {mention.get('entity_name')}")
            print(f"    - normalized_name: {mention.get('normalized_name')}")
            print(f"    - entity_type: {mention.get('entity_type')}")
            print(f"    - article_id: {mention.get('article_id')}")
        print()
    else:
        print("✗ No FTX mentions found")
        print()
    
    client.close()

if __name__ == "__main__":
    asyncio.run(main())
