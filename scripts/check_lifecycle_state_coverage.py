"""
Check lifecycle_state coverage across narratives.

This script provides a quick summary of:
1. Total narratives in database
2. Narratives with lifecycle_state
3. Narratives missing lifecycle_state
4. Distribution of lifecycle states
"""

import asyncio
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from crypto_news_aggregator.db.mongodb import mongo_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def check_lifecycle_state_coverage():
    """Check lifecycle_state coverage across narratives."""
    logger.info("=" * 80)
    logger.info("LIFECYCLE STATE COVERAGE CHECK")
    logger.info("=" * 80)
    
    await mongo_manager.initialize()
    
    try:
        db = await mongo_manager.get_async_database()
        narratives_collection = db.narratives
        
        # Count total narratives
        total_narratives = await narratives_collection.count_documents({})
        logger.info(f"📊 Total narratives: {total_narratives}")
        
        if total_narratives == 0:
            logger.info("ℹ️  No narratives found in database")
            return
        
        # Count narratives with lifecycle_state
        with_state = await narratives_collection.count_documents({
            'lifecycle_state': {'$exists': True, '$ne': None}
        })
        
        # Count narratives missing lifecycle_state
        missing_state = await narratives_collection.count_documents({
            '$or': [
                {'lifecycle_state': {'$exists': False}},
                {'lifecycle_state': None}
            ]
        })
        
        logger.info(f"✅ Narratives with lifecycle_state: {with_state}")
        logger.info(f"❌ Narratives missing lifecycle_state: {missing_state}")
        logger.info(f"📈 Coverage: {(with_state / total_narratives * 100):.1f}%")
        logger.info("")
        
        # Show lifecycle state distribution for narratives that have it
        if with_state > 0:
            logger.info("📊 Lifecycle State Distribution:")
            
            pipeline = [
                {'$match': {'lifecycle_state': {'$exists': True, '$ne': None}}},
                {'$group': {'_id': '$lifecycle_state', 'count': {'$sum': 1}}},
                {'$sort': {'count': -1}}
            ]
            
            state_distribution = await narratives_collection.aggregate(pipeline).to_list(length=None)
            
            for state_doc in state_distribution:
                state = state_doc['_id']
                count = state_doc['count']
                percentage = (count / with_state * 100)
                logger.info(f"  • {state}: {count} ({percentage:.1f}%)")
        
        logger.info("")
        
        # Show sample narratives missing lifecycle_state
        if missing_state > 0:
            logger.info(f"📋 Sample narratives missing lifecycle_state (showing up to 5):")
            
            cursor = narratives_collection.find(
                {
                    '$or': [
                        {'lifecycle_state': {'$exists': False}},
                        {'lifecycle_state': None}
                    ]
                },
                {
                    'title': 1,
                    'article_count': 1,
                    'mention_velocity': 1,
                    'last_updated': 1
                }
            ).limit(5)
            
            samples = await cursor.to_list(length=5)
            
            for narrative in samples:
                title = narrative.get('title', 'Unknown')
                article_count = narrative.get('article_count', 0)
                velocity = narrative.get('mention_velocity', 0.0)
                last_updated = narrative.get('last_updated', 'N/A')
                
                logger.info(
                    f"  • '{title}': "
                    f"{article_count} articles, "
                    f"velocity={velocity:.2f}, "
                    f"last_updated={last_updated}"
                )
        
        logger.info("=" * 80)
        
    except Exception as e:
        logger.exception(f"❌ Error checking coverage: {e}")
        raise
    finally:
        await mongo_manager.close()


async def main():
    """Main entry point."""
    try:
        await check_lifecycle_state_coverage()
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Check failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
