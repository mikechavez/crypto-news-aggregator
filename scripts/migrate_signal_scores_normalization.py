#!/usr/bin/env python3
"""
Production migration script to fix duplicate signal scores caused by entity normalization.

This script:
1. Deletes all existing signal_scores (they will be regenerated)
2. Verifies entity_mentions are normalized
3. Forces recalculation of signal scores using canonical entity names

Usage:
    # For production (Railway):
    python scripts/migrate_signal_scores_normalization.py --production
    
    # For local testing:
    python scripts/migrate_signal_scores_normalization.py
"""

import asyncio
import argparse
import logging
from datetime import datetime, timezone

from crypto_news_aggregator.db.mongodb import mongo_manager
from crypto_news_aggregator.services.signal_service import calculate_signal_score
from crypto_news_aggregator.db.operations.signal_scores import upsert_signal_score
from crypto_news_aggregator.services.entity_normalization import normalize_entity_name

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def verify_entity_mentions_normalized(db):
    """Verify that entity_mentions are using canonical names."""
    entity_mentions_collection = db.entity_mentions
    
    logger.info("Checking entity_mentions for normalization issues...")
    
    # Sample check: look for common variants
    variants_to_check = [
        ("$DOGE", "Dogecoin"),
        ("$BTC", "Bitcoin"),
        ("$ETH", "Ethereum"),
        ("BTC", "Bitcoin"),
        ("ETH", "Ethereum"),
        ("DOGE", "Dogecoin"),
    ]
    
    issues_found = []
    for variant, canonical in variants_to_check:
        count = await entity_mentions_collection.count_documents({"entity": variant})
        if count > 0:
            issues_found.append(f"Found {count} mentions of '{variant}' (should be '{canonical}')")
    
    if issues_found:
        logger.warning("Entity mention normalization issues found:")
        for issue in issues_found:
            logger.warning(f"  - {issue}")
        return False
    else:
        logger.info("✓ Entity mentions appear to be normalized correctly")
        return True


async def clear_signal_scores(db, dry_run=False):
    """Delete all signal scores to force clean recalculation."""
    signal_scores_collection = db.signal_scores
    
    count = await signal_scores_collection.count_documents({})
    logger.info(f"Found {count} existing signal scores")
    
    if dry_run:
        logger.info("[DRY RUN] Would delete all signal scores")
        return count
    
    result = await signal_scores_collection.delete_many({})
    logger.info(f"✓ Deleted {result.deleted_count} signal scores")
    return result.deleted_count


async def recalculate_signals_with_normalization(db, dry_run=False):
    """Recalculate signal scores using normalized entity names."""
    entity_mentions_collection = db.entity_mentions
    
    # Get all unique entities from entity_mentions (primary only)
    unique_entities = await entity_mentions_collection.distinct(
        "entity",
        {"is_primary": True}
    )
    
    logger.info(f"Found {len(unique_entities)} unique entities to score")
    
    # Group by canonical name
    canonical_entities = {}
    for entity in unique_entities:
        canonical = normalize_entity_name(entity)
        if canonical not in canonical_entities:
            canonical_entities[canonical] = []
        canonical_entities[canonical].append(entity)
    
    # Log any entities that map to the same canonical name
    duplicates_found = []
    for canonical, variants in canonical_entities.items():
        if len(variants) > 1:
            duplicates_found.append(f"{canonical}: {variants}")
    
    if duplicates_found:
        logger.info(f"Found {len(duplicates_found)} entities with multiple variants:")
        for dup in duplicates_found[:10]:  # Show first 10
            logger.info(f"  - {dup}")
    
    logger.info(f"Will calculate {len(canonical_entities)} unique signal scores")
    
    if dry_run:
        logger.info("[DRY RUN] Would recalculate signal scores")
        return len(canonical_entities)
    
    # Calculate signals for each canonical entity
    processed = 0
    errors = 0
    
    for canonical_entity in canonical_entities.keys():
        try:
            # Calculate signal score (this will use canonical name internally)
            signal_data = await calculate_signal_score(canonical_entity)
            
            # Get first_seen timestamp
            first_mention = await entity_mentions_collection.find_one(
                {"entity": canonical_entity, "is_primary": True},
                sort=[("created_at", 1)]
            )
            first_seen = first_mention["created_at"] if first_mention else datetime.now(timezone.utc)
            
            # Get entity type from first mention
            entity_type = first_mention.get("entity_type", "cryptocurrency") if first_mention else "cryptocurrency"
            
            # Store the signal score
            await upsert_signal_score(
                entity=canonical_entity,
                entity_type=entity_type,
                score=signal_data["score"],
                velocity=signal_data["velocity"],
                source_count=signal_data["source_count"],
                sentiment=signal_data["sentiment"],
                first_seen=first_seen,
            )
            
            processed += 1
            
            if processed % 10 == 0:
                logger.info(f"Progress: {processed}/{len(canonical_entities)} entities scored")
        
        except Exception as e:
            logger.error(f"Failed to calculate signal for '{canonical_entity}': {e}")
            errors += 1
    
    logger.info(f"✓ Signal recalculation complete: {processed} processed, {errors} errors")
    return processed


async def run_migration(production=False, dry_run=False):
    """Run the full migration."""
    db = await mongo_manager.get_async_database()
    
    mode = "PRODUCTION" if production else "LOCAL"
    run_type = "DRY RUN" if dry_run else "LIVE"
    
    logger.info("=" * 70)
    logger.info(f"Signal Score Normalization Migration - {mode} - {run_type}")
    logger.info("=" * 70)
    
    # Step 1: Verify entity mentions
    logger.info("\n[STEP 1] Verifying entity_mentions normalization...")
    mentions_ok = await verify_entity_mentions_normalized(db)
    
    if not mentions_ok and not dry_run:
        logger.error("Entity mentions are not properly normalized!")
        logger.error("Run entity normalization migration first:")
        logger.error("  python scripts/migrate_entity_normalization.py")
        return False
    
    # Step 2: Clear existing signal scores
    logger.info("\n[STEP 2] Clearing existing signal scores...")
    deleted_count = await clear_signal_scores(db, dry_run=dry_run)
    
    # Step 3: Recalculate with normalization
    logger.info("\n[STEP 3] Recalculating signal scores with normalization...")
    recalculated_count = await recalculate_signals_with_normalization(db, dry_run=dry_run)
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("MIGRATION SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Mode: {mode} - {run_type}")
    logger.info(f"Signal scores deleted: {deleted_count}")
    logger.info(f"Signal scores recalculated: {recalculated_count}")
    logger.info(f"Entity mentions normalized: {'✓' if mentions_ok else '✗'}")
    
    if not dry_run:
        logger.info("\n✓ Migration completed successfully!")
        logger.info("\nNext steps:")
        logger.info("1. Wait 2 minutes for signal worker to run")
        logger.info("2. Check UI for duplicate entities")
        logger.info("3. Verify Railway logs show normalization messages")
    else:
        logger.info("\nThis was a DRY RUN. Run without --dry-run to apply changes.")
    
    logger.info("=" * 70)
    
    return True


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Migrate signal scores to use normalized entity names"
    )
    parser.add_argument(
        "--production",
        action="store_true",
        help="Run against production database (Railway)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    
    args = parser.parse_args()
    
    try:
        success = await run_migration(
            production=args.production,
            dry_run=args.dry_run
        )
        
        if not success:
            exit(1)
    
    except Exception as e:
        logger.exception(f"Migration failed: {e}")
        raise
    finally:
        await mongo_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
