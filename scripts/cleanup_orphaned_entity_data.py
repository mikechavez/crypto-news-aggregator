#!/usr/bin/env python3
"""
Cleanup script for orphaned entity data.

This script identifies and removes:
1. Orphaned entity_mentions (references to non-existent articles)
2. Stale signal_scores (entities with no current mentions)

Run with --dry-run to see what would be deleted without actually deleting.
"""

import asyncio
import argparse
from datetime import datetime, timezone
from typing import List, Dict, Any
from bson import ObjectId

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.crypto_news_aggregator.db.mongodb import mongo_manager, initialize_mongodb


async def find_orphaned_entity_mentions(db) -> List[Dict[str, Any]]:
    """
    Find entity_mentions that reference non-existent articles.
    
    Returns:
        List of orphaned entity_mention documents
    """
    print("\n=== Finding Orphaned Entity Mentions ===")
    
    entity_mentions = db.entity_mentions
    articles = db.articles
    
    # Get all entity mentions
    all_mentions = await entity_mentions.find({}).to_list(length=None)
    print(f"Total entity mentions: {len(all_mentions)}")
    
    orphaned_mentions = []
    checked = 0
    
    for mention in all_mentions:
        checked += 1
        if checked % 1000 == 0:
            print(f"Checked {checked}/{len(all_mentions)} mentions...")
        
        article_id = mention.get("article_id")
        if not article_id:
            orphaned_mentions.append(mention)
            continue
        
        # Try to find the article
        try:
            # Convert to ObjectId if it's a string
            if isinstance(article_id, str):
                article_oid = ObjectId(article_id)
            else:
                article_oid = article_id
            
            article = await articles.find_one({"_id": article_oid})
            
            if not article:
                orphaned_mentions.append(mention)
        except Exception as e:
            # Invalid ObjectId or other error
            orphaned_mentions.append(mention)
    
    print(f"Found {len(orphaned_mentions)} orphaned entity mentions")
    
    # Show sample
    if orphaned_mentions:
        print("\nSample orphaned mentions:")
        for mention in orphaned_mentions[:5]:
            print(f"  - Entity: {mention.get('entity')}, Article ID: {mention.get('article_id')}, "
                  f"Created: {mention.get('created_at')}")
    
    return orphaned_mentions


async def find_stale_signal_scores(db) -> List[Dict[str, Any]]:
    """
    Find signal_scores for entities that have no current entity_mentions.
    
    Returns:
        List of stale signal_score documents
    """
    print("\n=== Finding Stale Signal Scores ===")
    
    signal_scores = db.signal_scores
    entity_mentions = db.entity_mentions
    
    # Get all signal scores
    all_signals = await signal_scores.find({}).to_list(length=None)
    print(f"Total signal scores: {len(all_signals)}")
    
    stale_signals = []
    checked = 0
    
    for signal in all_signals:
        checked += 1
        if checked % 100 == 0:
            print(f"Checked {checked}/{len(all_signals)} signals...")
        
        entity = signal.get("entity")
        if not entity:
            stale_signals.append(signal)
            continue
        
        # Check if there are any entity_mentions for this entity
        mention_count = await entity_mentions.count_documents({"entity": entity})
        
        if mention_count == 0:
            stale_signals.append(signal)
    
    print(f"Found {len(stale_signals)} stale signal scores")
    
    # Show sample
    if stale_signals:
        print("\nSample stale signals:")
        for signal in stale_signals[:10]:
            print(f"  - Entity: {signal.get('entity')}, Type: {signal.get('entity_type')}, "
                  f"Score 7d: {signal.get('score_7d')}, Last Updated: {signal.get('last_updated')}")
    
    return stale_signals


async def cleanup_orphaned_mentions(db, orphaned_mentions: List[Dict[str, Any]], dry_run: bool = True):
    """
    Delete orphaned entity_mentions.
    
    Args:
        db: Database connection
        orphaned_mentions: List of orphaned mention documents
        dry_run: If True, don't actually delete
    """
    if not orphaned_mentions:
        print("\nNo orphaned mentions to clean up")
        return
    
    print(f"\n=== Cleaning Up {len(orphaned_mentions)} Orphaned Mentions ===")
    
    if dry_run:
        print("DRY RUN - No actual deletions will occur")
        return
    
    entity_mentions = db.entity_mentions
    mention_ids = [m["_id"] for m in orphaned_mentions]
    
    result = await entity_mentions.delete_many({"_id": {"$in": mention_ids}})
    print(f"✅ Deleted {result.deleted_count} orphaned entity mentions")


