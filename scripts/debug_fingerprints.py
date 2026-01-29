#!/usr/bin/env python3
"""
Debug script to check fingerprint data in existing narratives.
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from crypto_news_aggregator.db.mongodb import mongo_manager


async def check_fingerprints():
    """Check fingerprint data in existing narratives."""
    print("=" * 80)
    print("FINGERPRINT DEBUG - Checking Existing Narratives")
    print("=" * 80)
    print()
    
    db = await mongo_manager.get_async_database()
    narratives_collection = db.narratives
    
    # Get recent narratives
    cutoff = datetime.now(timezone.utc) - timedelta(days=14)
    cursor = narratives_collection.find({
        'last_updated': {'$gte': cutoff}
    }).sort('last_updated', -1).limit(10)
    
    narratives = await cursor.to_list(length=10)
    
    print(f"Checking {len(narratives)} recent narratives:")
    print()
    
    has_fingerprint = 0
    missing_fingerprint = 0
    
    for i, narrative in enumerate(narratives, 1):
        print(f"{i}. Narrative #{narrative.get('_id')}")
        print(f"   Title: {narrative.get('title', 'N/A')}")
        
        fingerprint = narrative.get('fingerprint')
        if fingerprint:
            has_fingerprint += 1
            print(f"   ✅ HAS FINGERPRINT:")
            print(f"      nucleus_entity: {fingerprint.get('nucleus_entity', 'N/A')}")
            print(f"      top_actors: {fingerprint.get('top_actors', [])}")
            print(f"      key_actions: {fingerprint.get('key_actions', [])}")
        else:
            missing_fingerprint += 1
            print(f"   ❌ MISSING FINGERPRINT")
            # Check legacy fields
            theme = narrative.get('theme')
            entities = narrative.get('entities', [])
            print(f"      Legacy theme: {theme}")
            print(f"      Legacy entities: {entities}")
        
        print()
    
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Narratives with fingerprint: {has_fingerprint}")
    print(f"Narratives without fingerprint: {missing_fingerprint}")
    print()
    
    if missing_fingerprint > 0:
        print("⚠️  WARNING: Some narratives are missing fingerprint data!")
        print("   This will cause matching to fail.")
        print("   Run backfill to populate fingerprints.")


if __name__ == "__main__":
    asyncio.run(check_fingerprints())
