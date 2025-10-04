"""
Check signal scores to verify source_count is between 1-5.
"""
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))
    db = client[os.getenv('MONGODB_DB_NAME')]
    
    print("Signal Scores with Source Counts:")
    print("=" * 60)
    
    # Get all signal scores sorted by score
    cursor = db.signal_scores.find({}).sort('score', -1)
    
    async for score in cursor:
        entity = score.get('entity')
        signal_score = score.get('score', 0)
        source_count = score.get('source_count', 0)
        velocity = score.get('velocity', 0)
        
        print(f"{entity:20s} | Score: {signal_score:5.2f} | Sources: {source_count} | Velocity: {velocity:5.2f}")
    
    # Check if any have source_count outside 1-5 range
    print("\n" + "=" * 60)
    invalid_count = await db.signal_scores.count_documents({
        '$or': [
            {'source_count': {'$lt': 1}},
            {'source_count': {'$gt': 5}}
        ]
    })
    
    if invalid_count > 0:
        print(f"⚠️  WARNING: {invalid_count} scores have source_count outside 1-5 range")
    else:
        print("✓ All source counts are within 1-5 range")
    
    client.close()

asyncio.run(main())
