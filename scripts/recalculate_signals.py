#!/usr/bin/env python3
"""
Script to recalculate signals for all entities after normalization.

This ensures signal scores are accurate after entity names have been normalized.

Usage:
    python scripts/recalculate_signals.py
"""

import asyncio
import logging
from datetime import datetime, timezone

from crypto_news_aggregator.db.mongodb import mongo_manager
from crypto_news_aggregator.services.signal_service import calculate_signal_score

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def recalculate_all_signals():
    """Recalculate signals for all unique entities."""
    db = await mongo_manager.get_async_database()
    entity_mentions_collection = db.entity_mentions
    entity_signals_collection = db.entity_signals
    
    # Get all unique entities (primary mentions only)
    unique_entities = await entity_mentions_collection.distinct(
        "entity",
        {"is_primary": True}
    )
    
    logger.info(f"Found {len(unique_entities)} unique entities to process")
    
    processed = 0
    errors = 0
    
    for entity in unique_entities:
        try:
            # Calculate signal score
            signal_data = await calculate_signal_score(entity)
            
            # Save to entity_signals collection
            await entity_signals_collection.update_one(
                {"entity": entity},
                {
                    "$set": {
                        "entity": entity,
                        "score": signal_data["score"],
                        "velocity": signal_data["velocity"],
                        "source_count": signal_data["source_count"],
                        "sentiment": signal_data["sentiment"],
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
                upsert=True
            )
            
            processed += 1
            
            if processed % 10 == 0:
                logger.info(f"Processed {processed}/{len(unique_entities)} entities")
        
        except Exception as e:
            logger.error(f"Failed to calculate signal for entity '{entity}': {e}")
            errors += 1
    
    logger.info(f"\nSignal recalculation complete:")
    logger.info(f"  Processed: {processed}")
    logger.info(f"  Errors: {errors}")
    logger.info(f"  Total: {len(unique_entities)}")


async def main():
    """Main function."""
    try:
        logger.info("=" * 60)
        logger.info("Recalculating signals for all entities")
        logger.info("=" * 60)
        
        await recalculate_all_signals()
        
        logger.info("\n" + "=" * 60)
        logger.info("RECALCULATION COMPLETE")
        logger.info("=" * 60)
    
    except Exception as e:
        logger.exception(f"Signal recalculation failed: {e}")
        raise
    finally:
        await mongo_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
