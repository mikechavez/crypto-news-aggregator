#!/usr/bin/env python3
"""
Migration script to normalize entity names in existing data.

This script:
1. Updates all entity_mentions with canonical names
2. Merges duplicate entity mentions for the same article
3. Updates article entities with canonical names
4. Provides dry-run mode to preview changes

Usage:
    # Dry run (preview changes)
    python scripts/migrate_entity_normalization.py --dry-run
    
    # Apply changes
    python scripts/migrate_entity_normalization.py
"""

import asyncio
import argparse
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Any

from crypto_news_aggregator.db.mongodb import mongo_manager
from crypto_news_aggregator.services.entity_normalization import normalize_entity_name

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def migrate_entity_mentions(dry_run: bool = True) -> Dict[str, int]:
    """
    Migrate entity_mentions collection to use canonical names.
    
    Args:
        dry_run: If True, only preview changes without applying them
    
    Returns:
        Dict with migration statistics
    """
    db = await mongo_manager.get_async_database()
    collection = db.entity_mentions
    
    stats = {
        "total_mentions": 0,
        "normalized_mentions": 0,
        "merged_duplicates": 0,
        "unchanged_mentions": 0,
    }
    
    # Get all entity mentions grouped by article
    cursor = collection.find({})
    mentions_by_article = defaultdict(list)
    
    async for mention in cursor:
        stats["total_mentions"] += 1
        article_id = mention.get("article_id")
        mentions_by_article[article_id].append(mention)
    
    logger.info(f"Found {stats['total_mentions']} entity mentions across {len(mentions_by_article)} articles")
    
    # Process each article's mentions
    for article_id, mentions in mentions_by_article.items():
        # Normalize entity names and group duplicates
        normalized_mentions = {}
        
        for mention in mentions:
            mention_id = mention.get("_id")
            entity_name = mention.get("entity")
            
            if not entity_name:
                continue
            
            # Normalize the entity name
            canonical_name = normalize_entity_name(entity_name)
            
            # Track if normalization changed the name
            if canonical_name != entity_name:
                stats["normalized_mentions"] += 1
                logger.debug(f"Normalizing '{entity_name}' -> '{canonical_name}' in mention {mention_id}")
            else:
                stats["unchanged_mentions"] += 1
            
            # Create key for deduplication: (canonical_name, entity_type, is_primary)
            key = (
                canonical_name,
                mention.get("entity_type"),
                mention.get("is_primary", True)
            )
            
            # Keep the mention with highest confidence
            if key not in normalized_mentions:
                normalized_mentions[key] = {
                    "mention_id": mention_id,
                    "entity": canonical_name,
                    "entity_type": mention.get("entity_type"),
                    "article_id": article_id,
                    "sentiment": mention.get("sentiment"),
                    "confidence": mention.get("confidence", 1.0),
                    "source": mention.get("source"),
                    "is_primary": mention.get("is_primary", True),
                    "metadata": mention.get("metadata", {}),
                    "created_at": mention.get("created_at"),
                    "original_ids": [mention_id],
                }
            else:
                # Merge duplicate - keep higher confidence
                existing = normalized_mentions[key]
                if mention.get("confidence", 1.0) > existing["confidence"]:
                    existing["confidence"] = mention.get("confidence", 1.0)
                existing["original_ids"].append(mention_id)
                stats["merged_duplicates"] += 1
                logger.debug(f"Merging duplicate mention {mention_id} into {existing['mention_id']}")
        
        # Apply changes if not dry run
        if not dry_run:
            for key, normalized_mention in normalized_mentions.items():
                mention_id = normalized_mention["mention_id"]
                original_ids = normalized_mention["original_ids"]
                
                # Update the primary mention
                await collection.update_one(
                    {"_id": mention_id},
                    {
                        "$set": {
                            "entity": normalized_mention["entity"],
                            "confidence": normalized_mention["confidence"],
                            "updated_at": datetime.now(timezone.utc),
                        }
                    }
                )
                
                # Delete duplicate mentions
                if len(original_ids) > 1:
                    duplicate_ids = [oid for oid in original_ids if oid != mention_id]
                    await collection.delete_many({"_id": {"$in": duplicate_ids}})
    
    return stats


