"""
Check if new articles have proper source tracking.
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
    
    # Check articles from last 5 minutes
    five_min_ago = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=5)
    
    recent_articles = await db.articles.find({
        'created_at': {'$gte': five_min_ago}
    }).to_list(10)
    
    print(f"Articles created in last 5 minutes: {len(recent_articles)}\n")
    
    if recent_articles:
        print("Sample articles with sources:")
        for a in recent_articles[:5]:
            print(f"  Source: {a.get('source'):15s} | {a.get('title', 'N/A')[:50]}...")
        
        # Check unique sources
        sources = set(a.get('source') for a in recent_articles)
        print(f"\nUnique sources: {sources}")
    else:
        print("No new articles yet. Still processing...")
    
    # Check entity mentions
    recent_mentions = await db.entity_mentions.find({
        'created_at': {'$gte': five_min_ago},
        'is_primary': True
    }).to_list(10)
    
    print(f"\nEntity mentions created in last 5 minutes: {len(recent_mentions)}")
    
    if recent_mentions:
        print("Sample mentions with sources:")
        for m in recent_mentions[:5]:
            print(f"  Source: {m.get('source'):15s} | Entity: {m.get('entity')}")
        
        # Check unique sources
        sources = set(m.get('source') for m in recent_mentions)
        print(f"\nUnique sources in mentions: {sources}")
    
    client.close()

asyncio.run(main())
