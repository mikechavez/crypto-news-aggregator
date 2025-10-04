#!/usr/bin/env python3
"""
Script to delete all signal scores and recalculate them.

This script:
1. Deletes all documents in the signal_scores collection
2. Runs the update_signal_scores function to recalculate scores
"""

import asyncio
import logging
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from crypto_news_aggregator.db.mongodb import initialize_mongodb, mongo_manager
from crypto_news_aggregator.worker import update_signal_scores

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def delete_all_signal_scores():
    """Delete all documents from the signal_scores collection."""
    logger.info("Connecting to database...")
    db = await mongo_manager.get_async_database()
    collection = db.signal_scores
    
    # Count existing documents
    count_before = await collection.count_documents({})
    logger.info(f"Found {count_before} documents in signal_scores collection")
    
    if count_before == 0:
        logger.info("Collection is already empty")
        return 0
    
    # Delete all documents
    logger.info("Deleting all documents from signal_scores collection...")
    result = await collection.delete_many({})
    deleted_count = result.deleted_count
    
    logger.info(f"Successfully deleted {deleted_count} documents")
    
    # Verify deletion
    count_after = await collection.count_documents({})
    logger.info(f"Documents remaining: {count_after}")
    
    return deleted_count


async def run_single_update():
    """Run a single iteration of the signal score update."""
    logger.info("Running signal score recalculation...")
    
    # Import the update logic from worker.py
    from datetime import datetime, timezone, timedelta
    from crypto_news_aggregator.services.signal_service import calculate_signal_score
    from crypto_news_aggregator.db.operations.signal_scores import upsert_signal_score
    
    db = await mongo_manager.get_async_database()
    entity_mentions_collection = db.entity_mentions
    
    # Get entities mentioned in the last 7 days
    since_time = datetime.now(timezone.utc) - timedelta(days=7)
    
    pipeline = [
        {"$match": {
            "timestamp": {"$gte": since_time},
            "is_primary": True  # Only score primary entities
        }},
        {"$group": {
            "_id": {
                "entity": "$entity",
                "entity_type": "$entity_type"
            }
        }},
        {"$limit": 500}  # Limit to prevent overload
    ]
    
    entities_to_score = []
    async for result in entity_mentions_collection.aggregate(pipeline):
        entity_info = result["_id"]
        entities_to_score.append(entity_info)
    
    if not entities_to_score:
        logger.info("No recent entities found to score (last 7 days)")
        return 0
    
    logger.info(f"Found {len(entities_to_score)} entities to score")
    
    # Calculate scores for each entity
    scored_count = 0
    for entity_info in entities_to_score:
        entity = entity_info["entity"]
        entity_type = entity_info["entity_type"]
        
        try:
            signal_data = await calculate_signal_score(entity)
            
            # Get first_seen timestamp (primary mentions only)
            first_mention = await entity_mentions_collection.find_one(
                {"entity": entity, "is_primary": True},
                sort=[("timestamp", 1)]
            )
            first_seen = first_mention["timestamp"] if first_mention else datetime.now(timezone.utc)
            
            # Store the signal score
            await upsert_signal_score(
                entity=entity,
                entity_type=entity_type,
                score=signal_data["score"],
                velocity=signal_data["velocity"],
                source_count=signal_data["source_count"],
                sentiment=signal_data["sentiment"],
                first_seen=first_seen,
            )
            
            scored_count += 1
            logger.info(f"Scored {entity}: {signal_data['score']:.2f}")
            
        except Exception as exc:
            logger.error(f"Failed to score entity {entity}: {exc}")
    
    logger.info(f"Successfully scored {scored_count} entities")
    return scored_count


async def main():
    """Main execution function."""
    try:
        # Initialize MongoDB connection
        logger.info("Initializing MongoDB connection...")
        await initialize_mongodb()
        
        # Step 1: Delete all signal scores
        deleted_count = await delete_all_signal_scores()
        
        # Step 2: Recalculate signal scores
        scored_count = await run_single_update()
        
        logger.info("=" * 60)
        logger.info("SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Deleted documents: {deleted_count}")
        logger.info(f"Recalculated scores: {scored_count}")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.exception(f"Error during recalculation: {e}")
        sys.exit(1)
    finally:
        # Close MongoDB connection
        await mongo_manager.aclose()
        logger.info("MongoDB connection closed")


if __name__ == "__main__":
    asyncio.run(main())
