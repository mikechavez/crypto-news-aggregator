#!/usr/bin/env python3
"""
Merge duplicate narratives with matching fingerprints.

After running backfill_null_fingerprints.py, many narratives will have matching
nucleus_entity values (e.g., dozens about "Bitcoin", "Ethereum", etc.). This script
consolidates narratives with similar fingerprints to reduce duplication.

The script:
1. Queries all narratives, groups by nucleus_entity
2. For each group with 2+ narratives:
   a. Calculates pairwise fingerprint similarity
   b. If similarity >= threshold (0.6 default, 0.5 for recent):
      - Keeps narrative with most articles as primary
      - Merges article_ids from duplicates into primary
      - Updates primary with combined entity_salience
      - Updates lifecycle_state based on combined metrics
      - Deletes duplicate narratives
3. Supports --dry-run flag to preview merges
4. Supports --threshold parameter to override similarity threshold
5. Shows summary of merges

Usage:
    # Preview merges (dry run)
    poetry run python scripts/merge_duplicate_narratives.py --dry-run
    
    # Merge with default threshold (0.6 for older, 0.5 for recent)
    poetry run python scripts/merge_duplicate_narratives.py
    
    # Merge with custom threshold
    poetry run python scripts/merge_duplicate_narratives.py --threshold 0.7
    
    # Merge specific nucleus entity only
    poetry run python scripts/merge_duplicate_narratives.py --nucleus "Bitcoin"
"""

import asyncio
import argparse
import sys
import os
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from bson import ObjectId

# Add src to path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, os.path.join(project_root, "src"))

from crypto_news_aggregator.db.mongodb import mongo_manager
from crypto_news_aggregator.services.narrative_themes import calculate_fingerprint_similarity
from crypto_news_aggregator.services.narrative_service import determine_lifecycle_state


class MergeStats:
    """Track merge statistics."""
    
    def __init__(self):
        self.total_narratives = 0
        self.nucleus_groups = 0
        self.groups_with_duplicates = 0
        self.total_duplicates_found = 0
        self.merges_performed = 0
        self.narratives_deleted = 0
        self.articles_consolidated = 0
        self.merge_details = []
        self.failed_merges = []
    
    def add_merge(self, primary_title: str, duplicate_title: str, 
                  primary_articles: int, duplicate_articles: int, similarity: float):
        """Record a successful merge."""
        self.merges_performed += 1
        self.narratives_deleted += 1
        self.articles_consolidated += duplicate_articles
        self.merge_details.append({
            'primary': primary_title,
            'duplicate': duplicate_title,
            'primary_articles': primary_articles,
            'duplicate_articles': duplicate_articles,
            'similarity': similarity
        })
    
    def add_failure(self, primary_title: str, duplicate_title: str, reason: str):
        """Record a failed merge."""
        self.failed_merges.append({
            'primary': primary_title,
            'duplicate': duplicate_title,
            'reason': reason
        })


async def get_all_narratives() -> List[Dict[str, Any]]:
    """
    Query all narratives from the database.
    
    Returns:
        List of narrative documents
    """
    db = await mongo_manager.get_async_database()
    narratives_collection = db.narratives
    
    cursor = narratives_collection.find({})
    narratives = []
    async for narrative in cursor:
        narratives.append(narrative)
    
    return narratives


