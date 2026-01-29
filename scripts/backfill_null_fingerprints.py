#!/usr/bin/env python3
"""
Backfill narrative fingerprints for narratives with NULL nucleus_entity.

This script fixes the 229 narratives that have narrative_fingerprint.nucleus_entity = None
by re-extracting entities from their associated articles and regenerating proper fingerprints.

The script:
1. Queries narratives where narrative_fingerprint.nucleus_entity is null or missing
2. For each narrative:
   a. Fetches its articles using article_ids from the narrative document
   b. Extracts entities from articles (actors, nucleus_entity, actor_salience)
   c. Builds aggregated data structure
   d. Generates fingerprint using compute_narrative_fingerprint()
   e. Updates narrative with new fingerprint
3. Supports --dry-run flag to preview changes
4. Supports --batch-size parameter (default 50) to process in batches
5. Logs progress and handles edge cases

Usage:
    # Preview changes (dry run)
    poetry run python scripts/backfill_null_fingerprints.py --dry-run
    
    # Process first 10 narratives
    poetry run python scripts/backfill_null_fingerprints.py --limit 10
    
    # Full backfill with custom batch size
    poetry run python scripts/backfill_null_fingerprints.py --batch-size 25
    
    # Full backfill (requires confirmation)
    poetry run python scripts/backfill_null_fingerprints.py
"""

import asyncio
import argparse
import sys
import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from collections import Counter, defaultdict
from bson import ObjectId

# Add src to path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, os.path.join(project_root, "src"))

from crypto_news_aggregator.db.mongodb import mongo_manager
from crypto_news_aggregator.services.narrative_themes import compute_narrative_fingerprint


class BackfillStats:
    """Track backfill statistics."""
    
    def __init__(self):
        self.total_narratives = 0
        self.processed_narratives = 0
        self.successful_updates = 0
        self.failed_narratives = 0
        self.skipped_no_articles = 0
        self.skipped_no_data = 0
        self.failed_narrative_ids = []
        self.failure_reasons = defaultdict(int)
    
    def add_success(self):
        """Record a successful update."""
        self.successful_updates += 1
        self.processed_narratives += 1
    
    def add_failure(self, narrative_id: str, reason: str):
        """Record a failure."""
        self.failed_narratives += 1
        self.processed_narratives += 1
        self.failed_narrative_ids.append(narrative_id)
        self.failure_reasons[reason] += 1
    
    def add_skip_no_articles(self):
        """Record a skip due to no articles."""
        self.skipped_no_articles += 1
        self.processed_narratives += 1
    
    def add_skip_no_data(self):
        """Record a skip due to no entity data."""
        self.skipped_no_data += 1
        self.processed_narratives += 1


