#!/usr/bin/env python3
"""
Test script for signal detection system.

This script:
1. Checks how many entities are in the database
2. Calculates signal scores for a sample of entities
3. Displays the top trending entities
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.crypto_news_aggregator.db.mongodb import initialize_mongodb, mongo_manager
from src.crypto_news_aggregator.services.signal_service import calculate_signal_score
from src.crypto_news_aggregator.db.operations.signal_scores import (
    upsert_signal_score,
    get_trending_entities,
)
from datetime import datetime, timezone


async def main():
    """Test signal detection with existing entities."""
    print("🚀 Testing Signal Detection System\n")
    
    # Initialize MongoDB
    await initialize_mongodb()
    print("✅ Connected to MongoDB\n")
    
    db = await mongo_manager.get_async_database()
    entity_mentions_collection = db.entity_mentions
    
    # Count total entities
    pipeline = [
        {"$group": {"_id": {"entity": "$entity", "entity_type": "$entity_type"}}},
        {"$count": "total"}
    ]
    
    count_result = []
    async for result in entity_mentions_collection.aggregate(pipeline):
        count_result.append(result)
    
    total_entities = count_result[0]["total"] if count_result else 0
    print(f"📊 Total unique entities in database: {total_entities}\n")
    
    # Get sample of entities to score
    print("🔍 Getting sample entities to score...")
    pipeline = [
        {"$group": {"_id": {"entity": "$entity", "entity_type": "$entity_type"}}},
        {"$limit": 20}  # Sample 20 entities
    ]
    
    entities_to_score = []
    async for result in entity_mentions_collection.aggregate(pipeline):
        entity_info = result["_id"]
        entities_to_score.append(entity_info)
    
    print(f"   Found {len(entities_to_score)} entities to score\n")
    
    # Calculate and store signal scores
    print("⚡ Calculating signal scores...")
    scored_count = 0
    
    for entity_info in entities_to_score:
        entity = entity_info["entity"]
        entity_type = entity_info["entity_type"]
        
        try:
            signal_data = await calculate_signal_score(entity)
            
            # Get first_seen timestamp
            first_mention = await entity_mentions_collection.find_one(
                {"entity": entity},
                sort=[("timestamp", 1)]
            )
            first_seen = first_mention["timestamp"] if first_mention else datetime.now(timezone.utc)
            
            # Store the signal score
            await upsert_signal_score(
                entity=entity,
                entity_type=entity_type,
                score=signal_data["score"],
                velocity=signal_data["velocity"],
                source_count=signal_data["source_count"],
                sentiment=signal_data["sentiment"],
                first_seen=first_seen,
            )
            
            scored_count += 1
            print(f"   ✓ {entity}: score={signal_data['score']:.2f}, velocity={signal_data['velocity']:.2f}, sources={signal_data['source_count']}")
            
        except Exception as exc:
            print(f"   ✗ Failed to score {entity}: {exc}")
    
    print(f"\n✅ Scored {scored_count} entities\n")
    
    # Get top trending entities
    print("🔥 Top 10 Trending Entities:\n")
    trending = await get_trending_entities(limit=10, min_score=0.0)
    
    if not trending:
        print("   No trending entities found")
    else:
        for i, signal in enumerate(trending, 1):
            print(f"{i}. {signal['entity']} ({signal['entity_type']})")
            print(f"   Score: {signal['score']:.2f}")
            print(f"   Velocity: {signal['velocity']:.2f}")
            print(f"   Sources: {signal['source_count']}")
            print(f"   Sentiment: {signal['sentiment']['avg']:.3f}")
            print()
    
    # Close MongoDB connection
    await mongo_manager.aclose()
    print("✅ Test complete!")


if __name__ == "__main__":
    asyncio.run(main())
