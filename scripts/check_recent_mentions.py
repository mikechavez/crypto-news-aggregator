"""
Check recent entity mentions.
"""
import asyncio
import os
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
load_dotenv()
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))
    db = client[os.getenv('MONGODB_DB_NAME')]
    
    # Check mentions in last 7 days
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    
    recent_count = await db.entity_mentions.count_documents({
        'created_at': {'$gte': seven_days_ago}
    })
    
    print(f"Entity mentions in last 7 days: {recent_count}")
    print(f"Cutoff date: {seven_days_ago}")
    
    # Check all mentions
    total_count = await db.entity_mentions.count_documents({})
    print(f"\nTotal entity mentions: {total_count}")
    
    # Show newest mentions
    print("\nNewest mentions:")
    cursor = db.entity_mentions.find({}).sort('created_at', -1).limit(5)
    async for mention in cursor:
        print(f"  {mention.get('entity')}: {mention.get('created_at')} (source: {mention.get('source')})")
    
    client.close()

asyncio.run(main())
