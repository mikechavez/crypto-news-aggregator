#!/usr/bin/env python3
"""
Add performance indexes to MongoDB collections.

This script creates optimized indexes for frequently queried collections:
- articles: published_at desc, entities
- entity_mentions: entity + created_at desc, compound index with source
- signal_scores: timeframe + score desc
- narratives: lifecycle_state + last_updated desc

These indexes improve query performance for common access patterns
in the crypto news aggregator application.

Usage:
    poetry run python scripts/add_performance_indexes.py
"""

import asyncio
import sys
import os
import logging
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import OperationFailure

# Add src to path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, os.path.join(project_root, "src"))

from crypto_news_aggregator.db.mongodb import mongo_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _check_index_exists_by_keys(existing_indexes, keys):
    """
    Check if an index with the same keys already exists (regardless of name).
    
    Args:
        existing_indexes: Dictionary of existing indexes from index_information()
        keys: List of (field, direction) tuples to check
    
    Returns:
        Tuple of (exists: bool, index_name: str or None)
    """
    for idx_name, idx_info in existing_indexes.items():
        idx_keys = idx_info.get('key', [])
        # Convert to list of tuples for comparison
        idx_keys_list = [(k, v) for k, v in idx_keys]
        if idx_keys_list == keys:
            return True, idx_name
    return False, None


async def create_articles_indexes(db):
    """
    Create performance indexes for the articles collection.
    
    Indexes:
    - published_at (descending): For time-based queries and sorting
    - entities (ascending): For entity-based article lookups
    """
    collection = db.articles
    logger.info("=" * 70)
    logger.info("Creating indexes for 'articles' collection")
    logger.info("=" * 70)
    
    indexes_to_create = [
        {
            "name": "idx_published_at_desc_perf",
            "keys": [("published_at", DESCENDING)],
            "description": "Optimizes time-based queries and sorting by publication date"
        },
        {
            "name": "idx_entities_asc",
            "keys": [("entities", ASCENDING)],
            "description": "Optimizes entity-based article lookups"
        }
    ]
    
    existing_indexes = await collection.index_information()
    
    for index_info in indexes_to_create:
        index_name = index_info["name"]
        keys = index_info["keys"]
        
        # Check if index with same name exists
        if index_name in existing_indexes:
            logger.info(f"✓ Index '{index_name}' already exists")
            logger.info(f"  Details: {existing_indexes[index_name]}")
        else:
            # Check if functionally equivalent index exists with different name
            exists, existing_name = _check_index_exists_by_keys(existing_indexes, keys)
            if exists:
                logger.info(f"✓ Equivalent index already exists as '{existing_name}'")
                logger.info(f"  Keys: {keys}")
                logger.info(f"  Skipping creation of '{index_name}'")
            else:
                logger.info(f"Creating index '{index_name}'...")
                logger.info(f"  Description: {index_info['description']}")
                logger.info(f"  Keys: {keys}")
                
                try:
                    result = await collection.create_index(
                        keys,
                        name=index_name,
                        background=True
                    )
                    logger.info(f"✓ Index created successfully: {result}")
                except OperationFailure as e:
                    logger.error(f"✗ Failed to create index '{index_name}': {e}")
                    raise
    
    logger.info("")


async def create_entity_mentions_indexes(db):
    """
    Create performance indexes for the entity_mentions collection.
    
    Indexes:
    - entity + created_at (descending): For entity timeline queries
    - entity + source (compound): For source diversity calculations
    """
    collection = db.entity_mentions
    logger.info("=" * 70)
    logger.info("Creating indexes for 'entity_mentions' collection")
    logger.info("=" * 70)
    
    indexes_to_create = [
        {
            "name": "idx_entity_created_at_desc_perf",
            "keys": [("entity", ASCENDING), ("created_at", DESCENDING)],
            "description": "Optimizes entity timeline queries and velocity calculations"
        },
        {
            "name": "idx_entity_source_compound",
            "keys": [("entity", ASCENDING), ("source", ASCENDING)],
            "description": "Optimizes source diversity calculations for entities"
        }
    ]
    
    existing_indexes = await collection.index_information()
    
    for index_info in indexes_to_create:
        index_name = index_info["name"]
        keys = index_info["keys"]
        
        # Check if index with same name exists
        if index_name in existing_indexes:
            logger.info(f"✓ Index '{index_name}' already exists")
            logger.info(f"  Details: {existing_indexes[index_name]}")
        else:
            # Check if functionally equivalent index exists with different name
            exists, existing_name = _check_index_exists_by_keys(existing_indexes, keys)
            if exists:
                logger.info(f"✓ Equivalent index already exists as '{existing_name}'")
                logger.info(f"  Keys: {keys}")
                logger.info(f"  Skipping creation of '{index_name}'")
            else:
                logger.info(f"Creating index '{index_name}'...")
                logger.info(f"  Description: {index_info['description']}")
                logger.info(f"  Keys: {keys}")
                
                try:
                    result = await collection.create_index(
                        keys,
                        name=index_name,
                        background=True
                    )
                    logger.info(f"✓ Index created successfully: {result}")
                except OperationFailure as e:
                    logger.error(f"✗ Failed to create index '{index_name}': {e}")
                    raise
    
    logger.info("")


