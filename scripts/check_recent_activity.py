"""
Check for recent activity in the database.
"""
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone, timedelta

async def main():
    client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))
    db = client[os.getenv('MONGODB_DB_NAME')]
    
    print("Checking recent database activity...\n")
    
    # Check recent articles (last 10 minutes)
    ten_min_ago = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=10)
    
    recent_articles = await db.articles.count_documents({
        'created_at': {'$gte': ten_min_ago}
    })
    
    recent_mentions = await db.entity_mentions.count_documents({
        'created_at': {'$gte': ten_min_ago}
    })
    
    print(f"📰 Articles created in last 10 min: {recent_articles}")
    print(f"🏷️  Entity mentions created in last 10 min: {recent_mentions}")
    
    if recent_articles > 0:
        print("\n✅ RSS fetch is working - new articles are being created!")
        
        # Show sample
        sample = await db.articles.find_one({'created_at': {'$gte': ten_min_ago}})
        if sample:
            print(f"\nSample article:")
            print(f"  Title: {sample.get('title', 'N/A')[:80]}...")
            print(f"  Source: {sample.get('source', 'N/A')}")
            print(f"  Created: {sample.get('created_at', 'N/A')}")
    
    if recent_mentions > 0:
        print("\n✅ Entity extraction is working - new mentions are being created!")
        
        # Show sample entities
        mentions = await db.entity_mentions.find({
            'created_at': {'$gte': ten_min_ago},
            'is_primary': True
        }).limit(5).to_list(5)
        
        if mentions:
            print(f"\nSample entities extracted:")
            for m in mentions:
                print(f"  - {m.get('entity')} ({m.get('entity_type')}) - {m.get('sentiment')}")
    
    if recent_articles == 0 and recent_mentions == 0:
        print("\n⏳ No recent activity yet. RSS fetch may still be in progress...")
        print("   Or all articles may be duplicates (already in database)")
    
    client.close()

asyncio.run(main())
