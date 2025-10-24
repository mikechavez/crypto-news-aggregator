#!/usr/bin/env python3
"""
Fix narratives where first_seen is after the earliest article published_at.

This corrects narratives that were created with first_seen set to now()
instead of min(article_dates).

Usage:
    python scripts/fix_narrative_first_seen.py [--dry-run]

Options:
    --dry-run    Show what would be fixed without making changes
"""

import asyncio
import logging
import sys
from datetime import datetime, timezone
from typing import Dict, Any, List
from bson import ObjectId

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import after setting up logging
from crypto_news_aggregator.db.mongodb import mongo_manager


async def find_narratives_with_wrong_first_seen() -> List[Dict[str, Any]]:
    """
    Find narratives where first_seen is after the earliest article published_at.
    
    Returns:
        List of narrative documents that need fixing
    """
    db = await mongo_manager.get_async_database()
    narratives_collection = db.narratives
    articles_collection = db.articles
    
    # Get all narratives
    narratives = []
    cursor = narratives_collection.find({})
    async for narrative in cursor:
        narratives.append(narrative)
    
    logger.info(f"Checking {len(narratives)} narratives...")
    
    # For each narrative, check if first_seen is after earliest article
    narratives_to_fix = []
    
    for narrative in narratives:
        article_ids = narrative.get("article_ids", [])
        first_seen = narrative.get("first_seen")
        
        if not article_ids or not first_seen:
            continue
        
        # Convert article_ids to ObjectIds
        object_ids = []
        for aid in article_ids:
            try:
                if isinstance(aid, str):
                    object_ids.append(ObjectId(aid))
                else:
                    object_ids.append(aid)
            except Exception:
                continue
        
        if not object_ids:
            continue
        
        # Find the earliest article
        earliest_article = await articles_collection.find_one(
            {"_id": {"$in": object_ids}},
            sort=[("published_at", 1)]
        )
        
        if not earliest_article:
            continue
        
        earliest_published = earliest_article.get("published_at")
        if not earliest_published:
            continue
        
        # Ensure timezone-aware
        if first_seen.tzinfo is None:
            first_seen = first_seen.replace(tzinfo=timezone.utc)
        if earliest_published.tzinfo is None:
            earliest_published = earliest_published.replace(tzinfo=timezone.utc)
        
        # Check if first_seen is after earliest article
        if first_seen > earliest_published:
            narratives_to_fix.append({
                "narrative": narrative,
                "current_first_seen": first_seen,
                "earliest_article_published": earliest_published,
                "time_diff_minutes": (first_seen - earliest_published).total_seconds() / 60
            })
    
    return narratives_to_fix


async def fix_narrative_first_seen(dry_run: bool = False) -> Dict[str, Any]:
    """
    Fix narratives where first_seen is after earliest article.
    
    Args:
        dry_run: If True, only report what would be fixed without making changes
    
    Returns:
        Dictionary with fix statistics
    """
    db = await mongo_manager.get_async_database()
    narratives_collection = db.narratives
    
    # Find narratives to fix
    narratives_to_fix = await find_narratives_with_wrong_first_seen()
    
    if not narratives_to_fix:
        logger.info("✓ No narratives with wrong first_seen found")
        return {
            "total_checked": 0,
            "wrong_first_seen_found": 0,
            "fixed": 0,
            "errors": 0,
            "details": []
        }
    
    logger.warning(f"Found {len(narratives_to_fix)} narratives with wrong first_seen")
    
    stats = {
        "total_checked": len(narratives_to_fix),
        "wrong_first_seen_found": len(narratives_to_fix),
        "fixed": 0,
        "errors": 0,
        "details": []
    }
    
    for item in narratives_to_fix:
        try:
            narrative = item["narrative"]
            narrative_id = narrative["_id"]
            theme = narrative.get("theme", "unknown")
            current_first_seen = item["current_first_seen"]
            earliest_published = item["earliest_article_published"]
            time_diff = item["time_diff_minutes"]
            
            logger.warning(
                f"Narrative '{theme}' (ID: {narrative_id}): "
                f"first_seen={current_first_seen}, "
                f"earliest_article={earliest_published} "
                f"(diff: {time_diff:.1f} minutes)"
            )
            
            detail = {
                "id": str(narrative_id),
                "theme": theme,
                "title": narrative.get("title", "unknown"),
                "current_first_seen": current_first_seen.isoformat() if current_first_seen else None,
                "earliest_article_published": earliest_published.isoformat() if earliest_published else None,
                "time_diff_minutes": time_diff
            }
            
            if not dry_run:
                # Update the narrative with correct first_seen
                update_result = await narratives_collection.update_one(
                    {"_id": narrative_id},
                    {
                        "$set": {
                            "first_seen": earliest_published
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
    Validate that all narratives now have first_seen <= earliest article.
    
    Returns:
        Validation results
    """
    db = await mongo_manager.get_async_database()
    
    # Find narratives with wrong first_seen
    wrong_first_seen = await find_narratives_with_wrong_first_seen()
    
    return {
        "total_narratives": await db.narratives.count_documents({}),
        "still_wrong": len(wrong_first_seen),
        "valid": len(wrong_first_seen) == 0
    }


async def main():
    """Main entry point."""
    dry_run = "--dry-run" in sys.argv
    
    logger.info("=" * 80)
    logger.info("Narrative First Seen Fix Script")
    logger.info("=" * 80)
    
    if dry_run:
        logger.info("[DRY RUN MODE] No changes will be made")
    
    try:
        # Fix wrong first_seen
        logger.info("\nStep 1: Fixing narratives with wrong first_seen...")
        fix_stats = await fix_narrative_first_seen(dry_run=dry_run)
        
        logger.info(f"\nFix Results:")
        logger.info(f"  Total checked: {fix_stats['total_checked']}")
        logger.info(f"  Wrong first_seen found: {fix_stats['wrong_first_seen_found']}")
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
            logger.info(f"  Still wrong: {validation['still_wrong']}")
            logger.info(f"  Status: {'✓ VALID' if validation['valid'] else '✗ INVALID'}")
            
            if validation["valid"]:
                logger.info("\n✓ All narratives now have correct first_seen!")
            else:
                logger.error(f"\n✗ {validation['still_wrong']} narratives still have wrong first_seen")
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
