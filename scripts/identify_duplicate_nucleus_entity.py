#!/usr/bin/env python3
"""
Identify the actual nucleus_entity value that appears in 229 narratives.

This script investigates what the duplicate nucleus_entity value is and
provides detailed analysis of why these narratives weren't merged.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.crypto_news_aggregator.db.mongodb import mongo_manager


def identify_duplicate_nucleus_entity():
    """Identify and analyze the duplicate nucleus_entity value."""
    
    print("=" * 80)
    print("DUPLICATE NUCLEUS ENTITY INVESTIGATION")
    print("=" * 80)
    print()
    
    narratives_col = mongo_manager.get_collection('narratives')
    
    # Find the nucleus_entity with the most duplicates
    pipeline = [
        {'$group': {
            '_id': '$narrative_fingerprint.nucleus_entity',
            'count': {'$sum': 1}
        }},
        {'$match': {'count': {'$gt': 1}}},
        {'$sort': {'count': -1}},
        {'$limit': 1}
    ]
    
    result = list(narratives_col.aggregate(pipeline))
    
    if not result:
        print("No duplicate nucleus_entity found.")
        return
    
    nucleus_entity = result[0]['_id']
    count = result[0]['count']
    
    print(f"Duplicate Nucleus Entity Value: '{nucleus_entity}'")
    print(f"Type: {type(nucleus_entity)}")
    print(f"Length: {len(str(nucleus_entity)) if nucleus_entity else 0}")
    print(f"Is None: {nucleus_entity is None}")
    print(f"Is Empty String: {nucleus_entity == ''}")
    print(f"Count: {count} narratives")
    print()
    
    # Fetch a few sample narratives
    print("=" * 80)
    print("SAMPLE NARRATIVES")
    print("=" * 80)
    print()
    
    samples = list(narratives_col.find({
        'narrative_fingerprint.nucleus_entity': nucleus_entity
    }).limit(5))
    
    for i, narrative in enumerate(samples, 1):
        print(f"Sample {i}:")
        print(f"  ID: {narrative['_id']}")
        print(f"  Title: {narrative.get('title', 'N/A')}")
        print(f"  Article Count: {len(narrative.get('article_ids', []))}")
        
        fingerprint = narrative.get('narrative_fingerprint', {})
        print(f"  Nucleus Entity: '{fingerprint.get('nucleus_entity')}'")
        print(f"  Theme Keywords: {fingerprint.get('theme_keywords', [])}")
        print(f"  Supporting Entities: {fingerprint.get('supporting_entities', [])}")
        
        # Check if fingerprint has any meaningful data
        has_themes = bool(fingerprint.get('theme_keywords'))
        has_supporting = bool(fingerprint.get('supporting_entities'))
        
        print(f"  Has Theme Keywords: {has_themes}")
        print(f"  Has Supporting Entities: {has_supporting}")
        print()
    
    # Analysis
    print("=" * 80)
    print("ANALYSIS")
    print("=" * 80)
    print()
    
    if nucleus_entity is None:
        print("⚠️  CRITICAL: nucleus_entity is NULL")
        print()
        print("This means all 229 narratives have no nucleus_entity set.")
        print("The narrative creation logic is failing to extract or set the nucleus_entity.")
        print()
        print("Root Cause: Bug in narrative fingerprint generation")
        print()
        print("Fix Required:")
        print("1. Review narrative_service.py fingerprint generation")
        print("2. Ensure nucleus_entity is always set to a valid entity")
        print("3. Add validation to reject narratives with null nucleus_entity")
        print("4. Backfill existing narratives to set proper nucleus_entity values")
        
    elif nucleus_entity == '':
        print("⚠️  CRITICAL: nucleus_entity is EMPTY STRING")
        print()
        print("This means all 229 narratives have an empty nucleus_entity.")
        print("The narrative creation logic is setting nucleus_entity to empty string.")
        print()
        print("Root Cause: Bug in entity extraction or fingerprint generation")
        print()
        print("Fix Required:")
        print("1. Review entity extraction logic")
        print("2. Ensure at least one entity is extracted from articles")
        print("3. Add validation to reject narratives with empty nucleus_entity")
        print("4. Backfill existing narratives to set proper nucleus_entity values")
        
    else:
        print(f"✓ nucleus_entity has a value: '{nucleus_entity}'")
        print()
        print("This means all 229 narratives are about the same entity.")
        print("The matching logic should have merged them but didn't.")
        print()
        print("Possible Causes:")
        print("1. Matching logic never ran (narratives created before matching was implemented)")
        print("2. Fingerprint similarity threshold is too high")
        print("3. Bug in matching logic that prevents merging")
        print("4. Matching only runs for new narratives, not existing ones")
        print()
        print("Next Steps:")
        print("1. Check when matching logic was implemented")
        print("2. Review matching threshold in narrative_service.py")
        print("3. Run a backfill script to match and merge existing narratives")
    
    print()
    
    # Check creation dates
    print("=" * 80)
    print("CREATION DATE ANALYSIS")
    print("=" * 80)
    print()
    
    # Get earliest and latest narratives
    earliest = narratives_col.find_one(
        {'narrative_fingerprint.nucleus_entity': nucleus_entity},
        sort=[('created_at', 1)]
    )
    
    latest = narratives_col.find_one(
        {'narrative_fingerprint.nucleus_entity': nucleus_entity},
        sort=[('created_at', -1)]
    )
    
    if earliest and latest:
        earliest_date = earliest.get('created_at', 'N/A')
        latest_date = latest.get('created_at', 'N/A')
        
        print(f"Earliest Narrative Created: {earliest_date}")
        print(f"Latest Narrative Created: {latest_date}")
        print()
        
        if isinstance(earliest_date, datetime) and isinstance(latest_date, datetime):
            duration = latest_date - earliest_date
            print(f"Duration: {duration.days} days")
            print()
            print("These narratives were created over an extended period.")
            print("This suggests matching logic was not running during creation.")


if __name__ == '__main__':
    try:
        identify_duplicate_nucleus_entity()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
