"""
Test salience-based clustering with actual production articles.
"""
import asyncio
import sys
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta, timezone
import os

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from crypto_news_aggregator.services.narrative_service import detect_narratives
from crypto_news_aggregator.db.mongodb import mongo_manager

async def test_with_real_data():
    """Test clustering on real articles from last 48 hours."""
    
    print("🔌 Connecting to MongoDB...")
    await mongo_manager.initialize()
    
    # Get article count
    db = await mongo_manager.get_async_database()
    articles_collection = db.articles
    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
    article_count = await articles_collection.count_documents({
        "published_at": {"$gte": cutoff}
    })
    
    print(f"📊 Found {article_count} articles in last 48h\n")
    
    # Run salience-based clustering
    print("🔄 Running salience-based narrative detection...")
    narratives = await detect_narratives(
        hours=48,
        min_articles=3,
        use_salience_clustering=True
    )
    
    print(f"\n✅ Generated {len(narratives)} narratives\n")
    
    # Display results
    print("=" * 80)
    print("NARRATIVE RESULTS")
    print("=" * 80)
    
    for i, narrative in enumerate(narratives, 1):
        print(f"\n{i}. {narrative.get('title', 'Unknown')}")
        print(f"   Nucleus: {narrative.get('theme', 'N/A')}")  # theme field stores nucleus
        print(f"   Articles: {narrative.get('article_count', 0)}")
        print(f"   Entities: {', '.join(narrative.get('entities', [])[:5])}")
        print(f"   Lifecycle: {narrative.get('lifecycle', 'N/A')}")
        print(f"   Velocity: {narrative.get('mention_velocity', 0):.2f}")
    
    # Validation checks
    print("\n" + "=" * 80)
    print("VALIDATION CHECKS")
    print("=" * 80)
    
    # Check 1: Reasonable narrative count
    if 10 <= len(narratives) <= 20:
        print("✅ Narrative count in expected range (10-20)")
    else:
        print(f"⚠️  Narrative count {len(narratives)} outside expected range (10-20)")
    
    # Check 2: No duplicates
    titles = [n.get('title', '') for n in narratives]
    if len(titles) == len(set(titles)):
        print("✅ No duplicate narrative titles")
    else:
        print(f"⚠️  Found duplicate titles")
    
    # Check 3: Proper article distribution
    article_counts = [n.get('article_count', 0) for n in narratives]
    avg_articles = sum(article_counts) / len(article_counts) if article_counts else 0
    print(f"✅ Average {avg_articles:.1f} articles per narrative")
    print(f"   Range: {min(article_counts, default=0)}-{max(article_counts, default=0)} articles")
    
    # Check 4: Bitcoin not in every narrative
    bitcoin_narratives = sum(
        1 for n in narratives 
        if 'Bitcoin' in n.get('entities', []) or 
           'Bitcoin' in n.get('title', '') or
           n.get('theme') == 'Bitcoin'
    )
    bitcoin_pct = (bitcoin_narratives / len(narratives) * 100) if narratives else 0
    print(f"   Bitcoin in {bitcoin_narratives}/{len(narratives)} narratives ({bitcoin_pct:.0f}%)")
    
    if bitcoin_pct < 50:
        print("✅ Bitcoin not dominating narratives")
    else:
        print("⚠️  Bitcoin appearing in too many narratives")
    
    await mongo_manager.close()
    
    return narratives

if __name__ == "__main__":
    asyncio.run(test_with_real_data())