async def migrate_article_entities(dry_run: bool = True) -> Dict[str, int]:
    """
    Migrate entities field in articles collection to use canonical names.
    
    Args:
        dry_run: If True, only preview changes without applying them
    
    Returns:
        Dict with migration statistics
    """
    db = await mongo_manager.get_async_database()
    collection = db.articles
    
    stats = {
        "total_articles": 0,
        "articles_updated": 0,
        "entities_normalized": 0,
    }
    
    # Get all articles with entities
    cursor = collection.find({"entities": {"$exists": True, "$ne": []}})
    
    async for article in cursor:
        stats["total_articles"] += 1
        article_id = article.get("_id")
        entities = article.get("entities", [])
        
        if not entities:
            continue
        
        # Normalize entity names
        updated_entities = []
        article_changed = False
        
        for entity in entities:
            entity_name = entity.get("name")
            ticker = entity.get("ticker")
            
            if entity_name:
                canonical_name = normalize_entity_name(entity_name)
                if canonical_name != entity_name:
                    entity["name"] = canonical_name
                    article_changed = True
                    stats["entities_normalized"] += 1
                    logger.debug(f"Normalizing entity '{entity_name}' -> '{canonical_name}' in article {article_id}")
            
            if ticker:
                canonical_ticker = normalize_entity_name(ticker)
                if canonical_ticker != ticker:
                    entity["ticker"] = canonical_ticker
                    article_changed = True
            
            updated_entities.append(entity)
        
        # Remove duplicates after normalization
        seen_entities = {}
        deduplicated_entities = []
        
        for entity in updated_entities:
            key = (entity.get("name"), entity.get("type"), entity.get("is_primary", True))
            if key not in seen_entities:
                seen_entities[key] = entity
                deduplicated_entities.append(entity)
            else:
                # Keep higher confidence
                if entity.get("confidence", 0) > seen_entities[key].get("confidence", 0):
                    seen_entities[key]["confidence"] = entity.get("confidence")
        
        # Apply changes if not dry run and article changed
        if not dry_run and article_changed:
            await collection.update_one(
                {"_id": article_id},
                {
                    "$set": {
                        "entities": deduplicated_entities,
                        "updated_at": datetime.now(timezone.utc),
                    }
                }
            )
            stats["articles_updated"] += 1
    
    return stats


async def main():
    """Main migration function."""
    parser = argparse.ArgumentParser(
        description="Migrate entity names to canonical form"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without applying them"
    )
    args = parser.parse_args()
    
    if args.dry_run:
        logger.info("=" * 60)
        logger.info("DRY RUN MODE - No changes will be applied")
        logger.info("=" * 60)
    else:
        logger.info("=" * 60)
        logger.info("LIVE MODE - Changes will be applied to database")
        logger.info("=" * 60)
        response = input("Are you sure you want to proceed? (yes/no): ")
        if response.lower() != "yes":
            logger.info("Migration cancelled")
            return
    
    try:
        # Migrate entity mentions
        logger.info("\n" + "=" * 60)
        logger.info("Migrating entity_mentions collection...")
        logger.info("=" * 60)
        mention_stats = await migrate_entity_mentions(dry_run=args.dry_run)
        
        logger.info("\nEntity Mentions Migration Results:")
        logger.info(f"  Total mentions: {mention_stats['total_mentions']}")
        logger.info(f"  Normalized: {mention_stats['normalized_mentions']}")
        logger.info(f"  Merged duplicates: {mention_stats['merged_duplicates']}")
        logger.info(f"  Unchanged: {mention_stats['unchanged_mentions']}")
        
        # Migrate article entities
        logger.info("\n" + "=" * 60)
        logger.info("Migrating articles collection...")
        logger.info("=" * 60)
        article_stats = await migrate_article_entities(dry_run=args.dry_run)
        
        logger.info("\nArticle Entities Migration Results:")
        logger.info(f"  Total articles: {article_stats['total_articles']}")
        logger.info(f"  Articles updated: {article_stats['articles_updated']}")
        logger.info(f"  Entities normalized: {article_stats['entities_normalized']}")
        
        if args.dry_run:
            logger.info("\n" + "=" * 60)
            logger.info("DRY RUN COMPLETE - No changes were applied")
            logger.info("Run without --dry-run to apply changes")
            logger.info("=" * 60)
        else:
            logger.info("\n" + "=" * 60)
            logger.info("MIGRATION COMPLETE")
            logger.info("=" * 60)
            logger.info("\nNext steps:")
            logger.info("1. Recalculate signals: python scripts/recalculate_signals.py")
            logger.info("2. Verify entity grouping in the UI")
    
    except Exception as e:
        logger.exception(f"Migration failed: {e}")
        raise
    finally:
        await mongo_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
