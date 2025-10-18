#!/usr/bin/env python3
"""
One-time cleanup script to delete the irrelevant Benzinga advertising narrative.

Usage:
    python scripts/delete_benzinga_narrative.py              # Dry-run mode (shows what would be deleted)
    python scripts/delete_benzinga_narrative.py --confirm    # Actually delete the narrative
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from crypto_news_aggregator.db.mongodb import mongo_manager


async def find_benzinga_narrative():
    """Find the Benzinga narrative in the database."""
    db = await mongo_manager.get_async_database()
    narratives_collection = db.narratives
    
    # Query for Benzinga narrative
    query = {
        '$and': [
            {'title': {'$regex': 'Benzinga', '$options': 'i'}},
            {'fingerprint.nucleus_entity': 'Benzinga'}
        ]
    }
    
    narrative = await narratives_collection.find_one(query)
    return narrative


async def get_narrative_articles(article_ids):
    """Get article details for the narrative."""
    db = await mongo_manager.get_async_database()
    articles_collection = db.articles
    
    # Convert string IDs to ObjectId if needed
    from bson import ObjectId
    object_ids = []
    for aid in article_ids[:5]:  # Get first 5 for sample
        try:
            object_ids.append(ObjectId(aid))
        except:
            object_ids.append(aid)
    
    articles = await articles_collection.find(
        {'_id': {'$in': object_ids}}
    ).to_list(length=5)
    
    return articles


async def delete_narrative(narrative_id, update_articles=False):
    """Delete the narrative and optionally update articles."""
    db = await mongo_manager.get_async_database()
    narratives_collection = db.narratives
    
    # Delete the narrative
    result = await narratives_collection.delete_one({'_id': narrative_id})
    
    if update_articles:
        # Update articles to remove narrative association
        articles_collection = db.articles
        await articles_collection.update_many(
            {'narrative_id': str(narrative_id)},
            {'$unset': {'narrative_id': ''}}
        )
        print(f"✓ Updated articles to remove narrative association")
    
    return result.deleted_count


async def main():
    parser = argparse.ArgumentParser(
        description='Delete the Benzinga advertising narrative from the database'
    )
    parser.add_argument(
        '--confirm',
        action='store_true',
        help='Actually delete the narrative (default is dry-run mode)'
    )
    parser.add_argument(
        '--update-articles',
        action='store_true',
        help='Also update articles to remove narrative associations'
    )
    
    args = parser.parse_args()
    
    try:
        # Connect to database
        await mongo_manager.connect()
        
        # Find the Benzinga narrative
        print("🔍 Searching for Benzinga narrative...")
        narrative = await find_benzinga_narrative()
        
        if not narrative:
            print("❌ No Benzinga narrative found in database")
            return
        
        # Display narrative details
        print("\n" + "="*80)
        print("📊 NARRATIVE DETAILS")
        print("="*80)
        print(f"ID: {narrative['_id']}")
        print(f"Title: {narrative.get('title', 'N/A')}")
        print(f"Article Count: {narrative.get('article_count', 0)}")
        print(f"Nucleus Entity: {narrative.get('fingerprint', {}).get('nucleus_entity', 'N/A')}")
        print(f"Lifecycle State: {narrative.get('lifecycle_state', 'N/A')}")
        print(f"First Seen: {narrative.get('first_seen', 'N/A')}")
        print(f"Last Updated: {narrative.get('last_updated', 'N/A')}")
        
        # Get sample articles
        article_ids = narrative.get('article_ids', [])
        if article_ids:
            print(f"\n📰 Sample Articles (showing up to 5 of {len(article_ids)}):")
            articles = await get_narrative_articles(article_ids)
            for i, article in enumerate(articles, 1):
                print(f"  {i}. {article.get('title', 'N/A')}")
                print(f"     Source: {article.get('source', 'N/A')}")
                print(f"     Published: {article.get('published_at', 'N/A')}")
        
        print("="*80)
        
        if not args.confirm:
            print("\n⚠️  DRY-RUN MODE - No changes will be made")
            print("   Run with --confirm flag to actually delete the narrative")
            print(f"\n   Command: python scripts/delete_benzinga_narrative.py --confirm")
            if article_ids:
                print(f"   Note: {len(article_ids)} articles will remain but can be re-clustered in next detection run")
                print(f"   Add --update-articles to remove narrative associations from articles")
        else:
            print("\n⚠️  CONFIRM MODE - This will DELETE the narrative")
            response = input("   Type 'DELETE' to confirm: ")
            
            if response.strip() == 'DELETE':
                deleted_count = await delete_narrative(
                    narrative['_id'],
                    update_articles=args.update_articles
                )
                
                if deleted_count > 0:
                    print(f"\n✅ Successfully deleted Benzinga narrative (ID: {narrative['_id']})")
                    if not args.update_articles:
                        print(f"   {len(article_ids)} articles remain and will be re-clustered in next detection run")
                else:
                    print("\n❌ Failed to delete narrative")
            else:
                print("\n❌ Deletion cancelled - confirmation not received")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Close database connection
        await mongo_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
