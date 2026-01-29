#!/usr/bin/env python3
"""
Delete all Benzinga articles from the database and clean up affected narratives.

This script:
1. Finds and deletes all Benzinga articles
2. Removes Benzinga article references from narratives
3. Deletes narratives that only contained Benzinga articles
4. Updates article counts for affected narratives
5. Generates a comprehensive summary report

Usage:
    # Dry run (preview changes without applying)
    python scripts/delete_benzinga_articles.py --dry-run

    # Execute deletion
    python scripts/delete_benzinga_articles.py --confirm
"""

import asyncio
import argparse
import logging
import sys
from datetime import datetime
from typing import Dict, List, Any, Set
from collections import defaultdict

# Add parent directory to path
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.crypto_news_aggregator.db.mongodb import mongo_manager, initialize_mongodb

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class BenzingaRemovalReport:
    """Track all changes made during Benzinga removal."""
    
    def __init__(self):
        self.articles_found = 0
        self.articles_deleted = 0
        self.article_date_range = {"earliest": None, "latest": None}
        self.narratives_checked = 0
        self.narratives_updated = 0
        self.narratives_deleted = 0
        self.entity_mentions_deleted = 0
        self.narrative_updates: List[Dict[str, Any]] = []
        self.errors: List[str] = []
    
    def print_summary(self, dry_run: bool = False):
        """Print a comprehensive summary of all changes."""
        mode = "DRY RUN" if dry_run else "EXECUTION"
        action = "Would be" if dry_run else "Were"
        
        print("\n" + "=" * 80)
        print(f"BENZINGA REMOVAL REPORT - {mode}")
        print("=" * 80)
        
        print(f"\n📰 ARTICLES:")
        print(f"  • Found: {self.articles_found} Benzinga articles")
        if self.article_date_range["earliest"] and self.article_date_range["latest"]:
            print(f"  • Date range: {self.article_date_range['earliest']} to {self.article_date_range['latest']}")
        print(f"  • {action} deleted: {self.articles_deleted}")
        
        print(f"\n📝 NARRATIVES:")
        print(f"  • Checked: {self.narratives_checked} narratives")
        print(f"  • {action} updated (article count reduced): {self.narratives_updated}")
        print(f"  • {action} deleted (only Benzinga articles): {self.narratives_deleted}")
        
        if self.narrative_updates:
            print(f"\n  Narrative Updates Detail:")
            for update in self.narrative_updates[:10]:  # Show first 10
                print(f"    - {update['title'][:60]}...")
                print(f"      Articles: {update['old_count']} → {update['new_count']}")
        
        print(f"\n🏷️  ENTITY MENTIONS:")
        print(f"  • {action} deleted: {self.entity_mentions_deleted}")
        
        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for error in self.errors[:5]:  # Show first 5 errors
                print(f"  • {error}")
        
        print("\n" + "=" * 80)
        
        if dry_run:
            print("\n⚠️  This was a DRY RUN - no changes were made to the database.")
            print("Run with --confirm to execute the deletion.")
        else:
            print("\n✅ Benzinga content removal completed successfully!")
        
        print("=" * 80 + "\n")


async def find_benzinga_articles(db) -> List[Dict[str, Any]]:
    """Find all Benzinga articles in the database."""
    logger.info("Searching for Benzinga articles...")
    
    articles_collection = db.articles
    
    # Case-insensitive search for Benzinga articles
    query = {"source": {"$regex": "^benzinga$", "$options": "i"}}
    
    articles = []
    async for article in articles_collection.find(query):
        articles.append(article)
    
    logger.info(f"Found {len(articles)} Benzinga articles")
    return articles


async def delete_benzinga_articles(db, article_ids: List[str], dry_run: bool = False) -> int:
    """Delete Benzinga articles from the database."""
    if not article_ids:
        return 0
    
    if dry_run:
        logger.info(f"[DRY RUN] Would delete {len(article_ids)} articles")
        return len(article_ids)
    
    articles_collection = db.articles
    
    # Convert string IDs to ObjectId if needed
    from bson import ObjectId
    object_ids = []
    for aid in article_ids:
        if isinstance(aid, str):
            object_ids.append(ObjectId(aid))
        else:
            object_ids.append(aid)
    
    result = await articles_collection.delete_many({"_id": {"$in": object_ids}})
    deleted_count = result.deleted_count
    
    logger.info(f"Deleted {deleted_count} Benzinga articles from database")
    return deleted_count


async def delete_entity_mentions(db, article_ids: List[str], dry_run: bool = False) -> int:
    """Delete entity mentions associated with Benzinga articles."""
    if not article_ids:
        return 0
    
    entity_mentions_collection = db.entity_mentions
    
    # Convert ObjectIds to strings for entity_mentions lookup
    article_id_strings = [str(aid) for aid in article_ids]
    
    if dry_run:
        count = await entity_mentions_collection.count_documents(
            {"article_id": {"$in": article_id_strings}}
        )
        logger.info(f"[DRY RUN] Would delete {count} entity mentions")
        return count
    
    result = await entity_mentions_collection.delete_many(
        {"article_id": {"$in": article_id_strings}}
    )
    deleted_count = result.deleted_count
    
    logger.info(f"Deleted {deleted_count} entity mentions for Benzinga articles")
    return deleted_count


