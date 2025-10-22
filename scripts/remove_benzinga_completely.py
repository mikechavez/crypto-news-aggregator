#!/usr/bin/env python3
"""
Complete removal of Benzinga content from the system.

This script:
1. Deletes all Benzinga articles from the database
2. Cleans up narratives affected by Benzinga article removal
3. Provides summary of changes

Note: RSS feed removal and source blacklist must be done manually in code.

Usage:
    python scripts/remove_benzinga_completely.py              # Dry-run mode
    python scripts/remove_benzinga_completely.py --confirm    # Execute deletion
"""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from crypto_news_aggregator.db.mongodb import mongo_manager
from bson import ObjectId


class RemovalStats:
    """Track removal statistics."""
    
    def __init__(self):
        self.benzinga_articles_count = 0
        self.benzinga_article_ids = []
        self.narratives_to_delete = []
        self.narratives_to_update = []
        self.total_narratives_deleted = 0
        self.total_narratives_updated = 0


async def find_benzinga_articles() -> List[Dict[str, Any]]:
    """Find all Benzinga articles in the database."""
    db = await mongo_manager.get_async_database()
    articles_collection = db.articles
    
    # Case-insensitive search for Benzinga source
    query = {'source': {'$regex': '^benzinga$', '$options': 'i'}}
    
    articles = await articles_collection.find(query).to_list(length=None)
    return articles


async def find_affected_narratives(article_ids: List[ObjectId]) -> tuple[List[Dict], List[Dict]]:
    """
    Find narratives affected by Benzinga article removal.
    
    Returns:
        Tuple of (narratives_to_delete, narratives_to_update)
        - narratives_to_delete: Narratives with ONLY Benzinga articles
        - narratives_to_update: Narratives with SOME Benzinga articles
    """
    db = await mongo_manager.get_async_database()
    narratives_collection = db.narratives
    
    # Find all narratives that contain any of these article IDs
    affected_narratives = await narratives_collection.find(
        {'article_ids': {'$in': article_ids}}
    ).to_list(length=None)
    
    narratives_to_delete = []
    narratives_to_update = []
    
    for narrative in affected_narratives:
        narrative_article_ids = set(narrative.get('article_ids', []))
        benzinga_article_ids = set(article_ids)
        
        # Check if ALL articles in this narrative are from Benzinga
        if narrative_article_ids.issubset(benzinga_article_ids):
            narratives_to_delete.append(narrative)
        else:
            # Some articles are from other sources
            narratives_to_update.append(narrative)
    
    return narratives_to_delete, narratives_to_update


async def delete_benzinga_articles(article_ids: List[ObjectId], dry_run: bool = True) -> int:
    """Delete Benzinga articles from the database."""
    if dry_run:
        return len(article_ids)
    
    db = await mongo_manager.get_async_database()
    articles_collection = db.articles
    
    result = await articles_collection.delete_many({'_id': {'$in': article_ids}})
    return result.deleted_count


async def delete_narratives(narrative_ids: List[ObjectId], dry_run: bool = True) -> int:
    """Delete narratives that only contain Benzinga articles."""
    if dry_run:
        return len(narrative_ids)
    
    db = await mongo_manager.get_async_database()
    narratives_collection = db.narratives
    
    result = await narratives_collection.delete_many({'_id': {'$in': narrative_ids}})
    return result.deleted_count


async def update_narratives(narratives: List[Dict], benzinga_article_ids: List[ObjectId], dry_run: bool = True) -> int:
    """Update narratives to remove Benzinga article references and update counts."""
    if dry_run:
        return len(narratives)
    
    db = await mongo_manager.get_async_database()
    narratives_collection = db.narratives
    
    updated_count = 0
    benzinga_ids_set = set(benzinga_article_ids)
    
    for narrative in narratives:
        narrative_id = narrative['_id']
        current_article_ids = narrative.get('article_ids', [])
        
        # Remove Benzinga article IDs
        updated_article_ids = [aid for aid in current_article_ids if aid not in benzinga_ids_set]
        new_article_count = len(updated_article_ids)
        
        # Update the narrative
        result = await narratives_collection.update_one(
            {'_id': narrative_id},
            {
                '$set': {
                    'article_ids': updated_article_ids,
                    'article_count': new_article_count,
                    'last_updated': datetime.utcnow()
                }
            }
        )
        
        if result.modified_count > 0:
            updated_count += 1
    
    return updated_count


