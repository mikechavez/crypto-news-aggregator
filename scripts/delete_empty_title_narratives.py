#!/usr/bin/env python3
"""
One-time cleanup script to delete narratives with empty titles.

These are failed narrative creations from Oct 17 that never got proper titles.
Only deletes narratives with empty/null titles AND article_count = 1.

Usage:
    python scripts/delete_empty_title_narratives.py              # Dry-run mode (shows what would be deleted)
    python scripts/delete_empty_title_narratives.py --confirm    # Actually delete the narratives
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from crypto_news_aggregator.db.mongodb import mongo_manager


async def find_empty_title_narratives():
    """Find narratives with empty or null titles and article_count = 1."""
    db = await mongo_manager.get_async_database()
    narratives_collection = db.narratives
    
    # Query for narratives with empty/null titles and article_count = 1
    query = {
        '$or': [
            {'title': ''},
            {'title': None},
            {'title': {'$exists': False}}
        ],
        'article_count': 1
    }
    
    narratives = await narratives_collection.find(query).to_list(length=None)
    return narratives


async def delete_narratives(narrative_ids):
    """Delete the specified narratives."""
    db = await mongo_manager.get_async_database()
    narratives_collection = db.narratives
    
    # Delete the narratives
    result = await narratives_collection.delete_many({'_id': {'$in': narrative_ids}})
    
    return result.deleted_count


async def main():
    parser = argparse.ArgumentParser(
        description='Delete narratives with empty titles from the database'
    )
    parser.add_argument(
        '--confirm',
        action='store_true',
        help='Actually delete the narratives (default is dry-run mode)'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize database connection
        await mongo_manager.initialize()
        
        # Find narratives with empty titles
        print("🔍 Searching for narratives with empty titles and article_count = 1...")
        narratives = await find_empty_title_narratives()
        
        if not narratives:
            print("✅ No narratives with empty titles found in database")
            return
        
        # Display narrative details
        print("\n" + "="*80)
        print(f"📊 FOUND {len(narratives)} NARRATIVES WITH EMPTY TITLES")
        print("="*80)
        
        for i, narrative in enumerate(narratives, 1):
            print(f"\n{i}. Narrative ID: {narrative['_id']}")
            print(f"   Title: '{narrative.get('title', 'N/A')}'")
            print(f"   Article Count: {narrative.get('article_count', 0)}")
            
            # Show nucleus entity if available
            fingerprint = narrative.get('fingerprint', {})
            nucleus_entity = fingerprint.get('nucleus_entity', 'N/A')
            nucleus_type = fingerprint.get('nucleus_type', 'N/A')
            print(f"   Nucleus Entity: {nucleus_entity} ({nucleus_type})")
            
            # Show lifecycle state
            lifecycle_state = narrative.get('lifecycle_state', 'N/A')
            print(f"   Lifecycle State: {lifecycle_state}")
            
            # Show timestamps
            first_seen = narrative.get('first_seen', 'N/A')
            last_updated = narrative.get('last_updated', 'N/A')
            print(f"   First Seen: {first_seen}")
            print(f"   Last Updated: {last_updated}")
            
            # Show article IDs
            article_ids = narrative.get('article_ids', [])
            if article_ids:
                print(f"   Article IDs: {article_ids}")
        
        print("="*80)
        
        if not args.confirm:
            print("\n⚠️  DRY-RUN MODE - No changes will be made")
            print("   Run with --confirm flag to actually delete these narratives")
            print(f"\n   Command: python scripts/delete_empty_title_narratives.py --confirm")
            print(f"\n   This will delete {len(narratives)} narratives with empty titles")
        else:
            print(f"\n⚠️  CONFIRM MODE - This will DELETE {len(narratives)} narratives")
            response = input("   Type 'DELETE' to confirm: ")
            
            if response.strip() == 'DELETE':
                narrative_ids = [n['_id'] for n in narratives]
                deleted_count = await delete_narratives(narrative_ids)
                
                if deleted_count > 0:
                    print(f"\n✅ Successfully deleted {deleted_count} narratives with empty titles")
                    print(f"   IDs deleted: {[str(nid) for nid in narrative_ids]}")
                else:
                    print("\n❌ Failed to delete narratives")
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