async def cleanup_stale_signals(db, stale_signals: List[Dict[str, Any]], dry_run: bool = True):
    """
    Delete stale signal_scores.
    
    Args:
        db: Database connection
        stale_signals: List of stale signal documents
        dry_run: If True, don't actually delete
    """
    if not stale_signals:
        print("\nNo stale signals to clean up")
        return
    
    print(f"\n=== Cleaning Up {len(stale_signals)} Stale Signal Scores ===")
    
    if dry_run:
        print("DRY RUN - No actual deletions will occur")
        return
    
    signal_scores = db.signal_scores
    signal_ids = [s["_id"] for s in stale_signals]
    
    result = await signal_scores.delete_many({"_id": {"$in": signal_ids}})
    print(f"✅ Deleted {result.deleted_count} stale signal scores")


async def verify_data_integrity(db):
    """
    Verify data integrity after cleanup.
    """
    print("\n=== Verifying Data Integrity ===")
    
    entity_mentions = db.entity_mentions
    signal_scores = db.signal_scores
    articles = db.articles
    
    # Count documents
    mention_count = await entity_mentions.count_documents({})
    signal_count = await signal_scores.count_documents({})
    article_count = await articles.count_documents({})
    
    print(f"Entity mentions: {mention_count}")
    print(f"Signal scores: {signal_count}")
    print(f"Articles: {article_count}")
    
    # Sample check: verify a few random mentions have valid articles
    sample_mentions = await entity_mentions.find({}).limit(10).to_list(length=10)
    valid_count = 0
    
    for mention in sample_mentions:
        article_id = mention.get("article_id")
        if article_id:
            try:
                if isinstance(article_id, str):
                    article_oid = ObjectId(article_id)
                else:
                    article_oid = article_id
                
                article = await articles.find_one({"_id": article_oid})
                if article:
                    valid_count += 1
            except:
                pass
    
    print(f"\nSample check: {valid_count}/{len(sample_mentions)} mentions have valid articles")
    
    if valid_count == len(sample_mentions):
        print("✅ Data integrity looks good!")
    else:
        print("⚠️  Some mentions may still reference invalid articles")


async def main():
    parser = argparse.ArgumentParser(description="Clean up orphaned entity data")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting"
    )
    parser.add_argument(
        "--skip-mentions",
        action="store_true",
        help="Skip cleanup of orphaned entity_mentions"
    )
    parser.add_argument(
        "--skip-signals",
        action="store_true",
        help="Skip cleanup of stale signal_scores"
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("ORPHANED ENTITY DATA CLEANUP")
    print("=" * 70)
    
    if args.dry_run:
        print("\n🔍 DRY RUN MODE - No data will be deleted\n")
    else:
        print("\n⚠️  LIVE MODE - Data will be permanently deleted\n")
        response = input("Are you sure you want to proceed? (yes/no): ")
        if response.lower() != "yes":
            print("Aborted")
            return
    
    # Initialize database
    await initialize_mongodb()
    db = await mongo_manager.get_async_database()
    
    try:
        # Find orphaned data
        orphaned_mentions = []
        stale_signals = []
        
        if not args.skip_mentions:
            orphaned_mentions = await find_orphaned_entity_mentions(db)
        
        if not args.skip_signals:
            stale_signals = await find_stale_signal_scores(db)
        
        # Summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Orphaned entity_mentions: {len(orphaned_mentions)}")
        print(f"Stale signal_scores: {len(stale_signals)}")
        
        # Cleanup
        if not args.skip_mentions:
            await cleanup_orphaned_mentions(db, orphaned_mentions, dry_run=args.dry_run)
        
        if not args.skip_signals:
            await cleanup_stale_signals(db, stale_signals, dry_run=args.dry_run)
        
        # Verify if not dry run
        if not args.dry_run:
            await verify_data_integrity(db)
        
        print("\n✅ Cleanup complete!")
        
    finally:
        await mongo_manager.aclose()


if __name__ == "__main__":
    asyncio.run(main())
