"""Check narrative data status for articles."""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))

from crypto_news_aggregator.db.mongodb import mongo_manager


async def check_status():
    """Check narrative data status."""
    await mongo_manager.initialize()
    db = await mongo_manager.get_async_database()
    articles_collection = db.articles
    
    # Check last 48 hours
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=48)
    
    # Total articles in last 48h
    total = await articles_collection.count_documents({
        "published_at": {"$gte": cutoff_time}
    })
    
    # Articles with narrative data
    with_narrative = await articles_collection.count_documents({
        "published_at": {"$gte": cutoff_time},
        "narrative_summary": {"$exists": True, "$ne": None},
        "narrative_hash": {"$exists": True, "$ne": None}
    })
    
    # Articles missing narrative data
    missing_narrative = await articles_collection.count_documents({
        "published_at": {"$gte": cutoff_time},
        "$or": [
            {"narrative_summary": {"$exists": False}},
            {"narrative_summary": None},
            {"narrative_hash": {"$exists": False}},
            {"narrative_hash": None}
        ]
    })
    
    # Check older articles (7 days)
    cutoff_7d = datetime.now(timezone.utc) - timedelta(days=7)
    total_7d = await articles_collection.count_documents({
        "published_at": {"$gte": cutoff_7d}
    })
    
    missing_7d = await articles_collection.count_documents({
        "published_at": {"$gte": cutoff_7d},
        "$or": [
            {"narrative_summary": {"$exists": False}},
            {"narrative_summary": None},
            {"narrative_hash": {"$exists": False}},
            {"narrative_hash": None}
        ]
    })
    
    print(f"\n📊 Narrative Data Status Report")
    print(f"=" * 50)
    print(f"\n⏱️  Last 48 hours:")
    print(f"   Total articles: {total}")
    print(f"   With narrative data: {with_narrative}")
    print(f"   Missing narrative data: {missing_narrative}")
    if total > 0:
        print(f"   Coverage: {with_narrative/total*100:.1f}%")
    
    print(f"\n⏱️  Last 7 days:")
    print(f"   Total articles: {total_7d}")
    print(f"   Missing narrative data: {missing_7d}")
    if total_7d > 0:
        print(f"   Coverage: {(total_7d-missing_7d)/total_7d*100:.1f}%")
    
    # Sample a few articles to show their status
    print(f"\n📄 Sample of recent articles:")
    cursor = articles_collection.find({
        "published_at": {"$gte": cutoff_time}
    }).sort("published_at", -1).limit(5)
    
    articles = await cursor.to_list(length=5)
    for article in articles:
        has_summary = bool(article.get("narrative_summary"))
        has_hash = bool(article.get("narrative_hash"))
        has_actors = bool(article.get("actors"))
        print(f"\n   Title: {article.get('title', 'N/A')[:60]}...")
        print(f"   Published: {article.get('published_at')}")
        print(f"   Has narrative_summary: {has_summary}")
        print(f"   Has narrative_hash: {has_hash}")
        print(f"   Has actors: {has_actors}")
    
    await mongo_manager.close()


if __name__ == "__main__":
    asyncio.run(check_status())