async def create_signal_scores_indexes(db):
    """
    Create performance indexes for the signal_scores collection.
    
    Indexes:
    - score_24h (descending): For 24h timeframe queries
    - score_7d (descending): For 7d timeframe queries
    - score_30d (descending): For 30d timeframe queries
    """
    collection = db.signal_scores
    logger.info("=" * 70)
    logger.info("Creating indexes for 'signal_scores' collection")
    logger.info("=" * 70)
    
    indexes_to_create = [
        {
            "name": "idx_score_24h_desc",
            "keys": [("score_24h", DESCENDING)],
            "description": "Optimizes 24h timeframe signal queries and sorting"
        },
        {
            "name": "idx_score_7d_desc",
            "keys": [("score_7d", DESCENDING)],
            "description": "Optimizes 7d timeframe signal queries and sorting"
        },
        {
            "name": "idx_score_30d_desc",
            "keys": [("score_30d", DESCENDING)],
            "description": "Optimizes 30d timeframe signal queries and sorting"
        }
    ]
    
    existing_indexes = await collection.index_information()
    
    for index_info in indexes_to_create:
        index_name = index_info["name"]
        keys = index_info["keys"]
        
        # Check if index with same name exists
        if index_name in existing_indexes:
            logger.info(f"✓ Index '{index_name}' already exists")
            logger.info(f"  Details: {existing_indexes[index_name]}")
        else:
            # Check if functionally equivalent index exists with different name
            exists, existing_name = _check_index_exists_by_keys(existing_indexes, keys)
            if exists:
                logger.info(f"✓ Equivalent index already exists as '{existing_name}'")
                logger.info(f"  Keys: {keys}")
                logger.info(f"  Skipping creation of '{index_name}'")
            else:
                logger.info(f"Creating index '{index_name}'...")
                logger.info(f"  Description: {index_info['description']}")
                logger.info(f"  Keys: {keys}")
                
                try:
                    result = await collection.create_index(
                        keys,
                        name=index_name,
                        background=True
                    )
                    logger.info(f"✓ Index created successfully: {result}")
                except OperationFailure as e:
                    logger.error(f"✗ Failed to create index '{index_name}': {e}")
                    raise
    
    logger.info("")


async def create_narratives_indexes(db):
    """
    Create performance indexes for the narratives collection.
    
    Indexes:
    - lifecycle_state + last_updated (descending): For lifecycle-based queries
    """
    collection = db.narratives
    logger.info("=" * 70)
    logger.info("Creating indexes for 'narratives' collection")
    logger.info("=" * 70)
    
    indexes_to_create = [
        {
            "name": "idx_lifecycle_state_last_updated_desc",
            "keys": [("lifecycle_state", ASCENDING), ("last_updated", DESCENDING)],
            "description": "Optimizes lifecycle-based narrative queries and sorting"
        }
    ]
    
    existing_indexes = await collection.index_information()
    
    for index_info in indexes_to_create:
        index_name = index_info["name"]
        keys = index_info["keys"]
        
        # Check if index with same name exists
        if index_name in existing_indexes:
            logger.info(f"✓ Index '{index_name}' already exists")
            logger.info(f"  Details: {existing_indexes[index_name]}")
        else:
            # Check if functionally equivalent index exists with different name
            exists, existing_name = _check_index_exists_by_keys(existing_indexes, keys)
            if exists:
                logger.info(f"✓ Equivalent index already exists as '{existing_name}'")
                logger.info(f"  Keys: {keys}")
                logger.info(f"  Skipping creation of '{index_name}'")
            else:
                logger.info(f"Creating index '{index_name}'...")
                logger.info(f"  Description: {index_info['description']}")
                logger.info(f"  Keys: {keys}")
                
                try:
                    result = await collection.create_index(
                        keys,
                        name=index_name,
                        background=True
                    )
                    logger.info(f"✓ Index created successfully: {result}")
                except OperationFailure as e:
                    logger.error(f"✗ Failed to create index '{index_name}': {e}")
                    raise
    
    logger.info("")


async def create_performance_indexes():
    """
    Main function to create all performance indexes.
    """
    logger.info("=" * 70)
    logger.info("MongoDB Performance Indexes Creation")
    logger.info("=" * 70)
    logger.info("")
    
    try:
        # Initialize MongoDB connection
        logger.info("Initializing MongoDB connection...")
        await mongo_manager.initialize()
        db = await mongo_manager.get_async_database()
        logger.info("✓ MongoDB connection established")
        logger.info("")
        
        # Create indexes for each collection
        await create_articles_indexes(db)
        await create_entity_mentions_indexes(db)
        await create_signal_scores_indexes(db)
        await create_narratives_indexes(db)
        
        logger.info("=" * 70)
        logger.info("All performance indexes created successfully!")
        logger.info("=" * 70)
        logger.info("")
        logger.info("Summary:")
        logger.info("  • articles: 2 indexes (published_at, entities)")
        logger.info("  • entity_mentions: 2 indexes (entity+created_at, entity+source)")
        logger.info("  • signal_scores: 3 indexes (score_24h, score_7d, score_30d)")
        logger.info("  • narratives: 1 index (lifecycle_state+last_updated)")
        logger.info("")
        logger.info("These indexes will improve query performance for:")
        logger.info("  ✓ Time-based article queries")
        logger.info("  ✓ Entity mention lookups and velocity calculations")
        logger.info("  ✓ Signal score sorting across timeframes")
        logger.info("  ✓ Narrative lifecycle filtering and sorting")
        logger.info("")
        
    except OperationFailure as e:
        logger.error("=" * 70)
        logger.error("Database operation failed!")
        logger.error("=" * 70)
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        logger.error("=" * 70)
        logger.error("Unexpected error occurred!")
        logger.error("=" * 70)
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Close MongoDB connection
        await mongo_manager.close()


async def main():
    """Main entry point."""
    await create_performance_indexes()


if __name__ == "__main__":
    asyncio.run(main())
