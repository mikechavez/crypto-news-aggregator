#!/usr/bin/env python3
"""
Migration script to backfill the 'source' field in existing entity_mentions.

This script:
1. Finds all entity mentions without a source field
2. Looks up the article_id to get the source from the articles collection
3. Updates the entity mention with the source field

Usage:
    poetry run python scripts/backfill_entity_mention_sources.py [--dry-run]
"""

import asyncio
import argparse
import logging
from datetime import datetime, timezone
from bson import ObjectId
from crypto_news_aggregator.db.mongodb import mongo_manager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def backfill_entity_mention_sources(dry_run: bool = False):
    """
    Backfill source field for entity mentions by looking up article sources.
    
    Args:
        dry_run: If True, only report what would be updated without making changes
    """
    db = await mongo_manager.get_async_database()
    entity_mentions_collection = db.entity_mentions
    articles_collection = db.articles
    
    # Find all entity mentions without a source field or with source = "unknown"
    query = {
        "$or": [
            {"source": {"$exists": False}},
            {"source": None},
            {"source": "unknown"}
        ]
    }
    
    total_mentions = await entity_mentions_collection.count_documents(query)
    logger.info(f"Found {total_mentions} entity mentions without source field")
    
    if total_mentions == 0:
        logger.info("No entity mentions need source backfill")
        return 0
    
    updated_count = 0
    not_found_count = 0
    article_cache = {}  # Cache article sources to reduce DB queries
    
    # Process in batches
    batch_size = 100
    cursor = entity_mentions_collection.find(query)
    
    async for mention in cursor:
        mention_id = mention["_id"]
        article_id = mention.get("article_id")
        
        if not article_id:
            logger.warning(f"Entity mention {mention_id} has no article_id, skipping")
            continue
        
        # Check cache first
        if article_id in article_cache:
            source = article_cache[article_id]
        else:
            # Convert article_id string to ObjectId for MongoDB query
            try:
                article_object_id = ObjectId(article_id)
            except Exception as e:
                logger.warning(f"Invalid article_id format {article_id} for mention {mention_id}: {e}")
                source = "unknown"
                not_found_count += 1
                article_cache[article_id] = source
                continue
            
            # Look up the article to get its source
            article = await articles_collection.find_one(
                {"_id": article_object_id},
                {"source": 1, "source_id": 1}
            )
            
            if article:
                # Try to get source from article
                source = article.get("source") or article.get("source_id") or "unknown"
                article_cache[article_id] = source
            else:
                logger.warning(f"Article {article_id} not found for mention {mention_id}")
                source = "unknown"
                not_found_count += 1
                article_cache[article_id] = source
        
        # Update the entity mention with the source
        if not dry_run:
            await entity_mentions_collection.update_one(
                {"_id": mention_id},
                {
                    "$set": {
                        "source": source,
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
        
        updated_count += 1
        
        if updated_count % 100 == 0:
            logger.info(f"Processed {updated_count}/{total_mentions} entity mentions...")
    
    if dry_run:
        logger.info(f"[DRY RUN] Would update {updated_count} entity mentions")
        logger.info(f"[DRY RUN] {not_found_count} mentions have articles not found")
    else:
        logger.info(f"✅ Successfully updated {updated_count} entity mentions with source field")
        logger.info(f"⚠️  {not_found_count} mentions had articles not found (set to 'unknown')")
    
    # Show source distribution
    logger.info("\nSource distribution after backfill:")
    pipeline = [
        {"$group": {"_id": "$source", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    
    async for result in entity_mentions_collection.aggregate(pipeline):
        source = result["_id"] or "null"
        count = result["count"]
        logger.info(f"  {source}: {count} mentions")
    
    return updated_count


async def main():
    """Main entry point for the migration script."""
    parser = argparse.ArgumentParser(
        description="Backfill source field in entity_mentions collection"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run in dry-run mode (no actual updates)"
    )
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("Entity Mention Source Backfill Migration")
    logger.info("=" * 60)
    
    if args.dry_run:
        logger.info("Running in DRY RUN mode - no changes will be made")
    
    try:
        updated_count = await backfill_entity_mention_sources(dry_run=args.dry_run)
        
        logger.info("=" * 60)
        logger.info("Migration completed successfully")
        logger.info(f"Total entity mentions processed: {updated_count}")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        raise
    finally:
        await mongo_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
