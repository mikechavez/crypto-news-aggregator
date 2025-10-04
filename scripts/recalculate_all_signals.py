"""
Recalculate all signal scores with the fixed code.
"""
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from crypto_news_aggregator.services.signal_service import calculate_signal_score
from crypto_news_aggregator.db.operations.signal_scores import upsert_signal_score

async def main():
    client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))
    db = client[os.getenv('MONGODB_DB_NAME')]
    
    print("=" * 70)
    print("RECALCULATING ALL SIGNAL SCORES")
    print("=" * 70)
    
    # Get all entities with primary mentions in the last 7 days
    seven_days_ago = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7)
    
    pipeline = [
        {
            "$match": {
                "is_primary": True,
                "created_at": {"$gte": seven_days_ago}
            }
        },
        {
            "$group": {
                "_id": {
                    "entity": "$entity",
                    "entity_type": "$entity_type"
                }
            }
        },
        {"$sort": {"_id.entity": 1}}
    ]
    
    entities = []
    async for result in db.entity_mentions.aggregate(pipeline):
        entities.append(result["_id"])
    
    print(f"\nFound {len(entities)} entities with mentions in last 7 days\n")
    print(f"{'Entity':<30} {'Type':<15} {'Velocity':<10} {'Sources':<10} {'Score':<10}")
    print("-" * 70)
    
    results = []
    
    for i, entity_info in enumerate(entities, 1):
        entity = entity_info["entity"]
        entity_type = entity_info["entity_type"]
        
        try:
            # Calculate signal score with fixed code
            signal_data = await calculate_signal_score(entity)
            
            # Get first_seen timestamp
            first_mention = await db.entity_mentions.find_one(
                {"entity": entity, "is_primary": True},
                sort=[("created_at", 1)]
            )
            first_seen = first_mention["created_at"] if first_mention else datetime.now(timezone.utc)
            
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
            
            # Track for summary
            results.append({
                "entity": entity,
                "entity_type": entity_type,
                "velocity": signal_data["velocity"],
                "source_count": signal_data["source_count"],
                "score": signal_data["score"]
            })
            
            # Print progress
            entity_display = entity[:28] + ".." if len(entity) > 30 else entity
            print(f"{entity_display:<30} {entity_type:<15} {signal_data['velocity']:<10.2f} {signal_data['source_count']:<10} {signal_data['score']:<10.2f}")
            
        except Exception as e:
            print(f"{entity[:30]:<30} ERROR: {str(e)[:30]}")
    
    print("\n" + "=" * 70)
    print("SUMMARY STATISTICS")
    print("=" * 70)
    
    if results:
        source_counts = [r["source_count"] for r in results]
        velocities = [r["velocity"] for r in results]
        scores = [r["score"] for r in results]
        
        print(f"\nSource Count Distribution:")
        from collections import Counter
        source_dist = Counter(source_counts)
        for count in sorted(source_dist.keys()):
            print(f"  {count} sources: {source_dist[count]} entities")
        
        print(f"\nVelocity Stats:")
        print(f"  Min: {min(velocities):.2f}")
        print(f"  Max: {max(velocities):.2f}")
        print(f"  Avg: {sum(velocities)/len(velocities):.2f}")
        
        print(f"\nScore Stats:")
        print(f"  Min: {min(scores):.2f}")
        print(f"  Max: {max(scores):.2f}")
        print(f"  Avg: {sum(scores)/len(scores):.2f}")
        
        print(f"\nTop 10 by Signal Score:")
        top_10 = sorted(results, key=lambda x: x["score"], reverse=True)[:10]
        for r in top_10:
            print(f"  {r['entity']:<30} Score: {r['score']:.2f}, Velocity: {r['velocity']:.2f}, Sources: {r['source_count']}")
    
    print(f"\n✅ Recalculated {len(results)} signal scores")
    
    client.close()

asyncio.run(main())
