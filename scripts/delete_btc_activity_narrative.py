#!/usr/bin/env python3
"""
Delete the low-quality "BTC Activity" narrative from the archive.

This script removes a generic dormant narrative that doesn't provide meaningful insights.
The articles will be available for re-clustering in the next narrative detection run.

Usage:
    # Dry run (shows what would be deleted)
    poetry run python scripts/delete_btc_activity_narrative.py

    # Actually delete the narrative
    poetry run python scripts/delete_btc_activity_narrative.py --confirm
"""

import asyncio
import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from crypto_news_aggregator.db.mongodb import mongo_manager
from bson import ObjectId


async def delete_btc_activity_narrative(confirm: bool = False, clean_articles: bool = True):
    """
    Delete the BTC Activity narrative from the archive.
    
    Args:
        confirm: If True, actually delete. If False, dry-run only.
        clean_articles: If True, remove narrative associations from articles.
    """
    
    print("=" * 80)
    print("DELETE BTC ACTIVITY NARRATIVE")
    print("=" * 80)
    print()
    
    if not confirm:
        print("🔍 DRY RUN MODE - No changes will be made")
        print("   Use --confirm flag to actually delete")
        print()
    
    try:
        # Get database connection
        db = await mongo_manager.get_async_database()
        narratives_collection = db.narratives
        articles_collection = db.articles
        
        # Query for the narrative
        # Note: The narrative doesn't have a 'title' field in the database
        # It has 'nucleus_entity': 'BTC' which the API transforms to 'BTC Activity'
        query = {
            'nucleus_entity': 'BTC',
            'lifecycle_state': 'dormant',
            'article_count': 2
        }
        
        print("Searching for narrative...")
        print(f"Query: {query}")
        print()
        
        narrative = await narratives_collection.find_one(query)
        
        if not narrative:
            print("❌ No matching narrative found")
            print()
            print("Searched for:")
            print("  - nucleus_entity = 'BTC'")
            print("  - lifecycle_state = 'dormant'")
            print("  - article_count = 2")
            print()
            return
        
        # Display narrative details
        print("✓ Found narrative to delete:")
        print("=" * 80)
        print()
        print(f"ID: {narrative['_id']}")
        print(f"Title: {narrative.get('title', 'N/A')}")
        print(f"Theme: {narrative.get('theme', 'N/A')}")
        print(f"Nucleus Entity: {narrative.get('nucleus_entity', 'N/A')}")
        print(f"Article Count: {narrative.get('article_count', 0)}")
        print(f"Lifecycle State: {narrative.get('lifecycle_state', 'N/A')}")
        print(f"First Seen: {narrative.get('first_seen', 'N/A')}")
        print(f"Last Updated: {narrative.get('last_updated', 'N/A')}")
        print()
        
        # Get article details
        article_ids = narrative.get('article_ids', [])
        
        if article_ids:
            print(f"Associated Articles ({len(article_ids)}):")
            print("-" * 80)
            
            # Convert to ObjectIds if needed
            object_ids = []
            for aid in article_ids:
                if isinstance(aid, str):
                    object_ids.append(ObjectId(aid))
                else:
                    object_ids.append(aid)
            
            # Fetch articles
            cursor = articles_collection.find({'_id': {'$in': object_ids}})
            articles = await cursor.to_list(length=None)
            
            for i, article in enumerate(articles, 1):
                title = article.get('title', 'N/A')
                url = article.get('url', 'N/A')
                published = article.get('published_at', 'N/A')
                source = article.get('source', 'N/A')
                
                print(f"\n{i}. {title}")
                print(f"   Source: {source}")
                print(f"   Published: {published}")
                print(f"   URL: {url[:80]}...")
            
            print()
        else:
            print("⚠ No articles associated with this narrative")
            print()
        
        # Summary
        print("=" * 80)
        print("DELETION SUMMARY")
        print("=" * 80)
        print()
        print("This will:")
        print(f"  1. Delete the narrative document (ID: {narrative['_id']})")
        
        if clean_articles and article_ids:
            print(f"  2. Remove narrative associations from {len(article_ids)} articles")
            print("     (Articles will remain in database but can be re-clustered)")
        else:
            print("  2. Leave articles unchanged (they will still reference this narrative)")
        
        print()
        
        if not confirm:
            print("=" * 80)
            print("🔍 DRY RUN - No changes made")
            print("=" * 80)
            print()
            print("To actually delete this narrative, run:")
            print("  poetry run python scripts/delete_btc_activity_narrative.py --confirm")
            print()
            return
        
        # Confirm deletion
        print("=" * 80)
        print("⚠️  CONFIRM DELETION")
        print("=" * 80)
        print()
        print("You are about to permanently delete this narrative.")
        print()
        response = input("Type 'DELETE' to confirm: ")
        
        if response != 'DELETE':
            print()
            print("❌ Deletion cancelled")
            print()
            return
        
        print()
        print("Deleting narrative...")
        
        # Delete the narrative
        result = await narratives_collection.delete_one({'_id': narrative['_id']})
        
        if result.deleted_count == 1:
            print(f"✓ Deleted narrative: {narrative['_id']}")
        else:
            print(f"❌ Failed to delete narrative")
            return
        
        # Clean up article associations
        if clean_articles and article_ids:
            print()
            print("Cleaning up article associations...")
            
            # Remove narrative_id field from articles
            # This allows them to be re-clustered in the next detection run
            update_result = await articles_collection.update_many(
                {'_id': {'$in': object_ids}},
                {'$unset': {'narrative_id': '', 'narrative_theme': ''}}
            )
            
            print(f"✓ Updated {update_result.modified_count} articles")
            print("  (Removed narrative associations so they can be re-clustered)")
        
        print()
        print("=" * 80)
        print("✅ DELETION COMPLETE")
        print("=" * 80)
        print()
        print("The narrative has been removed from the archive.")
        
        if clean_articles and article_ids:
            print("The articles are now available for re-clustering.")
        
        print()
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Delete the low-quality BTC Activity narrative from the archive',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run (default) - shows what would be deleted
  poetry run python scripts/delete_btc_activity_narrative.py

  # Actually delete the narrative
  poetry run python scripts/delete_btc_activity_narrative.py --confirm

  # Delete but keep article associations
  poetry run python scripts/delete_btc_activity_narrative.py --confirm --no-clean-articles
        """
    )
    
    parser.add_argument(
        '--confirm',
        action='store_true',
        help='Actually delete the narrative (default is dry-run)'
    )
    
    parser.add_argument(
        '--no-clean-articles',
        action='store_true',
        help='Do not remove narrative associations from articles'
    )
    
    args = parser.parse_args()
    
    await delete_btc_activity_narrative(
        confirm=args.confirm,
        clean_articles=not args.no_clean_articles
    )


if __name__ == "__main__":
    asyncio.run(main())