def group_narratives_by_nucleus(narratives: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Group narratives by their nucleus_entity.
    
    Args:
        narratives: List of narrative documents
    
    Returns:
        Dict mapping nucleus_entity to list of narratives
    """
    groups = defaultdict(list)
    
    for narrative in narratives:
        # Try to get nucleus from fingerprint first
        fingerprint = narrative.get('narrative_fingerprint') or narrative.get('fingerprint')
        if fingerprint:
            nucleus = fingerprint.get('nucleus_entity')
        else:
            # Fallback to legacy theme field
            nucleus = narrative.get('theme')
        
        if nucleus:
            groups[nucleus].append(narrative)
    
    return dict(groups)


def get_narrative_fingerprint(narrative: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract fingerprint from narrative, trying both field names.
    
    Args:
        narrative: Narrative document
    
    Returns:
        Fingerprint dict or None
    """
    # Try narrative_fingerprint first (new field)
    fingerprint = narrative.get('narrative_fingerprint')
    if fingerprint:
        return fingerprint
    
    # Try fingerprint (legacy field)
    fingerprint = narrative.get('fingerprint')
    if fingerprint:
        return fingerprint
    
    # Construct from legacy fields
    return {
        'nucleus_entity': narrative.get('theme', ''),
        'top_actors': narrative.get('entities', []),
        'key_actions': []
    }


def determine_adaptive_threshold(narrative: Dict[str, Any], base_threshold: float) -> float:
    """
    Determine adaptive threshold based on narrative recency.
    
    Recent narratives (updated within 48h) use lower threshold (0.5)
    to allow easier continuation. Older narratives use stricter threshold.
    
    Args:
        narrative: Narrative document
        base_threshold: Base threshold to use for older narratives
    
    Returns:
        Adaptive threshold (0.5 for recent, base_threshold for older)
    """
    last_updated = narrative.get('last_updated')
    if not last_updated:
        return base_threshold
    
    # Ensure timezone-aware
    if last_updated.tzinfo is None:
        last_updated = last_updated.replace(tzinfo=timezone.utc)
    
    # Check if updated within 48 hours
    now = datetime.now(timezone.utc)
    recent_cutoff = now - timedelta(hours=48)
    
    if last_updated >= recent_cutoff:
        return 0.5  # Recent: lower threshold
    else:
        return base_threshold  # Older: stricter threshold


def find_duplicate_pairs(
    narratives: List[Dict[str, Any]],
    base_threshold: float = 0.6
) -> List[Tuple[Dict[str, Any], Dict[str, Any], float]]:
    """
    Find pairs of narratives that should be merged based on fingerprint similarity.
    
    Args:
        narratives: List of narratives with same nucleus_entity
        base_threshold: Base similarity threshold for older narratives
    
    Returns:
        List of (narrative1, narrative2, similarity) tuples to merge
    """
    duplicate_pairs = []
    
    # Compare each pair
    for i in range(len(narratives)):
        for j in range(i + 1, len(narratives)):
            narrative1 = narratives[i]
            narrative2 = narratives[j]
            
            # Get fingerprints
            fp1 = get_narrative_fingerprint(narrative1)
            fp2 = get_narrative_fingerprint(narrative2)
            
            if not fp1 or not fp2:
                continue
            
            # Calculate similarity
            similarity = calculate_fingerprint_similarity(fp1, fp2)
            
            # Determine adaptive threshold (use the lower of the two)
            threshold1 = determine_adaptive_threshold(narrative1, base_threshold)
            threshold2 = determine_adaptive_threshold(narrative2, base_threshold)
            threshold = min(threshold1, threshold2)
            
            # Check if similarity meets threshold
            if similarity >= threshold:
                duplicate_pairs.append((narrative1, narrative2, similarity))
    
    return duplicate_pairs


def select_primary_narrative(
    narrative1: Dict[str, Any],
    narrative2: Dict[str, Any]
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Select which narrative should be the primary (kept) and which is duplicate (deleted).
    
    Selection criteria (in order):
    1. Most articles
    2. Most recent last_updated
    3. Earliest created_at (older narrative kept)
    
    Args:
        narrative1: First narrative
        narrative2: Second narrative
    
    Returns:
        (primary, duplicate) tuple
    """
    # Count articles
    articles1 = len(narrative1.get('article_ids', []))
    articles2 = len(narrative2.get('article_ids', []))
    
    if articles1 > articles2:
        return narrative1, narrative2
    elif articles2 > articles1:
        return narrative2, narrative1
    
    # Same article count - use most recent last_updated
    last_updated1 = narrative1.get('last_updated')
    last_updated2 = narrative2.get('last_updated')
    
    if last_updated1 and last_updated2:
        if last_updated1 > last_updated2:
            return narrative1, narrative2
        elif last_updated2 > last_updated1:
            return narrative2, narrative1
    
    # Same last_updated - use earliest created_at
    created1 = narrative1.get('created_at')
    created2 = narrative2.get('created_at')
    
    if created1 and created2:
        if created1 < created2:
            return narrative1, narrative2
        else:
            return narrative2, narrative1
    
    # Default to first narrative
    return narrative1, narrative2


def merge_article_ids(primary: Dict[str, Any], duplicate: Dict[str, Any]) -> List[str]:
    """
    Merge article_ids from duplicate into primary, removing duplicates.
    
    Args:
        primary: Primary narrative
        duplicate: Duplicate narrative
    
    Returns:
        Combined list of unique article IDs
    """
    primary_ids = set(primary.get('article_ids', []))
    duplicate_ids = set(duplicate.get('article_ids', []))
    
    # Combine and deduplicate
    combined_ids = list(primary_ids | duplicate_ids)
    
    return combined_ids


def merge_entity_salience(primary: Dict[str, Any], duplicate: Dict[str, Any]) -> Dict[str, float]:
    """
    Merge entity_salience from duplicate into primary, averaging scores.
    
    Args:
        primary: Primary narrative
        duplicate: Duplicate narrative
    
    Returns:
        Combined entity_salience dict with averaged scores
    """
    primary_salience = primary.get('entity_salience', {})
    duplicate_salience = duplicate.get('entity_salience', {})
    
    # Combine salience scores
    combined_salience = {}
    all_entities = set(primary_salience.keys()) | set(duplicate_salience.keys())
    
    for entity in all_entities:
        scores = []
        if entity in primary_salience:
            scores.append(primary_salience[entity])
        if entity in duplicate_salience:
            scores.append(duplicate_salience[entity])
        
        # Average the scores
        combined_salience[entity] = sum(scores) / len(scores)
    
    return combined_salience


async def merge_narratives(
    primary: Dict[str, Any],
    duplicate: Dict[str, Any],
    db,
    dry_run: bool = False
) -> bool:
    """
    Merge duplicate narrative into primary narrative.
    
    Args:
        primary: Primary narrative (kept)
        duplicate: Duplicate narrative (deleted)
        db: Database instance
        dry_run: If True, don't actually perform merge
    
    Returns:
        True if successful, False otherwise
    """
    if dry_run:
        return True
    
    narratives_collection = db.narratives
    
    try:
        # Merge article IDs
        combined_article_ids = merge_article_ids(primary, duplicate)
        
        # Merge entity salience
        combined_entity_salience = merge_entity_salience(primary, duplicate)
        
        # Calculate new lifecycle state based on combined metrics
        article_count = len(combined_article_ids)
        
        # Get time span of articles
        articles_collection = db.articles
        article_object_ids = [ObjectId(aid) if ObjectId.is_valid(aid) else aid 
                             for aid in combined_article_ids]
        
        cursor = articles_collection.find(
            {'_id': {'$in': article_object_ids}},
            {'published_at': 1}
        )
        
        article_dates = []
        async for article in cursor:
            pub_date = article.get('published_at')
            if pub_date:
                article_dates.append(pub_date)
        
        # Calculate lifecycle state
        if article_dates:
            # Ensure all dates are timezone-aware
            aware_dates = []
            for date in article_dates:
                if date.tzinfo is None:
                    date = date.replace(tzinfo=timezone.utc)
                aware_dates.append(date)
            
            earliest = min(aware_dates)
            latest = max(aware_dates)
            time_span_days = (latest - earliest).total_seconds() / 86400
            
            # Calculate mention velocity (articles per day)
            mention_velocity = article_count / max(time_span_days, 1.0)
            
            # Get previous state from primary narrative
            previous_state = primary.get('lifecycle_state')
            
            # Determine lifecycle state
            lifecycle_state = determine_lifecycle_state(
                article_count=article_count,
                mention_velocity=mention_velocity,
                first_seen=earliest,
                last_updated=latest,
                previous_state=previous_state
            )
        else:
            lifecycle_state = primary.get('lifecycle_state', 'emerging')
        
        # Update primary narrative
        update_result = await narratives_collection.update_one(
            {'_id': primary['_id']},
            {
                '$set': {
                    'article_ids': combined_article_ids,
                    'entity_salience': combined_entity_salience,
                    'lifecycle_state': lifecycle_state,
                    'article_count': article_count,
                    'last_updated': datetime.now(timezone.utc),
                    'merged_from': duplicate['_id'],
                    'merged_at': datetime.now(timezone.utc)
                }
            }
        )
        
        if update_result.modified_count == 0:
            return False
        
        # Delete duplicate narrative
        delete_result = await narratives_collection.delete_one({'_id': duplicate['_id']})
        
        return delete_result.deleted_count > 0
    
    except Exception as e:
        print(f"Error merging narratives: {e}")
        return False


async def process_nucleus_group(
    nucleus: str,
    narratives: List[Dict[str, Any]],
    db,
    stats: MergeStats,
    base_threshold: float = 0.6,
    dry_run: bool = False,
    verbose: bool = False
) -> None:
    """
    Process a group of narratives with the same nucleus_entity.
    
    Args:
        nucleus: Nucleus entity value
        narratives: List of narratives with this nucleus
        db: Database instance
        stats: Statistics tracker
        base_threshold: Base similarity threshold
        dry_run: If True, don't perform merges
        verbose: If True, print detailed logs
    """
    if len(narratives) < 2:
        return
    
    stats.groups_with_duplicates += 1
    
    if verbose:
        print(f"\n🔍 Checking nucleus '{nucleus}' ({len(narratives)} narratives)")
    
    # Find duplicate pairs
    duplicate_pairs = find_duplicate_pairs(narratives, base_threshold)
    
    if not duplicate_pairs:
        if verbose:
            print(f"   No duplicates found (similarity below threshold)")
        return
    
    stats.total_duplicates_found += len(duplicate_pairs)
    
    if verbose:
        print(f"   Found {len(duplicate_pairs)} duplicate pairs")
    
    # Track which narratives have been merged (deleted)
    merged_ids = set()
    
    # Process each duplicate pair
    for narrative1, narrative2, similarity in duplicate_pairs:
        # Skip if either narrative has already been merged
        if narrative1['_id'] in merged_ids or narrative2['_id'] in merged_ids:
            continue
        
        # Select primary and duplicate
        primary, duplicate = select_primary_narrative(narrative1, narrative2)
        
        primary_title = primary.get('title', 'Unknown')[:50]
        duplicate_title = duplicate.get('title', 'Unknown')[:50]
        primary_articles = len(primary.get('article_ids', []))
        duplicate_articles = len(duplicate.get('article_ids', []))
        
        # Perform merge
        success = await merge_narratives(primary, duplicate, db, dry_run)
        
        if success:
            # Mark duplicate as merged
            merged_ids.add(duplicate['_id'])
            
            stats.add_merge(
                primary_title,
                duplicate_title,
                primary_articles,
                duplicate_articles,
                similarity
            )
            
            if dry_run:
                print(
                    f"   [DRY RUN] Would merge '{duplicate_title}...' ({duplicate_articles} articles) "
                    f"→ '{primary_title}...' ({primary_articles} articles) "
                    f"[similarity: {similarity:.3f}]"
                )
            else:
                print(
                    f"   ✅ Merged '{duplicate_title}...' ({duplicate_articles} articles) "
                    f"→ '{primary_title}...' ({primary_articles} articles) "
                    f"[similarity: {similarity:.3f}]"
                )
        else:
            stats.add_failure(primary_title, duplicate_title, "merge_failed")
            print(
                f"   ❌ Failed to merge '{duplicate_title}...' → '{primary_title}...'"
            )


async def merge_duplicate_narratives(
    base_threshold: float = 0.6,
    nucleus_filter: Optional[str] = None,
    dry_run: bool = False,
    verbose: bool = False
) -> MergeStats:
    """
    Main merge function.
    
    Args:
        base_threshold: Base similarity threshold for older narratives
        nucleus_filter: Optional nucleus entity to filter by
        dry_run: If True, don't perform merges
        verbose: If True, print detailed logs
    
    Returns:
        Statistics about the merge operation
    """
    stats = MergeStats()
    
    # Get all narratives
    print("🔍 Querying all narratives...")
    narratives = await get_all_narratives()
    stats.total_narratives = len(narratives)
    
    if not narratives:
        print("✅ No narratives found.")
        return stats
    
    print(f"📊 Found {len(narratives)} total narratives")
    
    # Group by nucleus_entity
    print("📦 Grouping narratives by nucleus_entity...")
    groups = group_narratives_by_nucleus(narratives)
    stats.nucleus_groups = len(groups)
    
    print(f"📊 Found {len(groups)} unique nucleus entities")
    
    if dry_run:
        print("\n⚠️  DRY RUN MODE - No changes will be saved\n")
    
    # Filter by nucleus if specified
    if nucleus_filter:
        if nucleus_filter in groups:
            groups = {nucleus_filter: groups[nucleus_filter]}
            print(f"🎯 Filtering to nucleus: '{nucleus_filter}'")
        else:
            print(f"⚠️  Nucleus '{nucleus_filter}' not found")
            return stats
    
    # Get database
    db = await mongo_manager.get_async_database()
    
    # Process each group
    for nucleus, group_narratives in groups.items():
        await process_nucleus_group(
            nucleus,
            group_narratives,
            db,
            stats,
            base_threshold,
            dry_run,
            verbose
        )
    
    return stats


def print_summary(stats: MergeStats, dry_run: bool = False):
    """Print summary of merge operation."""
    print("\n" + "="*70)
    print("MERGE SUMMARY")
    print("="*70)
    print(f"Total narratives:              {stats.total_narratives}")
    print(f"Unique nucleus entities:       {stats.nucleus_groups}")
    print(f"Groups with duplicates:        {stats.groups_with_duplicates}")
    print(f"Duplicate pairs found:         {stats.total_duplicates_found}")
    print(f"Merges performed:              {stats.merges_performed}")
    print(f"Narratives deleted:            {stats.narratives_deleted}")
    print(f"Articles consolidated:         {stats.articles_consolidated}")
    
    if stats.merges_performed > 0:
        final_count = stats.total_narratives - stats.narratives_deleted
        reduction_pct = (stats.narratives_deleted / stats.total_narratives) * 100
        print(f"\nReduction: {stats.total_narratives} → {final_count} narratives ({reduction_pct:.1f}% reduction)")
    
    if stats.failed_merges:
        print(f"\nFailed merges: {len(stats.failed_merges)}")
        for failure in stats.failed_merges[:5]:
            print(f"  - '{failure['primary']}...' ← '{failure['duplicate']}...' ({failure['reason']})")
        if len(stats.failed_merges) > 5:
            print(f"  ... and {len(stats.failed_merges) - 5} more")
    
    if dry_run:
        print("\n⚠️  This was a DRY RUN - no changes were saved")
    
    print("="*70)
    
    # Show top merges if verbose
    if stats.merge_details and len(stats.merge_details) <= 20:
        print("\nMerge Details:")
        for detail in stats.merge_details:
            print(
                f"  '{detail['duplicate']}...' ({detail['duplicate_articles']} articles) "
                f"→ '{detail['primary']}...' ({detail['primary_articles']} articles) "
                f"[{detail['similarity']:.3f}]"
            )


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Merge duplicate narratives with matching fingerprints",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview merges (dry run)
  python scripts/merge_duplicate_narratives.py --dry-run
  
  # Merge with default threshold
  python scripts/merge_duplicate_narratives.py
  
  # Merge with custom threshold
  python scripts/merge_duplicate_narratives.py --threshold 0.7
  
  # Merge specific nucleus entity only
  python scripts/merge_duplicate_narratives.py --nucleus "Bitcoin"
        """
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.6,
        help="Base similarity threshold for older narratives (default: 0.6, recent: 0.5)"
    )
    parser.add_argument(
        "--nucleus",
        type=str,
        default=None,
        help="Only merge narratives with this nucleus_entity"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview merges without executing"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed logs for each group"
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
        narratives = await get_all_narratives()
        narrative_count = len(narratives)
        
        if narrative_count == 0:
            print("✅ No narratives found.")
            return
        
        # Show preview
        print(f"\n📊 Found {narrative_count} narratives")
        print(f"   Base threshold: {args.threshold} (older narratives)")
        print(f"   Adaptive threshold: 0.5 (recent narratives within 48h)")
        
        if args.nucleus:
            print(f"   Filtering to nucleus: '{args.nucleus}'")
        
        if args.dry_run:
            print("   Mode: DRY RUN (no changes will be saved)")
        else:
            print("   Mode: LIVE (changes will be saved)")
        
        # Confirmation prompt (unless --yes or --dry-run)
        if not args.yes and not args.dry_run:
            response = input(f"\n❓ Proceed with merge? [y/N]: ")
            if response.lower() != 'y':
                print("❌ Aborted.")
                return
        
        # Run merge
        print("\n🚀 Starting merge...")
        stats = await merge_duplicate_narratives(
            base_threshold=args.threshold,
            nucleus_filter=args.nucleus,
            dry_run=args.dry_run,
            verbose=args.verbose
        )
        
        # Print summary
        print_summary(stats, args.dry_run)
        
        # Exit with appropriate code
        if stats.failed_merges:
            sys.exit(1)
        else:
            sys.exit(0)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Merge interrupted by user")
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
