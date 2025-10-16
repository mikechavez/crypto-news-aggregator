#!/usr/bin/env python3
"""
Create test dormant narratives for resurrection feature testing.

This script converts some existing narratives to dormant state by:
- Setting their last_updated to 10 days ago
- Setting lifecycle_state to 'dormant'
- Adding dormant state to lifecycle_history
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from crypto_news_aggregator.db.mongodb import mongo_manager, initialize_mongodb


async def create_test_dormant_narratives(count: int = 5):
    """
    Create test narratives in dormant state for resurrection testing.
    
    Args:
        count: Number of narratives to convert to dormant (default: 5)
    """
    print("=" * 80)
    print("CREATE TEST DORMANT NARRATIVES")
    print("=" * 80)
    print(f"Converting {count} narratives to dormant state for testing...")
    print()
    
    await initialize_mongodb()
    db = await mongo_manager.get_async_database()
    
    # Find some existing narratives to convert to dormant
    narratives = await db.narratives.find(
        {'lifecycle_state': {'$in': ['emerging', 'hot', 'rising']}}
    ).limit(count).to_list(length=count)
    
    if not narratives:
        print('❌ No narratives found to convert')
        await mongo_manager.aclose()
        return
    
    print(f'Found {len(narratives)} narratives to convert:')
    print()
    
    converted_count = 0
    
    for narrative in narratives:
        # Set last_updated to 10 days ago
        ten_days_ago = datetime.now(timezone.utc) - timedelta(days=10)
        
        # Update lifecycle state to dormant and add to history
        lifecycle_history = narrative.get('lifecycle_history', [])
        lifecycle_history.append({
            'state': 'dormant',
            'timestamp': ten_days_ago,
            'article_count': narrative.get('article_count', 0),
            'mention_velocity': 0.0
        })
        
        await db.narratives.update_one(
            {'_id': narrative['_id']},
            {
                '$set': {
                    'lifecycle_state': 'dormant',
                    'last_updated': ten_days_ago,
                    'lifecycle_history': lifecycle_history
                }
            }
        )
        
        title = narrative.get('title', 'N/A')
        print(f"  ✓ {title[:70]}")
        print(f"    Previous state: {narrative.get('lifecycle_state', 'N/A')}")
        print(f"    New state: dormant")
        print(f"    Last updated: {ten_days_ago.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        converted_count += 1
    
    print("=" * 80)
    print(f"✅ Successfully created {converted_count} dormant narratives for testing")
    print("=" * 80)
    print()
    print("Next steps:")
    print("1. Run narrative detection to reactivate these narratives:")
    print("   poetry run python scripts/trigger_narrative_detection.py --hours 24")
    print()
    print("2. Check resurrections API:")
    print("   curl http://localhost:8000/api/v1/narratives/resurrections?limit=10&days=7")
    print()
    
    await mongo_manager.aclose()


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Create test dormant narratives for resurrection testing"
    )
    parser.add_argument(
        '--count',
        type=int,
        default=5,
        help='Number of narratives to convert to dormant (default: 5)'
    )
    
    args = parser.parse_args()
    
    await create_test_dormant_narratives(count=args.count)


if __name__ == "__main__":
    asyncio.run(main())
