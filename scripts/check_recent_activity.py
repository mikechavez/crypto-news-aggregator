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
    
    # Check recent articles and mentions (last 2 hours)
    two_hours_ago = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=2)
    
    recent_articles = await db.articles.count_documents({
        'created_at': {'$gte': two_hours_ago}
    })
    
    recent_mentions = await db.entity_mentions.count_documents({
        'created_at': {'$gte': two_hours_ago}
    })
    
    print(f"Articles in last 2 hours: {recent_articles}")
    print(f"Entity mentions in last 2 hours: {recent_mentions}")
    
    # Get sample mentions with entity name and timestamp
    if recent_mentions > 0:
        mentions = await db.entity_mentions.find({
            'created_at': {'$gte': two_hours_ago}
        }).sort('created_at', -1).limit(5).to_list(5)
        
        print("\nSample mentions:")
        for m in mentions:
            entity_name = m.get('entity', 'N/A')
            created_at = m.get('created_at', 'N/A')
            entity_type = m.get('entity_type', 'N/A')
            is_primary = m.get('is_primary', False)
            print(f"  - {entity_name} ({entity_type}, primary={is_primary}) at {created_at}")
    else:
        print("\nSample mentions: []")
    
    # Show sample articles
    if recent_articles > 0:
        print("\nSample articles:")
        articles = await db.articles.find({
            'created_at': {'$gte': two_hours_ago}
        }).sort('created_at', -1).limit(3).to_list(3)
        
        for article in articles:
            print(f"  - {article.get('title', 'N/A')[:80]}")
            print(f"    Source: {article.get('source', 'N/A')}, Created: {article.get('created_at', 'N/A')}")
    
    # Status summary
    print("\n" + "="*60)
    if recent_articles > 0 and recent_mentions > 0:
        print("✅ RSS fetcher is working AND entity extraction is running")
    elif recent_articles > 0 and recent_mentions == 0:
        print("⚠️  RSS fetcher is working but NO entity mentions created")
        print("   This suggests entity extraction may be stuck or disabled")
    elif recent_articles == 0:
        print("❌ No new articles in last 2 hours")
        print("   RSS fetcher may be stuck or all articles are duplicates")
    
    client.close()

asyncio.run(main())
