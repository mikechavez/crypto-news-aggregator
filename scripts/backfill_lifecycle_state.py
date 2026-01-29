"""
Backfill lifecycle_state field for narratives missing it.

This script:
1. Queries narratives where lifecycle_state doesn't exist
2. Calculates the appropriate state based on:
   - article_count
   - last_updated date
   - mention_velocity
   Using the same logic from narrative_service.py's determine_lifecycle_state()
3. Initializes lifecycle_history array with the calculated state and current timestamp
4. Updates each narrative document with lifecycle_state and lifecycle_history
5. Logs progress and provides final summary
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
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def backfill_lifecycle_state():
    """
    Backfill lifecycle_state and lifecycle_history for narratives that don't have them.
    
    Returns:
        Tuple of (total_processed, total_updated, total_errors)
    """
    logger.info("=" * 80)
    logger.info("LIFECYCLE STATE BACKFILL")
    logger.info("=" * 80)
    
    await mongo_manager.initialize()
    
    try:
        db = await mongo_manager.get_async_database()
        narratives_collection = db.narratives
        
        # Query narratives where lifecycle_state doesn't exist
        query = {
            '$or': [
                {'lifecycle_state': {'$exists': False}},
                {'lifecycle_state': None}
            ]
        }
        
        # Count total narratives missing lifecycle_state
        total_missing = await narratives_collection.count_documents(query)
        logger.info(f"📊 Narratives missing lifecycle_state: {total_missing}")
        
        if total_missing == 0:
            logger.info("✅ No narratives need backfilling - all have lifecycle_state")
            return 0, 0, 0
        
        # Fetch narratives
        cursor = narratives_collection.find(query)
        narratives = await cursor.to_list(length=None)
        
        total_processed = 0
        total_updated = 0
        total_errors = 0
        
        logger.info(f"🔍 Processing {len(narratives)} narratives...")
        logger.info("")
        
        for narrative in narratives:
            total_processed += 1
            narrative_id = narrative.get('_id')
            title = narrative.get('title', 'Unknown')
            
            try:
                # Extract required fields for lifecycle_state calculation
                article_count = narrative.get('article_count', 0)
                mention_velocity = narrative.get('mention_velocity', 0.0)
                first_seen = narrative.get('first_seen')
                last_updated = narrative.get('last_updated')
                
                # Ensure first_seen and last_updated are timezone-aware
                if first_seen and first_seen.tzinfo is None:
                    first_seen = first_seen.replace(tzinfo=timezone.utc)
                if last_updated and last_updated.tzinfo is None:
                    last_updated = last_updated.replace(tzinfo=timezone.utc)
                
                # Use current time if timestamps are missing
                now = datetime.now(timezone.utc)
                if not first_seen:
                    first_seen = now
                if not last_updated:
                    last_updated = now
                
                # Calculate lifecycle_state using the same logic from narrative_service.py
                # No previous_state since this is the first time we're setting it
                lifecycle_state = determine_lifecycle_state(
                    article_count=article_count,
                    mention_velocity=mention_velocity,
                    first_seen=first_seen,
                    last_updated=last_updated,
                    previous_state=None
                )
                
                # Initialize lifecycle_history with the calculated state
                # Use update_lifecycle_history to create the first entry
                lifecycle_history, resurrection_fields = update_lifecycle_history(
                    narrative={},  # Empty dict since this is first entry
                    lifecycle_state=lifecycle_state,
                    article_count=article_count,
                    mention_velocity=mention_velocity
                )
                
                # Prepare update data
                update_data = {
                    'lifecycle_state': lifecycle_state,
                    'lifecycle_history': lifecycle_history
                }
                
                # Update narrative with lifecycle_state and lifecycle_history
                await narratives_collection.update_one(
                    {'_id': narrative_id},
                    {'$set': update_data}
                )
                
                total_updated += 1
                
                # Log progress every 5 narratives
                if total_updated % 5 == 0:
                    logger.info(
                        f"✅ Progress: {total_updated} narratives updated "
                        f"({total_processed}/{len(narratives)} processed)"
                    )
                
                logger.debug(
                    f"✅ Updated narrative '{title}': "
                    f"state={lifecycle_state}, "
                    f"articles={article_count}, "
                    f"velocity={mention_velocity:.2f}"
                )
                
            except Exception as e:
                total_errors += 1
                logger.error(f"❌ Failed to process narrative '{title}' (ID: {narrative_id}): {e}")
                continue
        
        # Final summary
        logger.info("")
        logger.info("=" * 80)
        logger.info("BACKFILL COMPLETE")
        logger.info("=" * 80)
        logger.info(f"📊 Total narratives processed: {total_processed}")
        logger.info(f"✅ Narratives updated with lifecycle_state: {total_updated}")
        logger.info(f"❌ Errors encountered: {total_errors}")
        logger.info("=" * 80)
        
        # Show breakdown of lifecycle states
        if total_updated > 0:
            logger.info("")
            logger.info("📈 Lifecycle State Distribution:")
            
            # Query to get state distribution
            pipeline = [
                {'$match': {'lifecycle_state': {'$exists': True}}},
                {'$group': {'_id': '$lifecycle_state', 'count': {'$sum': 1}}},
                {'$sort': {'count': -1}}
            ]
            
            state_distribution = await narratives_collection.aggregate(pipeline).to_list(length=None)
            
            for state_doc in state_distribution:
                state = state_doc['_id']
                count = state_doc['count']
                logger.info(f"  • {state}: {count} narratives")
            
            logger.info("=" * 80)
        
        return total_processed, total_updated, total_errors
        
    except Exception as e:
        logger.exception(f"❌ Error during backfill: {e}")
        raise
    finally:
        await mongo_manager.close()


async def main():
    """Main entry point."""
    try:
        total_processed, total_updated, total_errors = await backfill_lifecycle_state()
        
        # Exit with appropriate code
        if total_errors > 0:
            logger.warning(f"⚠️  Backfill completed with {total_errors} errors")
            sys.exit(1)
        elif total_updated > 0:
            logger.info("✅ Backfill successful!")
            sys.exit(0)
        else:
            logger.info("ℹ️  No narratives needed backfilling")
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"❌ Backfill failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
