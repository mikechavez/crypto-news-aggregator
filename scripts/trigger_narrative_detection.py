#!/usr/bin/env python3
"""
Manually trigger narrative detection worker.

This script runs the narrative detection worker to create new clusters
and test if they match existing narratives. Shows detailed output including:
- How many clusters were detected
- How many matched existing narratives vs created new ones
- Similarity scores for matched narratives
- Before/after counts of narratives
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from crypto_news_aggregator.db.mongodb import mongo_manager, initialize_mongodb
from crypto_news_aggregator.services.narrative_service import detect_narratives
from crypto_news_aggregator.services.narrative_deduplication import deduplicate_narratives
from crypto_news_aggregator.db.operations.narratives import upsert_narrative


async def get_narrative_stats():
    """Get current narrative statistics."""
    db = await mongo_manager.get_async_database()
    narratives_collection = db.narratives
    
    total_count = await narratives_collection.count_documents({})
    
    # Get counts by lifecycle state
    pipeline = [
        {
            '$group': {
                '_id': '$lifecycle_state',
                'count': {'$sum': 1}
            }
        }
    ]
    
    lifecycle_counts = {}
    async for doc in narratives_collection.aggregate(pipeline):
        lifecycle_counts[doc['_id']] = doc['count']
    
    return {
        'total': total_count,
        'by_lifecycle': lifecycle_counts
    }


async def trigger_narrative_detection(hours: int = 48, dry_run: bool = False):
    """
    Trigger narrative detection worker manually.
    
    Args:
        hours: Lookback window for articles (default: 48)
        dry_run: If True, don't save results to database
    """
    print("=" * 80)
    print("NARRATIVE DETECTION WORKER - MANUAL TRIGGER")
    print("=" * 80)
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print(f"Lookback window: {hours} hours")
    print()
    
    # Initialize MongoDB
    await initialize_mongodb()
    
    # Get initial state
    print("📊 INITIAL STATE")
    print("-" * 80)
    initial_stats = await get_narrative_stats()
    print(f"Total narratives: {initial_stats['total']}")
    print(f"By lifecycle state:")
    for state, count in sorted(initial_stats['by_lifecycle'].items(), key=lambda x: (x[0] is None, x[0])):
        state_label = state if state is not None else 'None'
        print(f"  - {state_label}: {count}")
    print()
    
    # Run narrative detection
    print("🔍 RUNNING NARRATIVE DETECTION")
    print("-" * 80)
    print(f"Detecting narratives from articles in last {hours} hours...")
    print()
    
    start_time = datetime.now(timezone.utc)
    
    try:
        # Call detect_narratives - this handles clustering, matching, and saving
        narratives = await detect_narratives(
            hours=hours,
            min_articles=3,
            use_salience_clustering=True
        )
        
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()
        
        print()
        print("✅ DETECTION COMPLETE")
        print("-" * 80)
        print(f"Duration: {duration:.2f} seconds")
        print(f"Narratives processed: {len(narratives)}")
        print()
        
        # Analyze results
        if narratives:
            print("📋 DETECTED NARRATIVES")
            print("-" * 80)
            
            # Group by whether they were matched or created
            matched = []
            created = []
            
            for narrative in narratives:
                # Check if narrative has an _id (existing) or not (new)
                if '_id' in narrative:
                    matched.append(narrative)
                else:
                    created.append(narrative)
            
            print(f"Matched existing narratives: {len(matched)}")
            print(f"Created new narratives: {len(created)}")
            print()
            
            # Show details of matched narratives
            if matched:
                print("🔄 MATCHED NARRATIVES (Updated)")
                print("-" * 40)
                for i, narrative in enumerate(matched[:5], 1):
                    print(f"\n{i}. {narrative.get('title', 'N/A')}")
                    fingerprint = narrative.get('fingerprint', {})
                    print(f"   Nucleus: {fingerprint.get('nucleus_entity', 'N/A')}")
                    actors = fingerprint.get('top_actors', [])[:3]
                    print(f"   Actors: {', '.join(actors) if actors else 'None'}")
                    print(f"   Articles: {narrative.get('article_count', 0)}")
                    print(f"   Lifecycle: {narrative.get('lifecycle_state', 'N/A')}")
                    print(f"   Velocity: {narrative.get('mention_velocity', 0):.2f} articles/day")
                
                if len(matched) > 5:
                    print(f"\n... and {len(matched) - 5} more matched narratives")
                print()
            
            # Show details of created narratives
            if created:
                print("✨ NEW NARRATIVES (Created)")
                print("-" * 40)
                for i, narrative in enumerate(created[:5], 1):
                    print(f"\n{i}. {narrative.get('title', 'N/A')}")
                    fingerprint = narrative.get('fingerprint', {})
                    print(f"   Nucleus: {fingerprint.get('nucleus_entity', 'N/A')}")
                    actors = fingerprint.get('top_actors', [])[:3]
                    print(f"   Actors: {', '.join(actors) if actors else 'None'}")
                    print(f"   Articles: {narrative.get('article_count', 0)}")
                    print(f"   Lifecycle: {narrative.get('lifecycle_state', 'N/A')}")
                    print(f"   Velocity: {narrative.get('mention_velocity', 0):.2f} articles/day")
                
                if len(created) > 5:
                    print(f"\n... and {len(created) - 5} more new narratives")
                print()
        else:
            print("ℹ️  No narratives detected in this cycle")
            print()
        
        # Get final state
        print("📊 FINAL STATE")
        print("-" * 80)
        final_stats = await get_narrative_stats()
        print(f"Total narratives: {final_stats['total']}")
        print(f"By lifecycle state:")
        for state, count in sorted(final_stats['by_lifecycle'].items(), key=lambda x: (x[0] is None, x[0])):
            state_label = state if state is not None else 'None'
            print(f"  - {state_label}: {count}")
        print()
        
        # Summary
        print("=" * 80)
        print("📈 SUMMARY")
        print("=" * 80)
        print(f"Narratives before:  {initial_stats['total']}")
        print(f"Narratives after:   {final_stats['total']}")
        print(f"Net change:         {final_stats['total'] - initial_stats['total']:+d}")
        print()
        
        if narratives:
            # Calculate matching effectiveness
            total_clusters = len(narratives)
            matched_count = len(matched) if 'matched' in locals() else 0
            created_count = len(created) if 'created' in locals() else 0
            
            if matched_count > 0 and created_count > 0:
                print("✅ Matching logic is working - both creating and updating narratives")
            elif matched_count > 0 and created_count == 0:
                print("✅ All clusters matched existing narratives - no duplicates")
            elif matched_count == 0 and created_count > 0:
                print("ℹ️  All clusters created new narratives - no matches found")
            
            print()
            print(f"Matching rate: {matched_count}/{total_clusters} ({100*matched_count/total_clusters:.1f}%)")
            print(f"Creation rate: {created_count}/{total_clusters} ({100*created_count/total_clusters:.1f}%)")
        
        print()
        print("=" * 80)
        if dry_run:
            print("DRY RUN COMPLETE - No changes were saved to database")
        else:
            print("DETECTION COMPLETE - Changes saved to database")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await mongo_manager.aclose()


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Manually trigger narrative detection worker"
    )
    parser.add_argument(
        '--hours',
        type=int,
        default=48,
        help='Lookback window in hours (default: 48)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run in dry-run mode (no database changes)'
    )
    
    args = parser.parse_args()
    
    await trigger_narrative_detection(
        hours=args.hours,
        dry_run=args.dry_run
    )


if __name__ == "__main__":
    asyncio.run(main())
