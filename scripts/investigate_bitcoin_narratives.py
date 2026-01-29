#!/usr/bin/env python3
"""
Investigate why Bitcoin Market Volatility and Bitcoin Market Turbulence weren't merged.
"""

import asyncio
import sys
import os

# Add src to path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, os.path.join(project_root, "src"))

from crypto_news_aggregator.db.mongodb import mongo_manager
from crypto_news_aggregator.services.narrative_themes import calculate_fingerprint_similarity


async def investigate():
    """Investigate Bitcoin narratives."""
    db = await mongo_manager.get_async_database()
    narratives_collection = db.narratives
    
    # Find Bitcoin narratives
    cursor = narratives_collection.find({})
    bitcoin_narratives = []
    
    async for narrative in cursor:
        title = narrative.get('title', '')
        if 'Bitcoin' in title and ('Volatility' in title or 'Turbulence' in title):
            bitcoin_narratives.append(narrative)
    
    print(f"Found {len(bitcoin_narratives)} Bitcoin narratives with Volatility/Turbulence\n")
    print("=" * 80)
    
    for i, narrative in enumerate(bitcoin_narratives, 1):
        print(f"\n{i}. Title: {narrative.get('title')}")
        print(f"   Articles: {len(narrative.get('article_ids', []))}")
        print(f"   Lifecycle: {narrative.get('lifecycle_state')}")
        print(f"   Last Updated: {narrative.get('last_updated')}")
        
        # Get fingerprint
        fingerprint = narrative.get('narrative_fingerprint') or narrative.get('fingerprint')
        if fingerprint:
            print(f"\n   Fingerprint:")
            print(f"   - Nucleus: {fingerprint.get('nucleus_entity')}")
            print(f"   - Top Actors: {fingerprint.get('top_actors', [])[:5]}")
            print(f"   - Key Actions: {fingerprint.get('key_actions', [])[:3]}")
        
        # Check if merged
        if narrative.get('merged_at'):
            print(f"   ✅ Created via merge at {narrative.get('merged_at')}")
            print(f"      Merged from: {narrative.get('merged_from')}")
        
        if narrative.get('fingerprint_backfilled_at'):
            print(f"   🔄 Fingerprint backfilled at {narrative.get('fingerprint_backfilled_at')}")
    
    # Calculate similarity between all pairs
    if len(bitcoin_narratives) >= 2:
        print("\n" + "=" * 80)
        print("PAIRWISE SIMILARITY ANALYSIS")
        print("=" * 80)
        
        for i in range(len(bitcoin_narratives)):
            for j in range(i + 1, len(bitcoin_narratives)):
                n1 = bitcoin_narratives[i]
                n2 = bitcoin_narratives[j]
                
                fp1 = n1.get('narrative_fingerprint') or n1.get('fingerprint')
                fp2 = n2.get('narrative_fingerprint') or n2.get('fingerprint')
                
                if fp1 and fp2:
                    similarity = calculate_fingerprint_similarity(fp1, fp2)
                    
                    print(f"\n'{n1.get('title')[:50]}...'")
                    print(f"  vs")
                    print(f"'{n2.get('title')[:50]}...'")
                    print(f"\nSimilarity: {similarity:.3f}")
                    
                    # Determine threshold
                    from datetime import datetime, timezone, timedelta
                    now = datetime.now(timezone.utc)
                    recent_cutoff = now - timedelta(hours=48)
                    
                    last_updated1 = n1.get('last_updated')
                    last_updated2 = n2.get('last_updated')
                    
                    if last_updated1 and last_updated1.tzinfo is None:
                        last_updated1 = last_updated1.replace(tzinfo=timezone.utc)
                    if last_updated2 and last_updated2.tzinfo is None:
                        last_updated2 = last_updated2.replace(tzinfo=timezone.utc)
                    
                    threshold1 = 0.5 if (last_updated1 and last_updated1 >= recent_cutoff) else 0.6
                    threshold2 = 0.5 if (last_updated2 and last_updated2 >= recent_cutoff) else 0.6
                    threshold = min(threshold1, threshold2)
                    
                    print(f"Threshold: {threshold} ({'recent' if threshold == 0.5 else 'older'})")
                    
                    if similarity >= threshold:
                        print(f"✅ SHOULD MERGE (similarity {similarity:.3f} >= {threshold})")
                    else:
                        print(f"❌ SHOULD NOT MERGE (similarity {similarity:.3f} < {threshold})")
                    
                    # Show detailed breakdown
                    nucleus1 = fp1.get('nucleus_entity', '')
                    nucleus2 = fp2.get('nucleus_entity', '')
                    actors1 = set(fp1.get('top_actors', []))
                    actors2 = set(fp2.get('top_actors', []))
                    actions1 = set(fp1.get('key_actions', []))
                    actions2 = set(fp2.get('key_actions', []))
                    
                    print(f"\nBreakdown:")
                    print(f"  Nucleus match: {nucleus1} == {nucleus2} ? {nucleus1 == nucleus2}")
                    print(f"  Actor overlap: {len(actors1 & actors2)}/{len(actors1 | actors2)} = {len(actors1 & actors2) / len(actors1 | actors2) if actors1 | actors2 else 0:.3f}")
                    print(f"    Actors 1: {list(actors1)[:5]}")
                    print(f"    Actors 2: {list(actors2)[:5]}")
                    print(f"  Action overlap: {len(actions1 & actions2)}/{len(actions1 | actions2)} = {len(actions1 & actions2) / len(actions1 | actions2) if actions1 | actions2 else 0:.3f}")
                    print(f"    Actions 1: {list(actions1)[:3]}")
                    print(f"    Actions 2: {list(actions2)[:3]}")


async def main():
    """Main entry point."""
    try:
        print("🔌 Connecting to MongoDB...\n")
        await mongo_manager.initialize()
        
        await investigate()
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        print("\n\n🔌 Closing MongoDB connection...")
        await mongo_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
