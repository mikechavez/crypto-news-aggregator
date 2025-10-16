#!/usr/bin/env python3
"""
Debug script to investigate narrative matching failures.

This script:
1. Examines the first 3 existing narratives in the database
2. Checks their fingerprint structure and values
3. Tests similarity calculation with a test cluster fingerprint
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from crypto_news_aggregator.db.mongodb import mongo_manager
from crypto_news_aggregator.services.narrative_themes import calculate_fingerprint_similarity


async def debug_matching_failure():
    """Debug why narrative matching is failing."""
    print("=" * 80)
    print("NARRATIVE MATCHING DEBUG SCRIPT")
    print("=" * 80)
    print()
    
    # Get database connection
    db = await mongo_manager.get_async_database()
    narratives_collection = db.narratives
    
    # Fetch first 3 narratives
    print("Fetching first 3 narratives from database...")
    cursor = narratives_collection.find().limit(3)
    narratives = await cursor.to_list(length=3)
    
    if not narratives:
        print("❌ No narratives found in database!")
        return
    
    print(f"✓ Found {len(narratives)} narratives\n")
    
    # Test cluster fingerprint from test_narrative_matching.py
    test_fingerprint = {
        'nucleus_entity': 'SEC',
        'top_actors': ['SEC', 'Binance', 'Coinbase'],
        'key_actions': ['filed lawsuit', 'regulatory enforcement']
    }
    
    print("=" * 80)
    print("TEST CLUSTER FINGERPRINT")
    print("=" * 80)
    print(f"Nucleus Entity: {test_fingerprint['nucleus_entity']}")
    print(f"Top Actors: {test_fingerprint['top_actors']}")
    print(f"Key Actions: {test_fingerprint['key_actions']}")
    print()
    
    # Examine each narrative
    for i, narrative in enumerate(narratives, 1):
        print("=" * 80)
        print(f"NARRATIVE {i}: {narrative.get('title', 'UNTITLED')}")
        print("=" * 80)
        print(f"ID: {narrative.get('_id')}")
        print(f"Status: {narrative.get('status', 'unknown')}")
        print(f"Last Updated: {narrative.get('last_updated', 'unknown')}")
        print()
        
        # Check if fingerprint field exists
        has_fingerprint = 'fingerprint' in narrative
        print(f"Has 'fingerprint' field: {has_fingerprint}")
        
        if has_fingerprint:
            fingerprint = narrative['fingerprint']
            print(f"Fingerprint type: {type(fingerprint).__name__}")
            
            if isinstance(fingerprint, dict):
                print("\nFingerprint structure:")
                print(f"  - nucleus_entity: {fingerprint.get('nucleus_entity', 'MISSING')}")
                print(f"  - top_actors: {fingerprint.get('top_actors', 'MISSING')}")
                print(f"  - key_actions: {fingerprint.get('key_actions', 'MISSING')}")
                
                # Check if it's a valid fingerprint
                has_nucleus = 'nucleus_entity' in fingerprint
                has_actors = 'top_actors' in fingerprint
                has_actions = 'key_actions' in fingerprint
                
                print(f"\nFingerprint completeness:")
                print(f"  - Has nucleus_entity: {has_nucleus}")
                print(f"  - Has top_actors: {has_actors}")
                print(f"  - Has key_actions: {has_actions}")
                
                if has_nucleus:
                    print(f"\nNucleus Entity Value: '{fingerprint.get('nucleus_entity')}'")
                if has_actors:
                    actors = fingerprint.get('top_actors', [])
                    print(f"Top Actors ({len(actors)} total): {actors}")
                if has_actions:
                    actions = fingerprint.get('key_actions', [])
                    print(f"Key Actions ({len(actions)} total): {actions}")
            elif isinstance(fingerprint, str):
                print(f"\n⚠️  Fingerprint is a STRING (should be dict): {fingerprint[:100]}...")
            else:
                print(f"\n⚠️  Fingerprint is unexpected type: {type(fingerprint)}")
        else:
            print("\n⚠️  No fingerprint field found")
            print("\nLegacy fields:")
            print(f"  - theme: {narrative.get('theme', 'MISSING')}")
            print(f"  - entities: {narrative.get('entities', 'MISSING')}")
        
        print()
        
        # Calculate similarity with test fingerprint
        print("-" * 80)
        print("SIMILARITY CALCULATION WITH TEST CLUSTER")
        print("-" * 80)
        
        # Prepare candidate fingerprint
        if has_fingerprint and isinstance(narrative.get('fingerprint'), dict):
            candidate_fingerprint = narrative['fingerprint']
        else:
            # Construct from legacy fields
            candidate_fingerprint = {
                'nucleus_entity': narrative.get('theme', ''),
                'top_actors': narrative.get('entities', []),
                'key_actions': []
            }
            print("⚠️  Using legacy fields to construct fingerprint")
        
        try:
            similarity = calculate_fingerprint_similarity(test_fingerprint, candidate_fingerprint)
            print(f"Similarity Score: {similarity:.4f}")
            
            # Breakdown
            test_nucleus = test_fingerprint.get('nucleus_entity', '')
            cand_nucleus = candidate_fingerprint.get('nucleus_entity', '')
            nucleus_match = test_nucleus == cand_nucleus
            
            test_actors = set(test_fingerprint.get('top_actors', []))
            cand_actors = set(candidate_fingerprint.get('top_actors', []))
            actor_overlap = len(test_actors & cand_actors)
            actor_union = len(test_actors | cand_actors)
            
            test_actions = set(test_fingerprint.get('key_actions', []))
            cand_actions = set(candidate_fingerprint.get('key_actions', []))
            action_overlap = len(test_actions & cand_actions)
            action_union = len(test_actions | cand_actions)
            
            print(f"\nBreakdown:")
            print(f"  Nucleus Match: {nucleus_match} ('{test_nucleus}' vs '{cand_nucleus}')")
            print(f"  Actor Overlap: {actor_overlap}/{actor_union} actors")
            print(f"    Test actors: {test_actors}")
            print(f"    Candidate actors: {cand_actors}")
            print(f"    Intersection: {test_actors & cand_actors}")
            print(f"  Action Overlap: {action_overlap}/{action_union} actions")
            print(f"    Test actions: {test_actions}")
            print(f"    Candidate actions: {cand_actions}")
            print(f"    Intersection: {test_actions & cand_actions}")
            
            # Determine if would match (threshold is 0.6)
            would_match = similarity > 0.6
            print(f"\n{'✓' if would_match else '✗'} Would match (threshold: 0.6): {would_match}")
            
        except Exception as e:
            print(f"❌ Error calculating similarity: {e}")
            import traceback
            traceback.print_exc()
        
        print()
    
    print("=" * 80)
    print("DEBUG COMPLETE")
    print("=" * 80)
    print("\nKey Findings:")
    print("- Check if narratives have valid fingerprint dicts")
    print("- Verify fingerprint structure matches expected format")
    print("- Review similarity scores and component breakdowns")
    print("- Threshold for matching is 0.6 (60% similarity)")


if __name__ == "__main__":
    asyncio.run(debug_matching_failure())
