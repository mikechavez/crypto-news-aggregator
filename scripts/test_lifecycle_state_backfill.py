"""
Test lifecycle_state backfill logic without modifying database.

This script tests the backfill logic by:
1. Fetching a sample of narratives missing lifecycle_state
2. Calculating what their lifecycle_state would be
3. Displaying the results without updating the database
"""

import asyncio
import sys
import logging
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))

from crypto_news_aggregator.db.mongodb import mongo_manager
from crypto_news_aggregator.services.narrative_service import (
    determine_lifecycle_state,
    update_lifecycle_history
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_lifecycle_state_calculation():
    """Test lifecycle_state calculation on sample narratives."""
    logger.info("=" * 80)
    logger.info("LIFECYCLE STATE BACKFILL TEST (DRY RUN)")
    logger.info("=" * 80)
    
    await mongo_manager.initialize()
    
    try:
        db = await mongo_manager.get_async_database()
        narratives_collection = db.narratives
        
        # Query narratives missing lifecycle_state (limit to 10 for testing)
        query = {
            '$or': [
                {'lifecycle_state': {'$exists': False}},
                {'lifecycle_state': None}
            ]
        }
        
        cursor = narratives_collection.find(query).limit(10)
        narratives = await cursor.to_list(length=10)
        
        if not narratives:
            logger.info("✅ No narratives missing lifecycle_state - nothing to test")
            return
        
        logger.info(f"🔍 Testing lifecycle_state calculation on {len(narratives)} sample narratives")
        logger.info("")
        
        state_counts = {}
        
        for i, narrative in enumerate(narratives, 1):
            title = narrative.get('title', 'Unknown')
            article_count = narrative.get('article_count', 0)
            mention_velocity = narrative.get('mention_velocity', 0.0)
            first_seen = narrative.get('first_seen')
            last_updated = narrative.get('last_updated')
            
            # Ensure timezone-aware
            if first_seen and first_seen.tzinfo is None:
                first_seen = first_seen.replace(tzinfo=timezone.utc)
            if last_updated and last_updated.tzinfo is None:
                last_updated = last_updated.replace(tzinfo=timezone.utc)
            
            # Use current time if missing
            now = datetime.now(timezone.utc)
            if not first_seen:
                first_seen = now
            if not last_updated:
                last_updated = now
            
            # Calculate days since last update
            days_since_update = (now - last_updated).total_seconds() / 86400
            
            # Calculate lifecycle_state
            lifecycle_state = determine_lifecycle_state(
                article_count=article_count,
                mention_velocity=mention_velocity,
                first_seen=first_seen,
                last_updated=last_updated,
                previous_state=None
            )
            
            # Track state counts
            state_counts[lifecycle_state] = state_counts.get(lifecycle_state, 0) + 1
            
            # Test lifecycle_history creation
            lifecycle_history, resurrection_fields = update_lifecycle_history(
                narrative={},
                lifecycle_state=lifecycle_state,
                article_count=article_count,
                mention_velocity=mention_velocity
            )
            
            logger.info(f"Sample {i}:")
            logger.info(f"  Title: '{title}'")
            logger.info(f"  Articles: {article_count}")
            logger.info(f"  Velocity: {mention_velocity:.2f} articles/day")
            logger.info(f"  Days since update: {days_since_update:.1f}")
            logger.info(f"  → Calculated state: {lifecycle_state}")
            logger.info(f"  → History entries: {len(lifecycle_history)}")
            if lifecycle_history:
                entry = lifecycle_history[0]
                logger.info(f"     - state: {entry['state']}")
                logger.info(f"     - article_count: {entry['article_count']}")
                logger.info(f"     - mention_velocity: {entry['mention_velocity']}")
            logger.info("")
        
        # Summary
        logger.info("=" * 80)
        logger.info("TEST SUMMARY")
        logger.info("=" * 80)
        logger.info(f"📊 Tested {len(narratives)} narratives")
        logger.info("")
        logger.info("📈 Calculated State Distribution:")
        for state, count in sorted(state_counts.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  • {state}: {count} narratives")
        logger.info("")
        logger.info("✅ Test completed successfully - no database changes made")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.exception(f"❌ Error during test: {e}")
        raise
    finally:
        await mongo_manager.close()


async def main():
    """Main entry point."""
    try:
        await test_lifecycle_state_calculation()
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
