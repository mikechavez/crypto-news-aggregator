"""
Check how fresh our data is.
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
    
    print("=" * 60)
    print("DATA FRESHNESS CHECK")
    print("=" * 60)
    
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    
    # Check different time windows
    time_windows = [
        ("1 hour", timedelta(hours=1)),
        ("6 hours", timedelta(hours=6)),
        ("24 hours", timedelta(hours=24)),
        ("7 days", timedelta(days=7)),
    ]
    
    print(f"\nCurrent time (UTC): {now}\n")
    
    print("ARTICLES:")
    for label, delta in time_windows:
        cutoff = now - delta
        count = await db.articles.count_documents({
            'created_at': {'$gte': cutoff}
        })
        print(f"  Last {label:10s}: {count:4d} articles")
    
    print("\nENTITY MENTIONS:")
    for label, delta in time_windows:
        cutoff = now - delta
        count = await db.entity_mentions.count_documents({
            'created_at': {'$gte': cutoff},
            'is_primary': True
        })
        print(f"  Last {label:10s}: {count:4d} primary mentions")
    
    # Check most recent article
    latest_article = await db.articles.find_one(
        {},
        sort=[('created_at', -1)]
    )
    
    if latest_article:
        age = now - latest_article['created_at']
        hours_old = age.total_seconds() / 3600
        print(f"\n📰 Most recent article:")
        print(f"   Title: {latest_article.get('title', 'N/A')[:70]}...")
        print(f"   Created: {latest_article['created_at']}")
        print(f"   Age: {hours_old:.1f} hours ago")
    
    # Check most recent mention
    latest_mention = await db.entity_mentions.find_one(
        {'is_primary': True},
        sort=[('created_at', -1)]
    )
    
    if latest_mention:
        age = now - latest_mention['created_at']
        hours_old = age.total_seconds() / 3600
        print(f"\n🏷️  Most recent entity mention:")
        print(f"   Entity: {latest_mention.get('entity')} ({latest_mention.get('entity_type')})")
        print(f"   Created: {latest_mention['created_at']}")
        print(f"   Age: {hours_old:.1f} hours ago")
    
    client.close()

asyncio.run(main())
