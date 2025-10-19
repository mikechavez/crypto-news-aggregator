#!/usr/bin/env python3
"""
Analyze duplicate narratives to determine if failed matches are due to:
1. Duplicate narratives with same nucleus_entity that should have merged
2. Legitimately unique entities that correctly didn't match
"""

import asyncio
import os
import sys
from collections import Counter, defaultdict
from dotenv import load_dotenv

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from crypto_news_aggregator.db.mongodb import mongo_manager

# Load environment variables
load_dotenv()

async def analyze_duplicate_narratives():
    """Analyze narratives for duplicates by nucleus_entity."""
    
    try:
        # Connect to MongoDB
        await mongo_manager.connect()
        
        # Get all narratives with their nucleus_entity
        narratives_cursor = mongo_manager.db.narratives.find(
            {},
            {
                '_id': 1,
                'nucleus_entity': 1,
                'title': 1,
                'lifecycle_state': 1,
                'created_at': 1
            }
        ).sort('nucleus_entity', 1)
        
        narratives = await narratives_cursor.to_list(length=None)
        
        print(f"Total narratives in database: {len(narratives)}")
        print("=" * 80)
        
        # Group narratives by nucleus_entity
        entity_groups = defaultdict(list)
        for narrative in narratives:
            entity_groups[narrative['nucleus_entity']].append(narrative)
        
        # Count duplicates
        duplicate_entities = {
            entity: narrs for entity, narrs in entity_groups.items() 
            if len(narrs) > 1
        }
        
        unique_entities = {
            entity: narrs for entity, narrs in entity_groups.items() 
            if len(narrs) == 1
        }
        
        print(f"\n📊 ENTITY DISTRIBUTION:")
        print(f"  Unique entities (appear once): {len(unique_entities)}")
        print(f"  Duplicate entities (appear 2+ times): {len(duplicate_entities)}")
        print(f"  Total unique nucleus_entities: {len(entity_groups)}")
        
        # Calculate narratives in each category
        narratives_with_duplicates = sum(len(narrs) for narrs in duplicate_entities.values())
        narratives_unique = len(unique_entities)
        
        print(f"\n📈 NARRATIVE DISTRIBUTION:")
        print(f"  Narratives with duplicate entities: {narratives_with_duplicates}")
        print(f"  Narratives with unique entities: {narratives_unique}")
        print(f"  Duplicate rate: {narratives_with_duplicates / len(narratives) * 100:.1f}%")
        
        # Show top duplicates
        print(f"\n🔍 TOP DUPLICATE ENTITIES:")
        sorted_duplicates = sorted(
            duplicate_entities.items(), 
            key=lambda x: len(x[1]), 
            reverse=True
        )
        
        for entity, narrs in sorted_duplicates[:20]:
            print(f"\n  Entity: {entity}")
            print(f"  Count: {len(narrs)} narratives")
            for narr in narrs:
                state_emoji = {
                    'emerging': '🌱',
                    'active': '🔥',
                    'cooling': '❄️',
                    'dormant': '💤',
                    'archived': '📦'
                }.get(narr.get('lifecycle_state'), '❓')
                narr_id = str(narr['_id'])
                title = narr.get('title', 'No title')
                state = narr.get('lifecycle_state', 'unknown')
                print(f"    {state_emoji} [{narr_id}] {title[:60]}... ({state})")
        
        # Analyze lifecycle states of duplicates
        print(f"\n📊 DUPLICATE NARRATIVE LIFECYCLE ANALYSIS:")
        duplicate_states = defaultdict(int)
        for entity, narrs in duplicate_entities.items():
            for narr in narrs:
                duplicate_states[narr.get('lifecycle_state', 'unknown')] += 1
        
        for state, count in sorted(duplicate_states.items(), key=lambda x: x[1], reverse=True):
            pct = count / narratives_with_duplicates * 100
            print(f"  {state}: {count} ({pct:.1f}%)")
        
        # Check if duplicates are in different states (might explain why they didn't merge)
        print(f"\n🔄 DUPLICATE GROUPS BY STATE DIVERSITY:")
        same_state_groups = 0
        mixed_state_groups = 0
        
        for entity, narrs in duplicate_entities.items():
            states = set(n.get('lifecycle_state', 'unknown') for n in narrs)
            if len(states) == 1:
                same_state_groups += 1
            else:
                mixed_state_groups += 1
        
        print(f"  Groups with all same state: {same_state_groups}")
        print(f"  Groups with mixed states: {mixed_state_groups}")
        
        # Show some examples of same-state duplicates (these are the problem cases)
        print(f"\n⚠️  PROBLEMATIC DUPLICATES (Same Entity, Same State):")
        problem_count = 0
        for entity, narrs in sorted_duplicates[:50]:
            states = set(n.get('lifecycle_state', 'unknown') for n in narrs)
            if len(states) == 1 and len(narrs) >= 2:
                problem_count += 1
                if problem_count <= 10:
                    print(f"\n  Entity: {entity} (State: {narrs[0].get('lifecycle_state', 'unknown')})")
                    print(f"  {len(narrs)} narratives that should have merged:")
                    for narr in narrs[:5]:  # Show first 5
                        narr_id = str(narr['_id'])
                        title = narr.get('title', 'No title')
                        print(f"    [{narr_id}] {title[:70]}")
        
        print(f"\n  Total same-state duplicate groups: {problem_count}")
        
        # Calculate the "expected" failed match rate
        print(f"\n💡 EXPECTED VS ACTUAL FAILED MATCH RATE:")
        print(f"  If matching worked perfectly:")
        print(f"    - {narratives_unique} unique entities would never match (expected)")
        print(f"    - {narratives_with_duplicates} duplicate narratives should have matched")
        print(f"  Expected 'no match' rate: {narratives_unique / len(narratives) * 100:.1f}%")
        print(f"  Actual 'no match' rate from test: 62.3%")
        
        if narratives_unique / len(narratives) * 100 < 62.3:
            print(f"\n  ⚠️  PROBLEM DETECTED: Actual no-match rate is higher than expected!")
            print(f"     This suggests {62.3 - (narratives_unique / len(narratives) * 100):.1f}% of narratives")
            print(f"     failed to match when they should have.")
        else:
            print(f"\n  ✅ No major problem: Most failed matches are legitimately unique entities")
        
    finally:
        await mongo_manager.disconnect()

if __name__ == '__main__':
    asyncio.run(analyze_duplicate_narratives())
