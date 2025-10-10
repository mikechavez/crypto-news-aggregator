"""
Recalculate signal scores with velocity as percentage.

This script recalculates all signal scores to ensure velocity values
are stored as percentages (e.g., 67.0 for 67% growth) instead of decimals (0.67).

This is needed after fixing the velocity calculation to return percentages
to match frontend expectations for velocity indicators.
"""

import asyncio
import logging
from datetime import datetime, timezone
from crypto_news_aggregator.db.mongodb import mongo_manager
from crypto_news_aggregator.services.signal_service import calculate_signal_score
from crypto_news_aggregator.db.operations.signal_scores import upsert_signal_score

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def recalculate_all_signals():
    """Recalculate all signal scores with new velocity percentage format."""
    db = await mongo_manager.get_async_database()
    collection = db.signal_scores
    
    # Get all existing signals
    cursor = collection.find({})
    signals = await cursor.to_list(length=None)
    
    logger.info(f"Found {len(signals)} signals to recalculate")
    
    recalculated = 0
    errors = 0
    
    for signal in signals:
        entity = signal["entity"]
        entity_type = signal["entity_type"]
        
        try:
            # Recalculate for all three timeframes
            score_24h_data = await calculate_signal_score(entity, timeframe_hours=24)
            score_7d_data = await calculate_signal_score(entity, timeframe_hours=168)
            score_30d_data = await calculate_signal_score(entity, timeframe_hours=720)
            
            # Update signal with new velocity percentages
            await upsert_signal_score(
                entity=entity,
                entity_type=entity_type,
                score=score_7d_data["score"],  # Legacy field uses 7d
                velocity=score_7d_data["velocity"],  # Legacy field uses 7d
                source_count=score_7d_data["source_count"],
                sentiment=score_7d_data["sentiment"],
                narrative_ids=score_7d_data["narrative_ids"],
                is_emerging=score_7d_data["is_emerging"],
                first_seen=signal.get("first_seen"),
                # Multi-timeframe fields
                score_24h=score_24h_data["score"],
                score_7d=score_7d_data["score"],
                score_30d=score_30d_data["score"],
                velocity_24h=score_24h_data["velocity"],
                velocity_7d=score_7d_data["velocity"],
                velocity_30d=score_30d_data["velocity"],
                mentions_24h=score_24h_data["mentions"],
                mentions_7d=score_7d_data["mentions"],
                mentions_30d=score_30d_data["mentions"],
                recency_24h=score_24h_data["recency_factor"],
                recency_7d=score_7d_data["recency_factor"],
                recency_30d=score_30d_data["recency_factor"],
            )
            
            recalculated += 1
            
            if recalculated % 10 == 0:
                logger.info(f"Recalculated {recalculated}/{len(signals)} signals...")
                logger.info(f"  Latest: {entity} - 24h velocity: {score_24h_data['velocity']:.2f}%, 7d: {score_7d_data['velocity']:.2f}%, 30d: {score_30d_data['velocity']:.2f}%")
            
        except Exception as e:
            logger.error(f"Error recalculating signal for {entity}: {e}")
            errors += 1
            continue
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Recalculation complete!")
    logger.info(f"  Successfully recalculated: {recalculated}")
    logger.info(f"  Errors: {errors}")
    logger.info(f"{'='*60}")
    
    # Show sample of updated velocities
    logger.info("\nSample of updated velocity values:")
    cursor = collection.find({}).sort("score_7d", -1).limit(5)
    async for signal in cursor:
        logger.info(f"  {signal['entity']}:")
        logger.info(f"    24h velocity: {signal.get('velocity_24h', 0):.2f}%")
        logger.info(f"    7d velocity: {signal.get('velocity_7d', 0):.2f}%")
        logger.info(f"    30d velocity: {signal.get('velocity_30d', 0):.2f}%")


if __name__ == "__main__":
    asyncio.run(recalculate_all_signals())
