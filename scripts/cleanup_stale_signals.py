#!/usr/bin/env python3
"""
Quick cleanup script for stale signal_scores.

Removes signal_scores for entities that have no current entity_mentions.
These are leftover from deleted articles/mentions.
"""

import asyncio
import argparse

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.crypto_news_aggregator.db.mongodb import mongo_manager, initialize_mongodb


async def cleanup_stale_signals(dry_run: bool = True):
    """
    Find and remove stale signal_scores.
    
    Args:
        dry_run: If True, don't actually delete
    """
    await initialize_mongodb()
    db = await mongo_manager.get_async_database()
    
    try:
        signal_scores = db.signal_scores
        entity_mentions = db.entity_mentions
        
        print("=" * 70)
        print("STALE SIGNAL SCORES CLEANUP")
        print("=" * 70)
        
        if dry_run:
            print("\n🔍 DRY RUN MODE - No data will be deleted\n")
        else:
            print("\n⚠️  LIVE MODE - Stale signals will be permanently deleted\n")
        
        # Get all signal scores
        print("Fetching all signal scores...")
        all_signals = await signal_scores.find({}).to_list(length=None)
        print(f"Total signal scores: {len(all_signals)}")
        
        # Find stale ones
        print("\nChecking for stale signals...")
        stale_signals = []
        
        for i, signal in enumerate(all_signals):
            if (i + 1) % 50 == 0:
                print(f"  Checked {i + 1}/{len(all_signals)}...", end='\r')
            
            entity = signal.get("entity")
            if not entity:
                stale_signals.append(signal)
                continue
            
            # Check if there are any entity_mentions for this entity
            mention_count = await entity_mentions.count_documents(
                {"entity": entity},
                limit=1
            )
            
            if mention_count == 0:
                stale_signals.append(signal)
        
        print(f"\n\nFound {len(stale_signals)} stale signal scores")
        
        # Show details
        if stale_signals:
            print("\nStale signals to be removed:")
            for signal in stale_signals:
                print(f"  - {signal.get('entity')} ({signal.get('entity_type')}): "
                      f"Score 7d={signal.get('score_7d')}, "
                      f"Last updated={signal.get('last_updated')}")
        
        # Delete if not dry run
        if not dry_run and stale_signals:
            print(f"\nDeleting {len(stale_signals)} stale signals...")
            signal_ids = [s["_id"] for s in stale_signals]
            result = await signal_scores.delete_many({"_id": {"$in": signal_ids}})
            print(f"✅ Deleted {result.deleted_count} stale signal scores")
        elif dry_run and stale_signals:
            print(f"\nDRY RUN: Would delete {len(stale_signals)} stale signals")
        else:
            print("\nNo stale signals to delete")
        
        # Verify
        remaining = await signal_scores.count_documents({})
        print(f"\nRemaining signal scores: {remaining}")
        
        print("\n✅ Cleanup complete!")
        
    finally:
        await mongo_manager.aclose()


async def main():
    parser = argparse.ArgumentParser(description="Clean up stale signal scores")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Show what would be deleted without actually deleting (default)"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually delete the stale signals (overrides --dry-run)"
    )
    
    args = parser.parse_args()
    
    # If --execute is specified, turn off dry_run
    dry_run = not args.execute
    
    if not dry_run:
        response = input("Are you sure you want to delete stale signals? (yes/no): ")
        if response.lower() != "yes":
            print("Aborted")
            return
    
    await cleanup_stale_signals(dry_run=dry_run)


if __name__ == "__main__":
    asyncio.run(main())
