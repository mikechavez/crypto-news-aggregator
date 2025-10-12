#!/usr/bin/env python3
"""
Clean narratives from MongoDB.

This script deletes all narratives from the MongoDB narratives collection,
allowing the system to regenerate them with corrected code.

PROBLEM:
The narrative discovery system created 30+ narratives that are still in the 
MongoDB database. Rolling back the code didn't delete them.

SOLUTION:
This script cleans the narratives collection and lets the system regenerate 
with the corrected code.

Usage:
    # Dry run (show what would be deleted)
    poetry run python scripts/clean_narratives.py --dry-run
    
    # Delete all narratives
    poetry run python scripts/clean_narratives.py --yes
    
    # Delete narratives older than N days
    poetry run python scripts/clean_narratives.py --days 7 --yes
"""

import asyncio
import argparse
import sys
import os
from datetime import datetime, timezone, timedelta
from typing import Optional

# Add src to path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, os.path.join(project_root, "src"))

from crypto_news_aggregator.db.mongodb import mongo_manager
from crypto_news_aggregator.core.config import settings


async def count_narratives(days: Optional[int] = None) -> int:
    """
    Count narratives in the database.
    
    Args:
        days: If provided, only count narratives older than this many days
        
    Returns:
        Number of narratives
    """
    db = await mongo_manager.get_async_database()
    collection = db.narratives
    
    if days is not None:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        query = {"last_updated": {"$lt": cutoff_date}}
    else:
        query = {}
    
    count = await collection.count_documents(query)
    return count


async def list_narratives(days: Optional[int] = None, limit: int = 10):
    """
    List narratives in the database.
    
    Args:
        days: If provided, only list narratives older than this many days
        limit: Maximum number of narratives to display
    """
    db = await mongo_manager.get_async_database()
    collection = db.narratives
    
    if days is not None:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        query = {"last_updated": {"$lt": cutoff_date}}
    else:
        query = {}
    
    cursor = collection.find(query).sort("last_updated", -1).limit(limit)
    
    narratives = []
    async for narrative in cursor:
        narratives.append(narrative)
    
    return narratives


async def delete_narratives(days: Optional[int] = None, dry_run: bool = True) -> int:
    """
    Delete narratives from the database.
    
    Args:
        days: If provided, only delete narratives older than this many days
        dry_run: If True, don't actually delete (default True)
        
    Returns:
        Number of narratives deleted (or would be deleted in dry run)
    """
    db = await mongo_manager.get_async_database()
    collection = db.narratives
    
    if days is not None:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        query = {"last_updated": {"$lt": cutoff_date}}
    else:
        query = {}
    
    if dry_run:
        # Just count what would be deleted
        count = await collection.count_documents(query)
        return count
    else:
        # Actually delete
        result = await collection.delete_many(query)
        return result.deleted_count


async def main():
    """Main script execution."""
    parser = argparse.ArgumentParser(
        description="Clean narratives from MongoDB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run (show what would be deleted)
  poetry run python scripts/clean_narratives.py --dry-run
  
  # Delete all narratives
  poetry run python scripts/clean_narratives.py --yes
  
  # Delete narratives older than 7 days
  poetry run python scripts/clean_narratives.py --days 7 --yes
  
  # List narratives before deleting
  poetry run python scripts/clean_narratives.py --list --dry-run
        """
    )
    
    parser.add_argument(
        "--days",
        type=int,
        help="Only delete narratives older than this many days (default: delete all)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting"
    )
    
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirm deletion (required to actually delete)"
    )
    
    parser.add_argument(
        "--list",
        action="store_true",
        help="List narratives before deleting"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.dry_run and not args.yes:
        print("❌ Error: Must specify either --dry-run or --yes")
        print("Use --dry-run to see what would be deleted")
        print("Use --yes to confirm deletion")
        sys.exit(1)
    
    # Initialize MongoDB connection
    print("🔌 Connecting to MongoDB...")
    await mongo_manager.initialize()
    
    try:
        # Count narratives
        total_count = await count_narratives()
        target_count = await count_narratives(days=args.days)
        
        print(f"\n📊 Database Status:")
        print(f"   Total narratives: {total_count}")
        
        if args.days:
            print(f"   Narratives older than {args.days} days: {target_count}")
        else:
            print(f"   Target narratives: {target_count} (all)")
        
        # List narratives if requested
        if args.list and target_count > 0:
            print(f"\n📋 Sample Narratives (showing up to 10):")
            narratives = await list_narratives(days=args.days, limit=10)
            
            for i, narrative in enumerate(narratives, 1):
                theme = narrative.get("theme", "N/A")
                title = narrative.get("title", "N/A")
                lifecycle = narrative.get("lifecycle", "N/A")
                article_count = narrative.get("article_count", 0)
                last_updated = narrative.get("last_updated", "N/A")
                
                print(f"\n   {i}. Theme: {theme}")
                print(f"      Title: {title}")
                print(f"      Lifecycle: {lifecycle}")
                print(f"      Articles: {article_count}")
                print(f"      Last Updated: {last_updated}")
        
        # Perform deletion
        if target_count == 0:
            print("\n✅ No narratives to delete")
        else:
            if args.dry_run:
                print(f"\n🔍 DRY RUN: Would delete {target_count} narratives")
                print("   (Run with --yes to actually delete)")
            else:
                print(f"\n⚠️  WARNING: About to delete {target_count} narratives")
                print("   This action cannot be undone!")
                
                # Extra confirmation for deleting all
                if not args.days:
                    confirm = input("\n   Type 'DELETE ALL' to confirm: ")
                    if confirm != "DELETE ALL":
                        print("❌ Deletion cancelled")
                        return
                
                print("\n🗑️  Deleting narratives...")
                deleted_count = await delete_narratives(days=args.days, dry_run=False)
                
                print(f"✅ Successfully deleted {deleted_count} narratives")
                
                # Verify deletion
                remaining = await count_narratives()
                print(f"   Remaining narratives: {remaining}")
    
    finally:
        # Close MongoDB connection
        print("\n🔌 Closing MongoDB connection...")
        await mongo_manager.close()
    
    print("\n✅ Done!")


if __name__ == "__main__":
    asyncio.run(main())
