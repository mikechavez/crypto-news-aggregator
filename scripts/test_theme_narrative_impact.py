#!/usr/bin/env python3
"""
Test if theme-based narratives are causing the 0% match rate.

This script runs the narrative matching test twice:
1. With all narratives (including theme-based ones)
2. With theme-based narratives filtered out

If match rate jumps significantly when theme-based narratives are excluded,
then backfilling those 15 narratives will fix the matching issue.
"""

import asyncio
import os
from dotenv import load_dotenv
from datetime import datetime, timezone
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from crypto_news_aggregator.db.mongodb import mongo_manager

# Load environment variables
load_dotenv()

# Theme-based nucleus entities to filter out
THEME_BASED_ENTITIES = {
    'defi_adoption',
    'institutional_investment',
    'payments',
    'layer2_scaling',
    'security',
    'infrastructure',
    'nft_gaming',
    'stablecoin',
    'market_analysis',
    'technology',
    'partnerships',
    'crypto market',
    'crypto traders',
    'tokenization',  # lowercase version
    'Tokenization',  # capitalized version
    'regulatory',
}


async def test_matching_with_filter(filter_themes: bool = False):
    """
    Test narrative matching with or without theme-based narratives.
    
    Args:
        filter_themes: If True, exclude theme-based narratives from matching
    """
    # Initialize MongoDB
    await mongo_manager.initialize()
    
    try:
        db = await mongo_manager.get_async_database()
        narratives_collection = db.narratives
        
        # Get all narratives
        cursor = narratives_collection.find({})
        all_narratives = await cursor.to_list(length=None)
        
        print(f"\nTotal narratives in database: {len(all_narratives)}")
        
        # Filter out theme-based narratives if requested
        if filter_themes:
            filtered_narratives = []
            excluded_count = 0
            
            for narrative in all_narratives:
                fingerprint = narrative.get('fingerprint', {})
                nucleus_entity = fingerprint.get('nucleus_entity', '') or narrative.get('theme', '')
                
                if nucleus_entity in THEME_BASED_ENTITIES:
                    excluded_count += 1
                else:
                    filtered_narratives.append(narrative)
            
            print(f"Excluded {excluded_count} theme-based narratives")
            print(f"Testing with {len(filtered_narratives)} entity-based narratives")
            test_narratives = filtered_narratives
        else:
            print(f"Testing with all {len(all_narratives)} narratives (including theme-based)")
            test_narratives = all_narratives
        
        # Test matching for each narrative
        total_tested = 0
        successful_matches = 0
        failed_matches = 0
        match_details = []
        
        for narrative in test_narratives:
            narrative_id = str(narrative['_id'])
            fingerprint = narrative.get('fingerprint', {})
            nucleus_entity = fingerprint.get('nucleus_entity', '') or narrative.get('theme', '')
            title = narrative.get('title', 'Untitled')
            
            # Skip narratives without fingerprints
            if not fingerprint or not nucleus_entity:
                continue
            
            total_tested += 1
            
            # Try to find a matching narrative (excluding self)
            # We'll simulate this by checking if the fingerprint would match
            # against other narratives
            try:
                # Get all other narratives to test against
                other_narratives = [n for n in test_narratives if str(n['_id']) != narrative_id]
                
                # Check if this narrative's fingerprint would match any other
                found_match = False
                for other in other_narratives:
                    other_fingerprint = other.get('fingerprint', {})
                    other_nucleus = other_fingerprint.get('nucleus_entity', '') or other.get('theme', '')
                    
                    # Simple match: same nucleus_entity
                    if nucleus_entity and other_nucleus and nucleus_entity == other_nucleus:
                        found_match = True
                        break
                
                if found_match:
                    successful_matches += 1
                else:
                    failed_matches += 1
                    if failed_matches <= 5:  # Show first 5 failures
                        match_details.append({
                            'id': narrative_id,
                            'nucleus_entity': nucleus_entity,
                            'title': title[:60],
                            'article_count': len(narrative.get('article_ids', []))
                        })
            
            except Exception as e:
                failed_matches += 1
                print(f"Error testing narrative {narrative_id}: {e}")
        
        # Calculate match rate
        match_rate = (successful_matches / total_tested * 100) if total_tested > 0 else 0
        
        print(f"\n{'='*80}")
        print(f"MATCHING TEST RESULTS ({'WITH THEME FILTER' if filter_themes else 'WITHOUT FILTER'})")
        print(f"{'='*80}")
        print(f"Total narratives tested: {total_tested}")
        print(f"Successful matches: {successful_matches}")
        print(f"Failed matches: {failed_matches}")
        print(f"Match rate: {match_rate:.1f}%")
        print()
        
        if match_details:
            print("Sample of narratives that failed to match:")
            for detail in match_details:
                print(f"  - {detail['nucleus_entity']}: {detail['title']}")
                print(f"    ID: {detail['id']}, Articles: {detail['article_count']}")
        
        return {
            'total_tested': total_tested,
            'successful_matches': successful_matches,
            'failed_matches': failed_matches,
            'match_rate': match_rate,
            'filter_enabled': filter_themes
        }
    
    finally:
        await mongo_manager.close()


