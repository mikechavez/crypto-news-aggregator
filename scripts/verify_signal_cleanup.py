"""
Verify that concept entities are not in signal_scores.
"""
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))
    db = client[os.getenv('MONGODB_DB_NAME')]
    
    # Check if Pilot Program is in signals
    pp_signal = await db.signal_scores.find_one({'entity': 'Pilot Program'})
    if pp_signal:
        print(f'❌ Pilot Program found in signals: {pp_signal}')
    else:
        print('✅ Pilot Program NOT in signals (correct!)')
    
    # Check other concept entities
    concepts = ['Ai', 'Web3', 'DeFi']
    for concept in concepts:
        signal = await db.signal_scores.find_one({'entity': concept})
        if signal:
            print(f'❌ {concept} found in signals')
        else:
            print(f'✅ {concept} NOT in signals')
    
    # Show sample of what IS in signals
    print('\nSample entities in signals:')
    async for doc in db.signal_scores.find().limit(10):
        print(f'  {doc["entity"]:25} | type: {doc.get("entity_type", "N/A")}')
    
    # Count by entity type in signals
    print('\nSignal scores by entity type:')
    pipeline = [
        {'$group': {'_id': '$entity_type', 'count': {'$sum': 1}}},
        {'$sort': {'count': -1}}
    ]
    async for result in db.signal_scores.aggregate(pipeline):
        print(f'  {result["_id"]:20} : {result["count"]} entities')
    
    client.close()

asyncio.run(main())
