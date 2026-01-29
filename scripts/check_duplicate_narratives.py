#!/usr/bin/env python3
"""
Check for duplicate narratives that should have matched but didn't.

This script identifies narratives with the same nucleus_entity, which indicates
potential matching failures. When multiple narratives share the same nucleus_entity,
they should have been merged into a single narrative.
"""

import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.crypto_news_aggregator.db.mongodb import mongo_manager


def check_duplicate_narratives():
    """Find and analyze narratives with duplicate nucleus_entity values."""
    
    print("=" * 80)
    print("DUPLICATE NARRATIVE DETECTION")
    print("=" * 80)
    print()
    
    # Step 1: Aggregate to find nucleus_entity counts
    print("Step 1: Finding nucleus_entity values that appear multiple times...")
    print()
    
    pipeline = [
        {'$group': {
            '_id': '$narrative_fingerprint.nucleus_entity',
            'count': {'$sum': 1}
        }},
        {'$match': {'count': {'$gt': 1}}},
        {'$sort': {'count': -1}}
    ]
    
    narratives_col = mongo_manager.get_collection('narratives')
    duplicate_counts = list(narratives_col.aggregate(pipeline))
    
    if not duplicate_counts:
        print("✓ No duplicate nucleus_entity values found!")
        print("  All narratives have unique nucleus entities.")
        return
    
    print(f"⚠ Found {len(duplicate_counts)} nucleus_entity values with duplicates")
    print()
    
    # Step 2: Analyze each duplicate nucleus_entity
    print("=" * 80)
    print("DETAILED DUPLICATE ANALYSIS")
    print("=" * 80)
    print()
    
    total_duplicate_narratives = 0
    
    for idx, item in enumerate(duplicate_counts, 1):
        nucleus_entity = item['_id']
        count = item['count']
        
        total_duplicate_narratives += count
        
        print(f"{idx}. Nucleus Entity: '{nucleus_entity}'")
        print(f"   Duplicate Count: {count} narratives")
        print()
        
        # Fetch all narratives with this nucleus_entity
        narratives = list(narratives_col.find({
            'narrative_fingerprint.nucleus_entity': nucleus_entity
        }).sort('last_updated', -1))
        
        # Display details for each duplicate
        for i, narrative in enumerate(narratives, 1):
            title = narrative.get('title', 'N/A')
            article_count = len(narrative.get('article_ids', []))
            last_updated = narrative.get('last_updated')
            lifecycle_state = narrative.get('lifecycle_state', 'N/A')
            
            # Format last_updated
            if isinstance(last_updated, datetime):
                last_updated_str = last_updated.strftime('%Y-%m-%d %H:%M:%S')
            else:
                last_updated_str = str(last_updated) if last_updated else 'N/A'
            
            # Get fingerprint details
            fingerprint = narrative.get('narrative_fingerprint', {})
            theme_keywords = fingerprint.get('theme_keywords', [])
            supporting_entities = fingerprint.get('supporting_entities', [])
            
            print(f"   [{i}] Title: {title}")
            print(f"       Article Count: {article_count}")
            print(f"       Last Updated: {last_updated_str}")
            print(f"       Lifecycle State: {lifecycle_state}")
            print(f"       Theme Keywords: {theme_keywords[:5]}")  # Show first 5
            print(f"       Supporting Entities: {supporting_entities[:5]}")  # Show first 5
            print()
        
        print("-" * 80)
        print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print(f"Total unique nucleus_entity values with duplicates: {len(duplicate_counts)}")
    print(f"Total narratives involved in duplication: {total_duplicate_narratives}")
    print(f"Average narratives per duplicate nucleus_entity: {total_duplicate_narratives / len(duplicate_counts):.2f}")
    print()
    
    # Additional analysis: Check for patterns
    print("=" * 80)
    print("PATTERN ANALYSIS")
    print("=" * 80)
    print()
    
    # Group by lifecycle state
    lifecycle_distribution = defaultdict(int)
    for item in duplicate_counts:
        nucleus_entity = item['_id']
        narratives = list(narratives_col.find({
            'narrative_fingerprint.nucleus_entity': nucleus_entity
        }))
        
        for narrative in narratives:
            state = narrative.get('lifecycle_state', 'unknown')
            lifecycle_distribution[state] += 1
    
    print("Lifecycle State Distribution of Duplicate Narratives:")
    for state, count in sorted(lifecycle_distribution.items(), key=lambda x: x[1], reverse=True):
        print(f"  {state}: {count} narratives")
    print()
    
    # Check for theme vs entity narratives
    theme_count = 0
    entity_count = 0
    
    for item in duplicate_counts:
        nucleus_entity = item['_id']
        narratives = list(narratives_col.find({
            'narrative_fingerprint.nucleus_entity': nucleus_entity
        }))
        
        for narrative in narratives:
            fingerprint = narrative.get('narrative_fingerprint', {})
            theme_keywords = fingerprint.get('theme_keywords', [])
            
            if theme_keywords:
                theme_count += 1
            else:
                entity_count += 1
    
    print("Narrative Type Distribution:")
    print(f"  Theme-based narratives: {theme_count}")
    print(f"  Entity-only narratives: {entity_count}")
    print()
    
    # Recommendations
    print("=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    print()
    print("These duplicate narratives indicate matching failures. Possible causes:")
    print()
    print("1. Fingerprint similarity threshold too strict")
    print("   → Consider lowering the similarity threshold in narrative matching")
    print()
    print("2. Theme keywords preventing matches")
    print("   → Review if theme keywords are too different for same nucleus_entity")
    print()
    print("3. Timing issues in matching logic")
    print("   → Check if narratives were created before matching logic was active")
    print()
    print("4. Supporting entities divergence")
    print("   → Verify if supporting entities are preventing otherwise good matches")
    print()


if __name__ == '__main__':
    try:
        check_duplicate_narratives()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
