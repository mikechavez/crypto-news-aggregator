"""
Audit entity types to find what still needs classification.
"""
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))
    db = client[os.getenv('MONGODB_DB_NAME')]
    
    # Count by type
    old = await db.entity_mentions.count_documents({'entity_type': {'$in': ['project', 'ticker', 'event']}})
    new = await db.entity_mentions.count_documents({'entity_type': {'$in': ['cryptocurrency', 'blockchain', 'protocol', 'company', 'person', 'location', 'concept']}})
    
    print(f'Old classification: {old} mentions')
    print(f'New classification: {new} mentions')
    
    # Find entities with old types that appear in signal_scores
    signals_pipeline = [
        {'$lookup': {
            'from': 'entity_mentions',
            'localField': 'entity',
            'foreignField': 'entity',
            'as': 'mentions'
        }},
        {'$unwind': '$mentions'},
        {'$match': {'mentions.entity_type': {'$in': ['project', 'ticker', 'event']}}},
        {'$group': {'_id': '$entity', 'type': {'$first': '$mentions.entity_type'}}},
        {'$limit': 20}
    ]
    
    old_in_signals = await db.signal_scores.aggregate(signals_pipeline).to_list(20)
    
    if old_in_signals:
        print(f'\nEntities in signals with OLD types (sample):')
        for item in old_in_signals:
            print(f'  {item["_id"]:20} | type: {item["type"]}')
    
    client.close()

asyncio.run(main())
