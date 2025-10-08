#!/usr/bin/env python3
"""
Backfill signal scores for all entities in the database.

This script:
1. Finds all unique entities in entity_mentions collection
2. Calculates 24h, 7d, and 30d scores for each entity
3. Stores results in signal_scores collection
4. Takes approximately 2-3 minutes to complete
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from crypto_news_aggregator.db.mongodb import initialize_mongodb, mongo_manager
from crypto_news_aggregator.services.signal_service import calculate_signal_score
from crypto_news_aggregator.db.operations.signal_scores import upsert_signal_score

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def get_all_entities():
    """Get all unique entities from entity_mentions collection."""
    db = await mongo_manager.get_async_database()
    entity_mentions_collection = db.entity_mentions
    
    # Get all unique entities (primary mentions only)
    pipeline = [
        {"$match": {"is_primary": True}},
        {"$group": {
            "_id": {
                "entity": "$entity",
                "entity_type": "$entity_type"
            }
        }}
    ]
    
    entities = []
    async for result in entity_mentions_collection.aggregate(pipeline):
        entity_info = result["_id"]
        entities.append(entity_info)
    
    return entities


async def calculate_and_store_scores(entity: str, entity_type: str):
    """
    Calculate signal scores for all timeframes and store them.
    
    Args:
        entity: The entity name
        entity_type: The entity type
    
    Returns:
        Dict with success status and calculated scores
    """
    try:
        # Calculate scores for each timeframe
        score_24h_data = await calculate_signal_score(entity, timeframe_hours=24)
        score_7d_data = await calculate_signal_score(entity, timeframe_hours=168)  # 7 days
        score_30d_data = await calculate_signal_score(entity, timeframe_hours=720)  # 30 days
        
        # Get first_seen timestamp
        db = await mongo_manager.get_async_database()
        entity_mentions_collection = db.entity_mentions
        first_mention = await entity_mentions_collection.find_one(
            {"entity": entity, "is_primary": True},
            sort=[("created_at", 1)]
        )
        first_seen = first_mention["created_at"] if first_mention else datetime.now(timezone.utc)
        
        # Get narrative_ids from 7d data (most representative)
        narrative_ids = score_7d_data.get("narrative_ids", [])
        is_emerging = score_7d_data.get("is_emerging", False)
        
        # Store consolidated signal score with all timeframes
        await upsert_signal_score(
            entity=entity,
            entity_type=entity_type,
            # Legacy fields (use 7d as default)
            score=score_7d_data["score"],
            velocity=score_7d_data["velocity"],
            source_count=score_7d_data["source_count"],
            sentiment=score_7d_data["sentiment"],
            narrative_ids=narrative_ids,
            is_emerging=is_emerging,
            first_seen=first_seen,
            # 24h timeframe
            score_24h=score_24h_data["score"],
            velocity_24h=score_24h_data["velocity"],
            mentions_24h=score_24h_data["mentions"],
            recency_24h=score_24h_data["recency_factor"],
            # 7d timeframe
            score_7d=score_7d_data["score"],
            velocity_7d=score_7d_data["velocity"],
            mentions_7d=score_7d_data["mentions"],
            recency_7d=score_7d_data["recency_factor"],
            # 30d timeframe
            score_30d=score_30d_data["score"],
            velocity_30d=score_30d_data["velocity"],
            mentions_30d=score_30d_data["mentions"],
            recency_30d=score_30d_data["recency_factor"],
        )
        
        return {
            "success": True,
            "entity": entity,
            "scores": {
                "24h": score_24h_data["score"],
                "7d": score_7d_data["score"],
                "30d": score_30d_data["score"],
            }
        }
        
    except Exception as exc:
        logger.error(f"Failed to calculate scores for {entity}: {exc}")
        return {
            "success": False,
            "entity": entity,
            "error": str(exc)
        }


async def main():
    """Main execution function."""
    try:
        # Initialize MongoDB connection
        logger.info("Initializing MongoDB connection...")
        await initialize_mongodb()
        
        # Get all entities
        logger.info("Fetching all entities from entity_mentions...")
        entities = await get_all_entities()
        logger.info(f"Found {len(entities)} unique entities to process")
        
        if not entities:
            logger.warning("No entities found in database")
            return
        
        # Process each entity
        logger.info("Calculating signal scores for all entities...")
        logger.info("This will take approximately 2-3 minutes...")
        
        success_count = 0
        failure_count = 0
        
        for i, entity_info in enumerate(entities, 1):
            entity = entity_info["entity"]
            entity_type = entity_info["entity_type"]
            
            logger.info(f"[{i}/{len(entities)}] Processing: {entity} ({entity_type})")
            
            result = await calculate_and_store_scores(entity, entity_type)
            
            if result["success"]:
                success_count += 1
                scores = result["scores"]
                logger.info(
                    f"  ✓ Scores: 24h={scores['24h']:.2f}, "
                    f"7d={scores['7d']:.2f}, 30d={scores['30d']:.2f}"
                )
            else:
                failure_count += 1
                logger.error(f"  ✗ Failed: {result.get('error', 'Unknown error')}")
        
        # Summary
        logger.info("=" * 60)
        logger.info("BACKFILL COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Total entities processed: {len(entities)}")
        logger.info(f"Successfully scored: {success_count}")
        logger.info(f"Failed: {failure_count}")
        logger.info("=" * 60)
        
        if success_count > 0:
            logger.info("✓ Signal scores have been populated!")
            logger.info("  You should now see 20-30 signals per tab in the UI")
        
    except Exception as e:
        logger.exception(f"Error during backfill: {e}")
        sys.exit(1)
    finally:
        # Close MongoDB connection
        await mongo_manager.aclose()
        logger.info("MongoDB connection closed")


if __name__ == "__main__":
    asyncio.run(main())
