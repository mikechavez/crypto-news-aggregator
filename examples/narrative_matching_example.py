"""
Example usage of narrative matching functionality.

This demonstrates how to use find_matching_narrative() to check for
existing narratives before creating new ones.
"""

import asyncio
from datetime import datetime, timezone

from src.crypto_news_aggregator.services.narrative_service import find_matching_narrative
from src.crypto_news_aggregator.services.narrative_themes import extract_narrative_fingerprint


async def example_check_for_duplicate_narrative():
    """
    Example: Check if a narrative already exists before creating a new one.
    """
    print("=" * 60)
    print("Example: Checking for Duplicate Narratives")
    print("=" * 60)
    
    # Scenario: We have a new cluster of articles about SEC regulatory actions
    # First, extract fingerprint from the cluster
    
    # For this example, we'll use a mock fingerprint
    # In practice, this would come from extract_narrative_fingerprint()
    new_fingerprint = {
        'nucleus_entity': 'SEC',
        'top_actors': ['SEC', 'Binance', 'Coinbase', 'Kraken'],
        'key_actions': ['filed lawsuit', 'regulatory enforcement', 'compliance review']
    }
    
    print("\n1. New Narrative Fingerprint:")
    print(f"   Nucleus Entity: {new_fingerprint['nucleus_entity']}")
    print(f"   Top Actors: {', '.join(new_fingerprint['top_actors'])}")
    print(f"   Key Actions: {', '.join(new_fingerprint['key_actions'])}")
    
    # Check for existing matching narrative within 14 days
    print("\n2. Searching for matching narratives (within 14 days)...")
    existing_narrative = await find_matching_narrative(
        fingerprint=new_fingerprint,
        within_days=14
    )
    
    if existing_narrative:
        print("\n✓ Found matching narrative!")
        print(f"   ID: {existing_narrative.get('_id')}")
        print(f"   Title: {existing_narrative.get('title')}")
        print(f"   Status: {existing_narrative.get('status')}")
        print(f"   Article Count: {existing_narrative.get('article_count')}")
        print(f"   Last Updated: {existing_narrative.get('last_updated')}")
        print("\n   → Action: Merge new articles into existing narrative")
        
        # In practice, you would:
        # 1. Add new article IDs to existing narrative
        # 2. Update article_count
        # 3. Recalculate lifecycle stage and momentum
        # 4. Update last_updated timestamp
        # 5. Optionally regenerate summary if significant new information
        
    else:
        print("\n✗ No matching narrative found")
        print("   → Action: Create new narrative")
        
        # In practice, you would:
        # 1. Generate narrative title and summary
        # 2. Create new narrative document
        # 3. Save to database


async def example_custom_time_window():
    """
    Example: Use custom time window for matching.
    """
    print("\n" + "=" * 60)
    print("Example: Custom Time Window")
    print("=" * 60)
    
    fingerprint = {
        'nucleus_entity': 'Bitcoin',
        'top_actors': ['MicroStrategy', 'Tesla', 'El Salvador'],
        'key_actions': ['purchased', 'investment', 'adoption']
    }
    
    # Check for matches in last 7 days (shorter window)
    print("\n1. Searching with 7-day window...")
    recent_match = await find_matching_narrative(
        fingerprint=fingerprint,
        within_days=7
    )
    
    if recent_match:
        print(f"   ✓ Found recent match: {recent_match.get('title')}")
    else:
        print("   ✗ No recent match found")
    
    # Check for matches in last 30 days (longer window)
    print("\n2. Searching with 30-day window...")
    older_match = await find_matching_narrative(
        fingerprint=fingerprint,
        within_days=30
    )
    
    if older_match:
        print(f"   ✓ Found older match: {older_match.get('title')}")
        print("   Note: Consider if this narrative should be reactivated")
    else:
        print("   ✗ No match found in extended window")


async def example_similarity_threshold_behavior():
    """
    Example: Understanding similarity threshold behavior.
    """
    print("\n" + "=" * 60)
    print("Example: Similarity Threshold (0.6)")
    print("=" * 60)
    
    print("\nThe function uses a 0.6 similarity threshold:")
    print("- Similarity > 0.6 → Match found, merge narratives")
    print("- Similarity ≤ 0.6 → No match, create new narrative")
    
    print("\nSimilarity is calculated using weighted components:")
    print("- Actor overlap (Jaccard): 50% weight")
    print("- Nucleus match (exact):   30% weight")
    print("- Action overlap (Jaccard): 20% weight")
    
    print("\nExample scenarios:")
    print("\n1. High similarity (0.85):")
    print("   - Same nucleus entity")
    print("   - 80% actor overlap")
    print("   - 60% action overlap")
    print("   → Narratives should be merged")
    
    print("\n2. Medium similarity (0.55):")
    print("   - Same nucleus entity")
    print("   - 40% actor overlap")
    print("   - 30% action overlap")
    print("   → Create separate narrative")
    
    print("\n3. Low similarity (0.25):")
    print("   - Different nucleus entity")
    print("   - 20% actor overlap")
    print("   - 10% action overlap")
    print("   → Clearly distinct narratives")


async def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("NARRATIVE MATCHING EXAMPLES")
    print("=" * 60)
    
    # Note: These examples will work with a live database
    # For demonstration without database, they show the expected behavior
    
    try:
        await example_check_for_duplicate_narrative()
        await example_custom_time_window()
        await example_similarity_threshold_behavior()
        
        print("\n" + "=" * 60)
        print("Examples completed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nError running examples: {e}")
        print("Note: These examples require a MongoDB connection")


if __name__ == "__main__":
    asyncio.run(main())