def print_summary(stats: RemovalStats, dry_run: bool = True):
    """Print summary of what will be or was removed."""
    mode = "DRY-RUN" if dry_run else "EXECUTED"
    
    print("\n" + "="*80)
    print(f"BENZINGA REMOVAL SUMMARY - {mode}")
    print("="*80)
    
    print(f"\n📰 ARTICLES:")
    print(f"   Benzinga articles found: {stats.benzinga_articles_count}")
    if dry_run:
        print(f"   Will be deleted: {stats.benzinga_articles_count}")
    else:
        print(f"   Deleted: {stats.benzinga_articles_count}")
    
    print(f"\n📖 NARRATIVES:")
    print(f"   Narratives with ONLY Benzinga articles: {len(stats.narratives_to_delete)}")
    print(f"   Narratives with SOME Benzinga articles: {len(stats.narratives_to_update)}")
    
    if dry_run:
        print(f"   Will delete: {len(stats.narratives_to_delete)} narratives")
        print(f"   Will update: {len(stats.narratives_to_update)} narratives")
    else:
        print(f"   Deleted: {stats.total_narratives_deleted} narratives")
        print(f"   Updated: {stats.total_narratives_updated} narratives")
    
    if stats.narratives_to_delete:
        print(f"\n🗑️  NARRATIVES TO DELETE (only Benzinga content):")
        for narrative in stats.narratives_to_delete[:10]:  # Show first 10
            title = narrative.get('title', 'Untitled')[:60]
            article_count = narrative.get('article_count', 0)
            print(f"   - {title}... ({article_count} articles)")
        if len(stats.narratives_to_delete) > 10:
            print(f"   ... and {len(stats.narratives_to_delete) - 10} more")
    
    if stats.narratives_to_update:
        print(f"\n🔄 NARRATIVES TO UPDATE (remove Benzinga articles):")
        for narrative in stats.narratives_to_update[:10]:  # Show first 10
            title = narrative.get('title', 'Untitled')[:60]
            article_count = narrative.get('article_count', 0)
            benzinga_count = sum(1 for aid in narrative.get('article_ids', []) 
                               if aid in stats.benzinga_article_ids)
            print(f"   - {title}... ({article_count} total, {benzinga_count} Benzinga)")
        if len(stats.narratives_to_update) > 10:
            print(f"   ... and {len(stats.narratives_to_update) - 10} more")
    
    print("\n" + "="*80)
    
    if dry_run:
        print("\n⚠️  DRY-RUN MODE - No changes were made")
        print("   Run with --confirm to execute the removal")
    else:
        print("\n✅ REMOVAL COMPLETE")
        print(f"   Deleted {stats.benzinga_articles_count} Benzinga articles")
        print(f"   Deleted {stats.total_narratives_deleted} narratives")
        print(f"   Updated {stats.total_narratives_updated} narratives")


def print_manual_steps():
    """Print manual steps needed to complete Benzinga removal."""
    print("\n" + "="*80)
    print("MANUAL STEPS REQUIRED")
    print("="*80)
    
    print("\n1️⃣  Remove Benzinga from RSS feeds:")
    print("   File: src/crypto_news_aggregator/services/rss_service.py")
    print("   Action: Comment out or remove line 29:")
    print('   "benzinga": "https://www.benzinga.com/feed",')
    print('   Add comment: # Benzinga excluded - advertising content')
    
    print("\n2️⃣  Add source blacklist to RSS fetcher:")
    print("   File: src/crypto_news_aggregator/background/rss_fetcher.py")
    print("   Action: Add after imports (around line 18):")
    print("   BLACKLIST_SOURCES = ['benzinga']")
    print("\n   Then in fetch_and_process_rss_feeds() function:")
    print("   Filter articles before processing:")
    print("   articles = [a for a in articles if a.source.lower() not in BLACKLIST_SOURCES]")
    
    print("\n3️⃣  Note: 'Benzinga' is already blacklisted in narrative_service.py")
    print("   File: src/crypto_news_aggregator/services/narrative_service.py")
    print("   Line 54: BLACKLIST_ENTITIES = {'Benzinga', 'Sarah Edwards'}")
    
    print("\n" + "="*80)


async def main():
    parser = argparse.ArgumentParser(
        description='Completely remove Benzinga content from the system'
    )
    parser.add_argument(
        '--confirm',
        action='store_true',
        help='Actually execute the removal (default is dry-run mode)'
    )
    
    args = parser.parse_args()
    stats = RemovalStats()
    
    try:
        # Initialize database connection
        await mongo_manager.initialize()
        
        print("🔍 Step 1: Finding Benzinga articles...")
        benzinga_articles = await find_benzinga_articles()
        stats.benzinga_articles_count = len(benzinga_articles)
        stats.benzinga_article_ids = [article['_id'] for article in benzinga_articles]
        
        if stats.benzinga_articles_count == 0:
            print("✅ No Benzinga articles found in database")
            print_manual_steps()
            return
        
        print(f"   Found {stats.benzinga_articles_count} Benzinga articles")
        
        print("\n🔍 Step 2: Finding affected narratives...")
        narratives_to_delete, narratives_to_update = await find_affected_narratives(
            stats.benzinga_article_ids
        )
        stats.narratives_to_delete = narratives_to_delete
        stats.narratives_to_update = narratives_to_update
        
        print(f"   Found {len(narratives_to_delete)} narratives to delete")
        print(f"   Found {len(narratives_to_update)} narratives to update")
        
        # Print summary
        print_summary(stats, dry_run=not args.confirm)
        
        if not args.confirm:
            print("\n💡 To execute this removal, run:")
            print("   poetry run python scripts/remove_benzinga_completely.py --confirm")
            print_manual_steps()
            return
        
        # Confirm with user
        print("\n⚠️  WARNING: This will permanently delete data!")
        response = input("   Type 'DELETE BENZINGA' to confirm: ")
        
        if response.strip() != 'DELETE BENZINGA':
            print("\n❌ Removal cancelled - confirmation not received")
            return
        
        # Execute removal
        print("\n🗑️  Step 3: Deleting Benzinga articles...")
        deleted_articles = await delete_benzinga_articles(stats.benzinga_article_ids, dry_run=False)
        print(f"   Deleted {deleted_articles} articles")
        
        print("\n🗑️  Step 4: Deleting narratives with only Benzinga content...")
        narrative_ids_to_delete = [n['_id'] for n in narratives_to_delete]
        deleted_narratives = await delete_narratives(narrative_ids_to_delete, dry_run=False)
        stats.total_narratives_deleted = deleted_narratives
        print(f"   Deleted {deleted_narratives} narratives")
        
        print("\n🔄 Step 5: Updating narratives with mixed content...")
        updated_narratives = await update_narratives(
            narratives_to_update, 
            stats.benzinga_article_ids, 
            dry_run=False
        )
        stats.total_narratives_updated = updated_narratives
        print(f"   Updated {updated_narratives} narratives")
        
        # Print final summary
        print_summary(stats, dry_run=False)
        print_manual_steps()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Close database connection
        await mongo_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
