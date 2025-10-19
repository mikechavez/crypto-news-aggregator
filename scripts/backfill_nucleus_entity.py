#!/usr/bin/env python3
"""
Backfill nucleus_entity field for existing narratives.

This script extracts nucleus_entity from the fingerprint subdocument
and sets it as a top-level field on each narrative document.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.crypto_news_aggregator.db.mongodb import mongo_manager

# Load environment variables
load_dotenv()


async def backfill_nucleus_entity():
    """Backfill nucleus_entity field for all narratives."""
    
    print("=" * 80)
    print("🔧 BACKFILLING NUCLEUS_ENTITY FIELD")
    print("=" * 80)
    
    try:
        await mongo_manager.initialize()
        db = await mongo_manager.get_async_database()
        narratives_collection = db.narratives
        
        # Count narratives before migration
        total_narratives = await narratives_collection.count_documents({})
        missing_field = await narratives_collection.count_documents({
            '$or': [
                {'nucleus_entity': {'$exists': False}},
                {'nucleus_entity': ''},
                {'nucleus_entity': None}
            ]
        })
        
        print(f"\n📊 PRE-MIGRATION STATUS:")
        print(f"  Total narratives: {total_narratives}")
        print(f"  Missing/empty nucleus_entity: {missing_field}")
        
        if missing_field == 0:
            print("\n✅ All narratives already have nucleus_entity field!")
            return
        
        # Fetch all narratives that need backfilling
        cursor = narratives_collection.find({
            '$or': [
                {'nucleus_entity': {'$exists': False}},
                {'nucleus_entity': ''},
                {'nucleus_entity': None}
            ]
        })
        narratives = await cursor.to_list(length=None)
        
        print(f"\n🔄 PROCESSING {len(narratives)} NARRATIVES...")
        
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        for i, narrative in enumerate(narratives, 1):
            narrative_id = narrative['_id']
            title = narrative.get('title', 'N/A')[:50]
            
            # Extract nucleus_entity from fingerprint
            fingerprint = narrative.get('fingerprint', {})
            nucleus_entity = fingerprint.get('nucleus_entity', '')
            
            if not nucleus_entity:
                print(f"  [{i}/{len(narratives)}] SKIP: No nucleus_entity in fingerprint for '{title}'")
                skipped_count += 1
                continue
            
            try:
                # Update the narrative with nucleus_entity field
                result = await narratives_collection.update_one(
                    {'_id': narrative_id},
                    {'$set': {'nucleus_entity': nucleus_entity}}
                )
                
                if result.modified_count > 0:
                    updated_count += 1
                    if updated_count % 10 == 0:
                        print(f"  [{i}/{len(narratives)}] Updated {updated_count} narratives...")
                else:
                    skipped_count += 1
                    
            except Exception as e:
                error_count += 1
                print(f"  [{i}/{len(narratives)}] ERROR updating '{title}': {e}")
        
        print(f"\n✅ MIGRATION COMPLETE!")
        print(f"  Updated: {updated_count}")
        print(f"  Skipped: {skipped_count}")
        print(f"  Errors: {error_count}")
        
        # Verify post-migration
        print(f"\n📊 POST-MIGRATION STATUS:")
        total_after = await narratives_collection.count_documents({})
        missing_after = await narratives_collection.count_documents({
            '$or': [
                {'nucleus_entity': {'$exists': False}},
                {'nucleus_entity': ''},
                {'nucleus_entity': None}
            ]
        })
        actual_after = await narratives_collection.count_documents({
            'nucleus_entity': {'$ne': '', '$ne': None, '$exists': True}
        })
        
        print(f"  Total narratives: {total_after}")
        print(f"  Missing/empty nucleus_entity: {missing_after}")
        print(f"  With actual nucleus_entity: {actual_after}")
        
        # Show sample of updated narratives
        print(f"\n📋 SAMPLE UPDATED NARRATIVES:")
        sample = await narratives_collection.find({
            'nucleus_entity': {'$ne': '', '$ne': None, '$exists': True}
        }).limit(5).to_list(length=5)
        
        for i, narrative in enumerate(sample, 1):
            print(f"  {i}. {narrative.get('title', 'N/A')[:60]}")
            print(f"     nucleus_entity: {narrative.get('nucleus_entity', 'N/A')}")
        
        if missing_after == 0:
            print(f"\n🎉 SUCCESS! All narratives now have nucleus_entity field!")
        else:
            print(f"\n⚠️  WARNING: {missing_after} narratives still missing nucleus_entity")
            print(f"     These may need manual review.")
        
    except Exception as e:
        print(f"\n❌ Error during migration: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await mongo_manager.close()


if __name__ == '__main__':
    asyncio.run(backfill_nucleus_entity())
