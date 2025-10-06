#!/usr/bin/env python3
"""
Verification script to check if signal normalization is working in production.

This script checks:
1. Signal scores collection for duplicate entities
2. Entity mentions for normalization
3. Recent signal calculations

Usage:
    python scripts/verify_signal_normalization.py
"""

import asyncio
import logging
from collections import defaultdict

from crypto_news_aggregator.db.mongodb import mongo_manager
from crypto_news_aggregator.services.entity_normalization import normalize_entity_name

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def check_duplicate_signals(db):
    """Check for duplicate signal scores that should be merged."""
    signal_scores_collection = db.signal_scores
    
    logger.info("=" * 70)
    logger.info("CHECKING FOR DUPLICATE SIGNAL SCORES")
    logger.info("=" * 70)
    
    # Get all signal scores
    cursor = signal_scores_collection.find({})
    
    # Group by canonical name
    canonical_map = defaultdict(list)
    async for signal in cursor:
        entity = signal.get("entity")
        canonical = normalize_entity_name(entity)
        canonical_map[canonical].append({
            "entity": entity,
            "score": signal.get("score"),
            "velocity": signal.get("velocity"),
            "source_count": signal.get("source_count"),
        })
    
    # Find duplicates
    duplicates = {k: v for k, v in canonical_map.items() if len(v) > 1}
    
    if duplicates:
        logger.warning(f"❌ Found {len(duplicates)} entities with duplicate signals:")
        for canonical, variants in duplicates.items():
            logger.warning(f"\n  Canonical: {canonical}")
            for variant in variants:
                logger.warning(f"    - {variant['entity']}: score={variant['score']}, velocity={variant['velocity']}")
        return False
    else:
        logger.info("✅ No duplicate signals found - normalization is working!")
        return True


async def check_entity_mentions(db):
    """Check entity mentions for common variants that should be normalized."""
    entity_mentions_collection = db.entity_mentions
    
    logger.info("\n" + "=" * 70)
    logger.info("CHECKING ENTITY MENTIONS FOR NORMALIZATION")
    logger.info("=" * 70)
    
    # Check for common variants
    variants_to_check = [
        ("$DOGE", "Dogecoin"),
        ("$BTC", "Bitcoin"),
        ("$ETH", "Ethereum"),
        ("BTC", "Bitcoin"),
        ("ETH", "Ethereum"),
        ("DOGE", "Dogecoin"),
        ("doge", "Dogecoin"),
        ("btc", "Bitcoin"),
    ]
    
    issues = []
    for variant, canonical in variants_to_check:
        count = await entity_mentions_collection.count_documents({"entity": variant})
        if count > 0:
            issues.append(f"Found {count} mentions of '{variant}' (should be '{canonical}')")
    
    if issues:
        logger.warning("❌ Entity mention normalization issues:")
        for issue in issues:
            logger.warning(f"  - {issue}")
        return False
    else:
        logger.info("✅ Entity mentions are properly normalized")
        return True


async def show_top_signals(db):
    """Show top signal scores to verify no duplicates in rankings."""
    signal_scores_collection = db.signal_scores
    
    logger.info("\n" + "=" * 70)
    logger.info("TOP 10 SIGNAL SCORES")
    logger.info("=" * 70)
    
    cursor = signal_scores_collection.find({}).sort("score", -1).limit(10)
    
    rank = 1
    async for signal in cursor:
        entity = signal.get("entity")
        score = signal.get("score")
        velocity = signal.get("velocity")
        source_count = signal.get("source_count")
        
        logger.info(f"#{rank}: {entity}")
        logger.info(f"     Score: {score}, Velocity: {velocity}, Sources: {source_count}")
        rank += 1
    
    logger.info("")


async def check_normalization_in_action(db):
    """Check if recent entity mentions are being normalized."""
    entity_mentions_collection = db.entity_mentions
    
    logger.info("=" * 70)
    logger.info("RECENT ENTITY MENTIONS (Last 20)")
    logger.info("=" * 70)
    
    cursor = entity_mentions_collection.find({}).sort("created_at", -1).limit(20)
    
    normalized_count = 0
    total_count = 0
    
    async for mention in cursor:
        entity = mention.get("entity")
        canonical = normalize_entity_name(entity)
        is_normalized = (entity == canonical)
        
        total_count += 1
        if is_normalized:
            normalized_count += 1
        
        status = "✅" if is_normalized else "⚠️"
        logger.info(f"{status} {entity}" + (f" (canonical)" if is_normalized else f" -> should be {canonical}"))
    
    logger.info(f"\nNormalization rate: {normalized_count}/{total_count} ({100*normalized_count/total_count:.1f}%)")
    
    return normalized_count == total_count


async def main():
    """Run all verification checks."""
    db = await mongo_manager.get_async_database()
    
    logger.info("\n" + "=" * 70)
    logger.info("SIGNAL NORMALIZATION VERIFICATION")
    logger.info("=" * 70 + "\n")
    
    # Run checks
    signals_ok = await check_duplicate_signals(db)
    mentions_ok = await check_entity_mentions(db)
    await show_top_signals(db)
    recent_ok = await check_normalization_in_action(db)
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("VERIFICATION SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Signal scores: {'✅ PASS' if signals_ok else '❌ FAIL'}")
    logger.info(f"Entity mentions: {'✅ PASS' if mentions_ok else '❌ FAIL'}")
    logger.info(f"Recent normalization: {'✅ PASS' if recent_ok else '⚠️ WARNING'}")
    
    all_ok = signals_ok and mentions_ok
    
    if all_ok:
        logger.info("\n✅ All checks passed! Entity normalization is working correctly.")
    else:
        logger.warning("\n❌ Some checks failed. Review the issues above.")
        logger.warning("\nRecommended actions:")
        if not signals_ok:
            logger.warning("  1. Run migration script: python scripts/migrate_signal_scores_normalization.py --production")
        if not mentions_ok:
            logger.warning("  2. Run entity mention migration: python scripts/migrate_entity_normalization.py")
    
    logger.info("=" * 70 + "\n")
    
    await mongo_manager.close()
    
    return 0 if all_ok else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