async def cleanup_narratives(db, article_ids: List[str], report: BenzingaRemovalReport, dry_run: bool = False):
    """Clean up narratives affected by Benzinga article removal."""
    logger.info("Cleaning up narratives affected by Benzinga removal...")
    
    narratives_collection = db.narratives
    
    # Convert to string IDs for narrative lookup
    article_id_strings = [str(aid) for aid in article_ids]
    article_id_set = set(article_id_strings)
    
    # Find all narratives that contain any Benzinga articles
    query = {"article_ids": {"$in": article_id_strings}}
    
    narratives_to_update = []
    narratives_to_delete = []
    
    async for narrative in narratives_collection.find(query):
        report.narratives_checked += 1
        
        narrative_id = narrative["_id"]
        old_article_ids = narrative.get("article_ids", [])
        old_count = len(old_article_ids)
        
        # Remove Benzinga article IDs
        new_article_ids = [aid for aid in old_article_ids if aid not in article_id_set]
        new_count = len(new_article_ids)
        
        if new_count == 0:
            # Narrative only had Benzinga articles - delete it
            narratives_to_delete.append(narrative_id)
            report.narratives_deleted += 1
            logger.info(f"Narrative '{narrative.get('title', 'Unknown')}' will be deleted (only Benzinga articles)")
        elif new_count < old_count:
            # Narrative had some Benzinga articles - update it
            narratives_to_update.append({
                "id": narrative_id,
                "article_ids": new_article_ids,
                "article_count": new_count
            })
            report.narratives_updated += 1
            report.narrative_updates.append({
                "title": narrative.get("title", "Unknown"),
                "old_count": old_count,
                "new_count": new_count
            })
    
    # Execute updates
    if not dry_run:
        # Update narratives with reduced article counts
        for update in narratives_to_update:
            await narratives_collection.update_one(
                {"_id": update["id"]},
                {
                    "$set": {
                        "article_ids": update["article_ids"],
                        "article_count": update["article_count"],
                        "updated_at": datetime.utcnow()
                    }
                }
            )
        
        # Delete narratives that only had Benzinga articles
        if narratives_to_delete:
            await narratives_collection.delete_many(
                {"_id": {"$in": narratives_to_delete}}
            )
    
    logger.info(f"Narratives: {report.narratives_updated} updated, {report.narratives_deleted} deleted")


async def run_benzinga_removal(dry_run: bool = False, confirm: bool = False):
    """Execute the complete Benzinga removal process."""
    
    if not dry_run and not confirm:
        logger.error("Must specify either --dry-run or --confirm")
        print("\n❌ Error: You must specify either --dry-run (to preview) or --confirm (to execute)")
        print("   Run with --dry-run first to see what would be deleted.\n")
        return False
    
    report = BenzingaRemovalReport()
    
    try:
        # Initialize MongoDB
        logger.info("Initializing MongoDB connection...")
        await initialize_mongodb()
        db = await mongo_manager.get_async_database()
        
        # Step 1: Find all Benzinga articles
        articles = await find_benzinga_articles(db)
        report.articles_found = len(articles)
        
        if not articles:
            logger.info("No Benzinga articles found in database")
            report.print_summary(dry_run)
            return True
        
        # Extract article IDs and date range
        article_ids = [article["_id"] for article in articles]
        
        # Calculate date range
        dates = [article.get("published_at") for article in articles if article.get("published_at")]
        if dates:
            report.article_date_range["earliest"] = min(dates).strftime("%Y-%m-%d")
            report.article_date_range["latest"] = max(dates).strftime("%Y-%m-%d")
        
        logger.info(f"Found {len(article_ids)} Benzinga articles to remove")
        logger.info(f"Date range: {report.article_date_range['earliest']} to {report.article_date_range['latest']}")
        
        # Step 2: Clean up narratives BEFORE deleting articles
        await cleanup_narratives(db, article_ids, report, dry_run)
        
        # Step 3: Delete entity mentions
        report.entity_mentions_deleted = await delete_entity_mentions(db, article_ids, dry_run)
        
        # Step 4: Delete articles
        report.articles_deleted = await delete_benzinga_articles(db, article_ids, dry_run)
        
        # Print summary
        report.print_summary(dry_run)
        
        return True
        
    except Exception as e:
        logger.exception(f"Error during Benzinga removal: {e}")
        report.errors.append(str(e))
        report.print_summary(dry_run)
        return False
    finally:
        await mongo_manager.aclose()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Delete all Benzinga articles and clean up affected narratives",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview what would be deleted (safe, no changes)
  python scripts/delete_benzinga_articles.py --dry-run
  
  # Execute the deletion
  python scripts/delete_benzinga_articles.py --confirm
        """
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without executing them"
    )
    group.add_argument(
        "--confirm",
        action="store_true",
        help="Execute the deletion (use with caution!)"
    )
    
    args = parser.parse_args()
    
    # Run the removal process
    success = asyncio.run(run_benzinga_removal(
        dry_run=args.dry_run,
        confirm=args.confirm
    ))
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
