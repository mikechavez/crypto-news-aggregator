"""
Check organization entities and their signal scores.
"""
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))
    db = client[os.getenv('MONGODB_DB_NAME')]
    
    print("=" * 70)
    print("ORGANIZATION ENTITIES CHECK")
    print("=" * 70)
    
    # Get all organization entities with signal scores
    org_signals = await db.signal_scores.find({
        'entity_type': 'organization'
    }).sort('score', -1).to_list(100)
    
    print(f"\nOrganization entities with signal scores: {len(org_signals)}\n")
    
    if org_signals:
        print(f"{'Entity':<30} {'Velocity':<10} {'Sources':<10} {'Score':<10}")
        print("-" * 70)
        
        for signal in org_signals:
            entity = signal.get('entity', 'Unknown')
            velocity = signal.get('velocity', 0)
            source_count = signal.get('source_count', 0)
            score = signal.get('score', 0)
            
            print(f"{entity:<30} {velocity:<10.2f} {source_count:<10} {score:<10.2f}")
    
    # Check primary entity type distribution
    print("\n" + "=" * 70)
    print("PRIMARY ENTITY TYPE DISTRIBUTION")
    print("=" * 70)
    
    pipeline = [
        {'$match': {'is_primary': True}},
        {'$group': {'_id': '$entity_type', 'count': {'$sum': 1}}},
        {'$sort': {'count': -1}}
    ]
    
    print(f"\n{'Entity Type':<20} {'Count':<10}")
    print("-" * 30)
    
    async for result in db.entity_mentions.aggregate(pipeline):
        entity_type = result['_id']
        count = result['count']
        print(f"{entity_type:<20} {count:<10}")
    
    client.close()

asyncio.run(main())
