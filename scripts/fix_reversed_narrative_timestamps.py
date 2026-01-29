#!/usr/bin/env python3
"""
Fix reversed narrative timestamps where first_seen > last_updated.

This script identifies and corrects data corruption in the narratives collection
where first_seen timestamps are later than last_updated timestamps, which is
logically impossible.

The fix ensures that for each narrative:
- first_seen <= last_updated
- If reversed, swaps the values to restore logical consistency

Usage:
    python scripts/fix_reversed_narrative_timestamps.py [--dry-run]

Options:
    --dry-run    Show what would be fixed without making changes
"""

import asyncio
import logging
import sys
from datetime import datetime, timezone
from typing import Dict, Any, List

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import after setting up logging
from crypto_news_aggregator.db.mongodb import mongo_manager


async def find_reversed_narratives() -> List[Dict[str, Any]]:
    """
    Find all narratives where first_seen > last_updated.
    
    Returns:
        List of narrative documents with reversed timestamps
    """
    db = await mongo_manager.get_async_database()
    collection = db.narratives
    
    # Use aggregation pipeline to find reversed timestamps
    pipeline = [
        {
            "$addFields": {
                "isReversed": {
                    "$gt": ["$first_seen", "$last_updated"]
                }
            }
        },
        {
            "$match": {
                "isReversed": True
            }
        },
        {
            "$project": {
                "_id": 1,
                "theme": 1,
                "title": 1,
                "first_seen": 1,
                "last_updated": 1,
                "isReversed": 1
            }
        }
    ]
    
    reversed_narratives = []
    async for doc in collection.aggregate(pipeline):
        reversed_narratives.append(doc)
    
    return reversed_narratives


async def fix_reversed_timestamps(dry_run: bool = False) -> Dict[str, Any]:
    """
    Fix narratives with reversed timestamps.
    
    Args:
        dry_run: If True, only report what would be fixed without making changes
    
    Returns:
        Dictionary with fix statistics
    """
    db = await mongo_manager.get_async_database()
    collection = db.narratives
    
    # Find reversed narratives
    reversed_narratives = await find_reversed_narratives()
    
    if not reversed_narratives:
        logger.info("✓ No narratives with reversed timestamps found")
        return {
            "total_checked": 0,
            "reversed_found": 0,
            "fixed": 0,
            "errors": 0,
            "details": []
        }
    
    logger.warning(f"Found {len(reversed_narratives)} narratives with reversed timestamps")
    
    stats = {
        "total_checked": len(reversed_narratives),
        "reversed_found": len(reversed_narratives),
        "fixed": 0,
        "errors": 0,
        "details": []
    }
    
    for narrative in reversed_narratives:
        try:
            narrative_id = narrative["_id"]
            theme = narrative.get("theme", "unknown")
            first_seen = narrative.get("first_seen")
            last_updated = narrative.get("last_updated")
            title = narrative.get("title", "unknown")
            
            # Calculate time difference
            if first_seen and last_updated:
                time_diff = (first_seen - last_updated).total_seconds() / 60  # in minutes
            else:
                time_diff = None
            
            logger.warning(
                f"Narrative '{theme}' (ID: {narrative_id}): "
                f"first_seen={first_seen}, last_updated={last_updated} "
                f"(diff: {time_diff:.1f} minutes)"
            )
            
            detail = {
                "id": str(narrative_id),
                "theme": theme,
                "title": title,
                "first_seen": first_seen.isoformat() if first_seen else None,
                "last_updated": last_updated.isoformat() if last_updated else None,
                "time_diff_minutes": time_diff
            }
            
            if not dry_run:
                # Swap the timestamps
                update_result = await collection.update_one(
                    {"_id": narrative_id},
                    {
                        "$set": {
                            "first_seen": last_updated,
                            "last_updated": first_seen
                        }
                    }
                )
                
                if update_result.modified_count > 0:
                    logger.info(f"✓ Fixed narrative '{theme}' (ID: {narrative_id})")
                    detail["status"] = "fixed"
                    stats["fixed"] += 1
                else:
                    logger.error(f"✗ Failed to update narrative '{theme}' (ID: {narrative_id})")
                    detail["status"] = "failed"
                    stats["errors"] += 1
            else:
                detail["status"] = "would_fix"
                logger.info(f"[DRY RUN] Would fix narrative '{theme}' (ID: {narrative_id})")
            
            stats["details"].append(detail)
            
        except Exception as e:
            logger.exception(f"Error processing narrative {narrative.get('_id')}: {e}")
            stats["errors"] += 1
            stats["details"].append({
                "id": str(narrative.get("_id", "unknown")),
                "status": "error",
                "error": str(e)
            })
    
    return stats


async def validate_fix() -> Dict[str, Any]:
    """
    Validate that all narratives now have first_seen <= last_updated.
    
    Returns:
        Validation results
    """
    db = await mongo_manager.get_async_database()
    collection = db.narratives
    
    # Check for any remaining reversed timestamps
    pipeline = [
        {
            "$addFields": {
                "isReversed": {
                    "$gt": ["$first_seen", "$last_updated"]
                }
            }
        },
        {
            "$match": {
                "isReversed": True
            }
        },
        {
            "$count": "count"
        }
    ]
    
    result = await collection.aggregate(pipeline).to_list(1)
    remaining_reversed = result[0]["count"] if result else 0
    
    # Get total narrative count
    total_narratives = await collection.count_documents({})
    
    return {
        "total_narratives": total_narratives,
        "remaining_reversed": remaining_reversed,
        "valid": remaining_reversed == 0
    }


async def main():
    """Main entry point."""
    dry_run = "--dry-run" in sys.argv
    
    logger.info("=" * 80)
    logger.info("Narrative Timestamp Reversal Fix Script")
    logger.info("=" * 80)
    
    if dry_run:
        logger.info("[DRY RUN MODE] No changes will be made")
    
    try:
        # Fix reversed timestamps
        logger.info("\nStep 1: Fixing reversed timestamps...")
        fix_stats = await fix_reversed_timestamps(dry_run=dry_run)
        
        logger.info(f"\nFix Results:")
        logger.info(f"  Total narratives checked: {fix_stats['total_checked']}")
        logger.info(f"  Reversed timestamps found: {fix_stats['reversed_found']}")
        logger.info(f"  Fixed: {fix_stats['fixed']}")
        logger.info(f"  Errors: {fix_stats['errors']}")
        
        if fix_stats["details"]:
            logger.info(f"\nDetailed Results:")
            for detail in fix_stats["details"]:
                logger.info(f"  - {detail['theme']}: {detail['status']}")
        
        # Validate the fix (skip in dry-run mode)
        if not dry_run:
            logger.info("\nStep 2: Validating fix...")
            validation = await validate_fix()
            
            logger.info(f"\nValidation Results:")
            logger.info(f"  Total narratives: {validation['total_narratives']}")
            logger.info(f"  Remaining reversed: {validation['remaining_reversed']}")
            logger.info(f"  Status: {'✓ VALID' if validation['valid'] else '✗ INVALID'}")
            
            if validation["valid"]:
                logger.info("\n✓ All narratives now have valid timestamp ordering!")
            else:
                logger.error(f"\n✗ {validation['remaining_reversed']} narratives still have reversed timestamps")
                return 1
        else:
            logger.info("\n[DRY RUN] Skipping validation")
        
        logger.info("\n" + "=" * 80)
        logger.info("Fix script completed successfully")
        logger.info("=" * 80)
        return 0
        
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