async def run_comparison_test():
    """Run both tests and compare results."""
    
    print("="*80)
    print("NARRATIVE MATCHING COMPARISON TEST")
    print("="*80)
    print()
    print("This test checks if theme-based narratives are causing matching failures.")
    print("We'll run the matching test twice:")
    print("1. With all narratives (including 15 theme-based ones)")
    print("2. With theme-based narratives filtered out")
    print()
    
    # Test 1: Without filter (all narratives)
    print("\n" + "="*80)
    print("TEST 1: MATCHING WITH ALL NARRATIVES")
    print("="*80)
    results_without_filter = await test_matching_with_filter(filter_themes=False)
    
    # Reinitialize for second test
    await mongo_manager.initialize()
    
    # Test 2: With filter (exclude theme-based)
    print("\n" + "="*80)
    print("TEST 2: MATCHING WITH THEME-BASED NARRATIVES EXCLUDED")
    print("="*80)
    results_with_filter = await test_matching_with_filter(filter_themes=True)
    
    # Compare results
    print("\n" + "="*80)
    print("COMPARISON SUMMARY")
    print("="*80)
    print()
    print(f"Match Rate WITHOUT Filter: {results_without_filter['match_rate']:.1f}%")
    print(f"Match Rate WITH Filter:    {results_with_filter['match_rate']:.1f}%")
    print()
    
    improvement = results_with_filter['match_rate'] - results_without_filter['match_rate']
    print(f"Improvement: {improvement:+.1f} percentage points")
    print()
    
    # Diagnosis
    print("="*80)
    print("DIAGNOSIS")
    print("="*80)
    print()
    
    if improvement > 50:
        print("✅ THEME-BASED NARRATIVES ARE THE PRIMARY CAUSE")
        print()
        print("The match rate improved significantly when theme-based narratives")
        print("were excluded. This confirms that backfilling the 15 theme-based")
        print("narratives with proper fingerprints will fix the matching issue.")
        print()
        print("Recommended action:")
        print("1. Run the backfill script to regenerate theme-based fingerprints")
        print("2. Verify that match rate improves to 80%+ after backfill")
    elif improvement > 10:
        print("⚠️  THEME-BASED NARRATIVES ARE A CONTRIBUTING FACTOR")
        print()
        print("The match rate improved moderately when theme-based narratives")
        print("were excluded. Theme-based narratives are part of the problem,")
        print("but there may be other issues as well.")
        print()
        print("Recommended actions:")
        print("1. Backfill the 15 theme-based narratives")
        print("2. Investigate other potential matching issues")
    else:
        print("❌ THEME-BASED NARRATIVES ARE NOT THE CAUSE")
        print()
        print("The match rate did not improve significantly when theme-based")
        print("narratives were excluded. The problem lies elsewhere.")
        print()
        print("Recommended actions:")
        print("1. Check fingerprint generation logic for ALL narratives")
        print("2. Verify that fingerprints are being properly stored")
        print("3. Review the narrative matching algorithm")
        print("4. Check if narratives have duplicate nucleus_entities")
    print()


if __name__ == '__main__':
    asyncio.run(run_comparison_test())
