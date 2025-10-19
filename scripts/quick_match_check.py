#!/usr/bin/env python3
"""
Quick check of narrative matching - just test similarity calculation directly.
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from crypto_news_aggregator.db.mongodb import mongo_manager
from crypto_news_aggregator.services.narrative_themes import calculate_fingerprint_similarity


async def quick_check():
    """Quick check of matching logic."""
    print("=" * 80)
    print("QUICK MATCH CHECK")
    print("=" * 80)
    print()
    
    db = await mongo_manager.get_async_database()
    narratives_collection = db.narratives
    
    # Get recent narratives
    cutoff = datetime.now(timezone.utc) - timedelta(days=3)
    cursor = narratives_collection.find({
        'last_updated': {'$gte': cutoff}
    }).sort('last_updated', -1).limit(20)
    
    narratives = await cursor.to_list(length=20)
    
    print(f"Found {len(narratives)} recent narratives (last 3 days)")
    print()
    
    # Test: Create a fingerprint that should match "Bitcoin" narrative
    test_fingerprint = {
        'nucleus_entity': 'Bitcoin',
        'top_actors': ['Bitcoin', 'Ethereum', 'Traders'],
        'key_actions': []
    }
    
    print("TEST FINGERPRINT (should match Bitcoin narrative):")
    print(f"  nucleus_entity: {test_fingerprint['nucleus_entity']}")
    print(f"  top_actors: {test_fingerprint['top_actors']}")
    print()
    
    print("CHECKING SIMILARITY WITH RECENT NARRATIVES:")
    print("-" * 80)
    
    best_match = None
    best_score = 0.0
    
    for narrative in narratives:
        fingerprint = narrative.get('fingerprint')
        if not fingerprint:
            continue
        
        nucleus = fingerprint.get('nucleus_entity', '')
        actors = fingerprint.get('top_actors', [])
        
        similarity = calculate_fingerprint_similarity(test_fingerprint, fingerprint)
        
        if similarity > 0:
            print(f"✓ {narrative.get('title')[:60]}")
            print(f"  Nucleus: {nucleus}")
            print(f"  Actors: {actors[:3]}")
            print(f"  Similarity: {similarity:.3f}")
            print()
        
        if similarity > best_score:
            best_score = similarity
            best_match = narrative
    
    print("=" * 80)
    print("RESULT")
    print("=" * 80)
    
    if best_score >= 0.6:
        print(f"✅ MATCHING WORKS!")
        print(f"   Best match: {best_match.get('title')}")
        print(f"   Score: {best_score:.3f} (threshold: 0.6)")
    else:
        print(f"❌ MATCHING BROKEN!")
        if best_match:
            print(f"   Best candidate: {best_match.get('title')}")
            print(f"   Score: {best_score:.3f} < 0.6 (threshold)")
        else:
            print(f"   No matches found at all")


if __name__ == "__main__":
    asyncio.run(quick_check())
