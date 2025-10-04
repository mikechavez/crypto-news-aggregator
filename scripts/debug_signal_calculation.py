"""
Debug signal calculation issues - check raw data.
"""
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta, timezone

async def main():
    client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))
    db = client[os.getenv('MONGODB_DB_NAME')]
    
    # Pick a high-signal entity to test with
    test_entity = "Bitcoin"
    
    print(f"Debugging signal calculation for: {test_entity}\n")
    
    # 1. Check entity mentions
    mentions = await db.entity_mentions.find({
        'entity': test_entity,
        'is_primary': True
    }).limit(10).to_list(10)
    
    print(f"Sample entity mentions ({len(mentions)} found):")
    for m in mentions[:3]:
        created_at = m.get('created_at', 'MISSING')
        print(f"  source: {m.get('source', 'MISSING')}")
        print(f"  created_at: {created_at}")
        print(f"  created_at type: {type(created_at)}")
        print(f"  created_at timezone: {getattr(created_at, 'tzinfo', 'N/A')}")
        print(f"  sentiment: {m.get('sentiment', 'MISSING')}")
        print(f"  is_primary: {m.get('is_primary', 'MISSING')}")
        print()
    
    # 2. Check time distribution (use naive datetimes like the service does)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    one_hour_ago = now - timedelta(hours=1)
    twenty_four_hours_ago = now - timedelta(hours=24)
    seven_days_ago = now - timedelta(days=7)
    
    print(f"Current time (naive UTC): {now}")
    print(f"One hour ago: {one_hour_ago}")
    print(f"24 hours ago: {twenty_four_hours_ago}")
    
    recent_1h = await db.entity_mentions.count_documents({
        'entity': test_entity,
        'is_primary': True,
        'created_at': {'$gte': one_hour_ago}
    })
    
    recent_24h = await db.entity_mentions.count_documents({
        'entity': test_entity,
        'is_primary': True,
        'created_at': {'$gte': twenty_four_hours_ago}
    })
    
    week = await db.entity_mentions.count_documents({
        'entity': test_entity,
        'is_primary': True,
        'created_at': {'$gte': seven_days_ago}
    })
    
    print(f"\nMentions in last hour: {recent_1h}")
    print(f"Mentions in last 24 hours: {recent_24h}")
    print(f"Mentions in last 7 days: {week}")
    print(f"Velocity calculation: {recent_1h} / ({recent_24h} / 24) = {recent_1h / (recent_24h / 24) if recent_24h > 0 else 0}")
    
    # 3. Check unique sources
    sources = await db.entity_mentions.distinct('source', {
        'entity': test_entity,
        'is_primary': True
    })
    
    print(f"\nUnique sources: {len(sources)}")
    print(f"Sources: {sources}")
    
    # 4. Check signal_scores collection
    signal = await db.signal_scores.find_one({'entity': test_entity})
    
    if signal:
        print(f"\nStored signal score:")
        print(f"  velocity: {signal.get('velocity')}")
        print(f"  source_count: {signal.get('source_count')}")
        print(f"  signal_score: {signal.get('score')}")
    else:
        print(f"\nNo signal score found for {test_entity}")
    
    client.close()

asyncio.run(main())