async def get_narratives_with_null_fingerprints(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Query narratives where narrative_fingerprint.nucleus_entity is null or missing.
    
    Args:
        limit: Maximum number of narratives to return (None for all)
    
    Returns:
        List of narrative documents
    """
    db = await mongo_manager.get_async_database()
    collection = db.narratives
    
    # Query for narratives with null or missing nucleus_entity in fingerprint
    query = {
        '$or': [
            {'narrative_fingerprint.nucleus_entity': None},
            {'narrative_fingerprint.nucleus_entity': {'$exists': False}},
            {'narrative_fingerprint': {'$exists': False}}
        ]
    }
    
    cursor = collection.find(query).sort("created_at", -1)
    
    if limit:
        cursor = cursor.limit(limit)
    
    narratives = []
    async for narrative in cursor:
        narratives.append(narrative)
    
    return narratives


async def fetch_articles_for_narrative(
    article_ids: List[str],
    db
) -> List[Dict[str, Any]]:
    """
    Fetch article documents by their IDs.
    
    Args:
        article_ids: List of article ID strings
        db: Database instance
    
    Returns:
        List of article documents
    """
    articles_collection = db.articles
    
    # Convert string IDs to ObjectIds
    object_ids = []
    for aid in article_ids:
        if isinstance(aid, str) and ObjectId.is_valid(aid):
            object_ids.append(ObjectId(aid))
        elif isinstance(aid, ObjectId):
            object_ids.append(aid)
    
    if not object_ids:
        return []
    
    cursor = articles_collection.find({'_id': {'$in': object_ids}})
    articles = []
    async for article in cursor:
        articles.append(article)
    
    return articles


def extract_entities_from_articles(articles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Extract and aggregate entity data from articles.
    
    Args:
        articles: List of article documents
    
    Returns:
        Dict with aggregated entity data:
        {
            'nucleus_entity': str (most common nucleus),
            'actors': dict (combined actor salience),
            'actions': list (combined actions)
        }
    """
    # Collect all nucleus entities
    nucleus_entities = []
    
    # Collect all actors with their salience scores
    actor_salience_combined = defaultdict(list)
    
    # Collect all actions
    actions_combined = []
    
    for article in articles:
        # Extract nucleus entity
        nucleus = article.get('nucleus_entity')
        if nucleus:
            nucleus_entities.append(nucleus)
        
        # Extract actors
        actors = article.get('actors', [])
        
        # Extract actor salience
        actor_salience = article.get('actor_salience', {})
        
        # Combine actor salience scores
        for actor in actors:
            salience = actor_salience.get(actor, 3)  # Default to 3 if not specified
            actor_salience_combined[actor].append(salience)
        
        # Extract actions
        actions = article.get('actions', [])
        if actions:
            actions_combined.extend(actions)
    
    # Determine most common nucleus entity
    if nucleus_entities:
        nucleus_counter = Counter(nucleus_entities)
        most_common_nucleus = nucleus_counter.most_common(1)[0][0]
    else:
        most_common_nucleus = None
    
    # Average actor salience scores
    actor_salience_dict = {}
    for actor, salience_scores in actor_salience_combined.items():
        avg_salience = sum(salience_scores) / len(salience_scores)
        actor_salience_dict[actor] = round(avg_salience, 1)
    
    # Deduplicate actions (keep unique actions)
    unique_actions = list(set(actions_combined))
    
    return {
        'nucleus_entity': most_common_nucleus,
        'actors': actor_salience_dict,
        'actions': unique_actions
    }


async def update_narrative_fingerprint(
    narrative_id: ObjectId,
    fingerprint: Dict[str, Any],
    db,
    dry_run: bool = False
) -> bool:
    """
    Update a narrative with a new fingerprint.
    
    Args:
        narrative_id: Narrative ObjectId
        fingerprint: New fingerprint dict
        db: Database instance
        dry_run: If True, don't actually update
    
    Returns:
        True if successful, False otherwise
    """
    if dry_run:
        return True
    
    narratives_collection = db.narratives
    
    try:
        result = await narratives_collection.update_one(
            {'_id': narrative_id},
            {
                '$set': {
                    'narrative_fingerprint': fingerprint,
                    'fingerprint_backfilled_at': datetime.now(timezone.utc)
                }
            }
        )
        return result.modified_count > 0
    except Exception as e:
        print(f"Error updating narrative {narrative_id}: {e}")
        return False


async def process_narrative(
    narrative: Dict[str, Any],
    db,
    stats: BackfillStats,
    dry_run: bool = False,
    verbose: bool = False
) -> None:
    """
    Process a single narrative to regenerate its fingerprint.
    
    Args:
        narrative: Narrative document
        db: Database instance
        stats: Statistics tracker
        dry_run: If True, don't save changes
        verbose: If True, print detailed logs
    """
    narrative_id = narrative.get('_id')
    title = narrative.get('title', 'Unknown')
    
    # Get article IDs
    article_ids = narrative.get('article_ids', [])
    
    if not article_ids:
        if verbose:
            print(f"  ⚠️  Narrative '{title[:50]}...' has no articles - skipping")
        stats.add_skip_no_articles()
        return
    
    # Fetch articles
    try:
        articles = await fetch_articles_for_narrative(article_ids, db)
        
        if not articles:
            if verbose:
                print(f"  ⚠️  Narrative '{title[:50]}...' - no articles found in DB - skipping")
            stats.add_skip_no_articles()
            return
        
        # Extract entity data from articles
        cluster_data = extract_entities_from_articles(articles)
        
        # Check if we have enough data
        if not cluster_data['nucleus_entity']:
            if verbose:
                print(f"  ⚠️  Narrative '{title[:50]}...' - no nucleus entity found - skipping")
            stats.add_skip_no_data()
            return
        
        if not cluster_data['actors']:
            if verbose:
                print(f"  ⚠️  Narrative '{title[:50]}...' - no actors found - skipping")
            stats.add_skip_no_data()
            return
        
        # Generate fingerprint
        fingerprint = compute_narrative_fingerprint(cluster_data)
        
        # Update narrative
        success = await update_narrative_fingerprint(
            narrative_id,
            fingerprint,
            db,
            dry_run
        )
        
        if success:
            stats.add_success()
            if verbose:
                print(
                    f"  ✅ Updated '{title[:50]}...' - "
                    f"nucleus={fingerprint.get('nucleus_entity')}, "
                    f"actors={len(fingerprint.get('top_actors', []))}, "
                    f"actions={len(fingerprint.get('key_actions', []))}"
                )
        else:
            stats.add_failure(str(narrative_id), "update_failed")
            print(f"  ❌ Failed to update '{title[:50]}...'")
    
    except Exception as e:
        stats.add_failure(str(narrative_id), f"exception: {type(e).__name__}")
        print(f"  ❌ Error processing '{title[:50]}...': {e}")


async def process_batch(
    batch: List[Dict[str, Any]],
    batch_num: int,
    total_batches: int,
    db,
    stats: BackfillStats,
    dry_run: bool = False,
    verbose: bool = False
) -> None:
    """
    Process a batch of narratives.
    
    Args:
        batch: List of narrative documents
        batch_num: Current batch number (1-indexed)
        total_batches: Total number of batches
        db: Database instance
        stats: Statistics tracker
        dry_run: If True, don't save changes
        verbose: If True, print detailed logs
    """
    print(f"\n📦 Processing batch {batch_num}/{total_batches} ({len(batch)} narratives)")
    
    for narrative in batch:
        await process_narrative(narrative, db, stats, dry_run, verbose)
    
    # Print batch summary
    print(
        f"   Batch complete: {stats.successful_updates} successful, "
        f"{stats.failed_narratives} failed, "
        f"{stats.skipped_no_articles + stats.skipped_no_data} skipped"
    )


async def backfill_null_fingerprints(
    limit: Optional[int] = None,
    batch_size: int = 50,
    dry_run: bool = False,
    verbose: bool = False
) -> BackfillStats:
    """
    Main backfill function.
    
    Args:
        limit: Maximum number of narratives to process (None for all)
        batch_size: Number of narratives to process per batch
        dry_run: If True, don't save changes
        verbose: If True, print detailed logs
    
    Returns:
        Statistics about the backfill operation
    """
    stats = BackfillStats()
    
    # Get narratives
    print("🔍 Querying narratives with NULL fingerprints...")
    narratives = await get_narratives_with_null_fingerprints(limit)
    stats.total_narratives = len(narratives)
    
    if not narratives:
        print("✅ No narratives found with NULL fingerprints.")
        return stats
    
    print(f"📊 Found {len(narratives)} narratives to process")
    
    if dry_run:
        print("\n⚠️  DRY RUN MODE - No changes will be saved\n")
    
    # Get database
    db = await mongo_manager.get_async_database()
    
    # Process in batches
    total_batches = (len(narratives) + batch_size - 1) // batch_size
    
    for i in range(0, len(narratives), batch_size):
        batch = narratives[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        
        await process_batch(
            batch,
            batch_num,
            total_batches,
            db,
            stats,
            dry_run,
            verbose
        )
    
    return stats


def print_summary(stats: BackfillStats, dry_run: bool = False):
    """Print summary of backfill operation."""
    print("\n" + "="*70)
    print("BACKFILL SUMMARY")
    print("="*70)
    print(f"Total narratives found:        {stats.total_narratives}")
    print(f"Successfully updated:          {stats.successful_updates}")
    print(f"Failed:                        {stats.failed_narratives}")
    print(f"Skipped (no articles):         {stats.skipped_no_articles}")
    print(f"Skipped (no entity data):      {stats.skipped_no_data}")
    print(f"Total processed:               {stats.processed_narratives}")
    
    if stats.successful_updates > 0:
        success_rate = (stats.successful_updates / stats.total_narratives) * 100
        print(f"Success rate:                  {success_rate:.1f}%")
    
    if stats.failure_reasons:
        print(f"\nFailure breakdown:")
        for reason, count in stats.failure_reasons.items():
            print(f"  - {reason}: {count}")
    
    if stats.failed_narrative_ids:
        print(f"\nFailed narrative IDs ({len(stats.failed_narrative_ids)}):")
        for narrative_id in stats.failed_narrative_ids[:10]:
            print(f"  - {narrative_id}")
        if len(stats.failed_narrative_ids) > 10:
            print(f"  ... and {len(stats.failed_narrative_ids) - 10} more")
        
        # Write failed IDs to file
        failure_log = os.path.join(project_root, "backfill_null_fingerprints_failures.log")
        with open(failure_log, 'w') as f:
            f.write(f"Failed narrative IDs ({len(stats.failed_narrative_ids)}):\n")
            for narrative_id in stats.failed_narrative_ids:
                f.write(f"{narrative_id}\n")
        print(f"\n📝 Failed narrative IDs written to: {failure_log}")
    
    if dry_run:
        print("\n⚠️  This was a DRY RUN - no changes were saved")
    
    print("="*70)


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Backfill fingerprints for narratives with NULL nucleus_entity",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview changes (dry run)
  python scripts/backfill_null_fingerprints.py --dry-run
  
  # Process first 10 narratives
  python scripts/backfill_null_fingerprints.py --limit 10
  
  # Full backfill with custom batch size
  python scripts/backfill_null_fingerprints.py --batch-size 25
  
  # Full backfill with verbose output
  python scripts/backfill_null_fingerprints.py --verbose
        """
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process only N narratives (for testing)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Number of narratives to process per batch (default: 50)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without making changes"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed logs for each narrative"
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt"
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize MongoDB connection
        print("🔌 Connecting to MongoDB...")
        await mongo_manager.initialize()
        
        # Get narrative count
        narratives = await get_narratives_with_null_fingerprints(args.limit)
        narrative_count = len(narratives)
        
        if narrative_count == 0:
            print("✅ No narratives found with NULL fingerprints.")
            return
        
        # Show preview
        print(f"\n📊 Found {narrative_count} narratives with NULL fingerprints")
        if args.limit:
            print(f"   Will process up to {args.limit} narratives")
        else:
            print("   Will process ALL narratives")
        
        print(f"   Batch size: {args.batch_size}")
        
        if args.dry_run:
            print("   Mode: DRY RUN (no changes will be saved)")
        else:
            print("   Mode: LIVE (changes will be saved)")
        
        # Confirmation prompt (unless --yes or --dry-run)
        if not args.yes and not args.dry_run:
            response = input(f"\n❓ Proceed with backfill of {narrative_count} narratives? [y/N]: ")
            if response.lower() != 'y':
                print("❌ Aborted.")
                return
        
        # Run backfill
        print("\n🚀 Starting backfill...")
        stats = await backfill_null_fingerprints(
            limit=args.limit,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
            verbose=args.verbose
        )
        
        # Print summary
        print_summary(stats, args.dry_run)
        
        # Exit with appropriate code
        if stats.failed_narratives > 0:
            sys.exit(1)
        else:
            sys.exit(0)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Backfill interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Close MongoDB connection
        print("\n🔌 Closing MongoDB connection...")
        await mongo_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
