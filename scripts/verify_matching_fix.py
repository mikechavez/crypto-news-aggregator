#!/usr/bin/env python3
"""
Verify narrative actions backfill and re-test matching.

This script verifies that the backfill succeeded and tests whether
narratives now match correctly with populated key_actions.
"""

import asyncio
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from crypto_news_aggregator.db.mongodb import mongo_manager
from crypto_news_aggregator.services.narrative_service import find_matching_narrative
from crypto_news_aggregator.services.narrative_themes import calculate_fingerprint_similarity


async def verify_backfill_stats() -> Dict[str, Any]:
    """
    Verify backfill statistics.
    
    Returns:
        Dict with total count, populated count, percentage, and samples
    """
    print("=" * 80)
    print("PART 1: BACKFILL VERIFICATION")
    print("=" * 80)
    
    db = await mongo_manager.get_async_database()
    narratives_collection = db.narratives
    
    # 1. Total narratives count
    total_count = await narratives_collection.count_documents({})
    print(f"\n1. Total narratives in database: {total_count}")
    
    # 2. Count with populated key_actions (not empty array)
    populated_count = await narratives_collection.count_documents({
        "fingerprint.key_actions": {"$exists": True, "$ne": [], "$ne": None}
    })
    print(f"2. Narratives with populated key_actions: {populated_count}")
    
    # 3. Percentage with actions
    percentage = (populated_count / total_count * 100) if total_count > 0 else 0
    print(f"3. Percentage with actions: {percentage:.1f}%")
    
    # 4. Sample 5 narratives showing their fingerprints with actions
    print(f"\n4. Sample narratives with populated key_actions:")
    print("-" * 80)
    
    cursor = narratives_collection.find(
        {"fingerprint.key_actions": {"$exists": True, "$ne": [], "$ne": None}},
        limit=5
    )
    
    samples = []
    idx = 1
    async for narrative in cursor:
        fingerprint = narrative.get("fingerprint", {})
        theme = narrative.get("theme", "unknown")
        title = narrative.get("title", "No title")
        
        sample = {
            "theme": theme,
            "title": title,
            "fingerprint": fingerprint
        }
        samples.append(sample)
        
        print(f"\nSample {idx}:")
        print(f"  Theme: {theme}")
        print(f"  Title: {title}")
        print(f"  Fingerprint:")
        print(f"    - Nucleus Entity: {fingerprint.get('nucleus_entity', 'N/A')}")
        print(f"    - Top Actors: {fingerprint.get('top_actors', [])}")
        print(f"    - Key Actions: {fingerprint.get('key_actions', [])}")
        idx += 1
    
    return {
        "total_count": total_count,
        "populated_count": populated_count,
        "percentage": percentage,
        "samples": samples
    }


async def test_matching_last_24h() -> Dict[str, Any]:
    """
    Re-test narrative matching for narratives from last 24 hours.
    
    Returns:
        Dict with match statistics and top similarity scores
    """
    print("\n" + "=" * 80)
    print("PART 2: MATCHING TEST (LAST 24 HOURS)")
    print("=" * 80)
    
    db = await mongo_manager.get_async_database()
    narratives_collection = db.narratives
    
    # Get narratives from last 24 hours
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
    
    cursor = narratives_collection.find(
        {"last_updated": {"$gte": cutoff_time}},
        sort=[("last_updated", -1)]
    )
    
    recent_narratives = await cursor.to_list(length=None)
    total_recent = len(recent_narratives)
    
    print(f"\nFound {total_recent} narratives from last 24 hours")
    
    if total_recent == 0:
        print("No recent narratives to test. Exiting.")
        return {
            "total_narratives": 0,
            "matches_found": 0,
            "new_narratives": 0,
            "match_rate": 0,
            "top_similarities": []
        }
    
    # Test matching for each narrative
    matches_found = 0
    new_narratives = 0
    similarity_scores = []
    match_details = []
    
    print(f"\nTesting matching for {total_recent} narratives...")
    print("-" * 80)
    
    for idx, narrative in enumerate(recent_narratives, 1):
        narrative_id = str(narrative.get("_id"))
        theme = narrative.get("theme", "unknown")
        fingerprint = narrative.get("fingerprint")
        
        if not fingerprint:
            # Skip narratives without fingerprints
            continue
        
        # Exclude self from search by looking for narratives updated before this one
        narrative_updated = narrative.get("last_updated")
        
        # Try to find a matching narrative (excluding self)
        # We'll search in narratives updated before this one
        try:
            # Get candidates from before this narrative
            candidate_cursor = narratives_collection.find({
                "last_updated": {
                    "$gte": cutoff_time - timedelta(days=14),  # Look back 14 days
                    "$lt": narrative_updated  # But before this narrative
                },
                "_id": {"$ne": narrative.get("_id")}  # Exclude self
            })
            
            candidates = await candidate_cursor.to_list(length=None)
            
            best_match = None
            best_similarity = 0.0
            
            for candidate in candidates:
                candidate_fingerprint = candidate.get("fingerprint")
                if not candidate_fingerprint:
                    # Try to construct from legacy fields
                    candidate_fingerprint = {
                        'nucleus_entity': candidate.get('theme', ''),
                        'top_actors': candidate.get('entities', []),
                        'key_actions': []
                    }
                
                # Calculate similarity
                similarity = calculate_fingerprint_similarity(fingerprint, candidate_fingerprint)
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = candidate
            
            # Check if similarity exceeds threshold (0.6)
            if best_similarity >= 0.6:
                matches_found += 1
                match_details.append({
                    "narrative_theme": theme,
                    "matched_theme": best_match.get("theme", "unknown"),
                    "similarity": best_similarity
                })
                status = f"✓ MATCH (similarity: {best_similarity:.3f})"
            else:
                new_narratives += 1
                status = f"✗ NEW (best similarity: {best_similarity:.3f})"
            
            similarity_scores.append(best_similarity)
            
            if idx <= 10:  # Show first 10 for brevity
                print(f"[{idx}/{total_recent}] {theme[:40]:40} | {status}")
        
        except Exception as e:
            print(f"[{idx}/{total_recent}] Error testing {theme}: {e}")
            new_narratives += 1
    
    # Calculate match rate
    match_rate = (matches_found / total_recent * 100) if total_recent > 0 else 0
    
    # Get top 5 similarity scores
    similarity_scores.sort(reverse=True)
    top_5_similarities = similarity_scores[:5]
    
    print("\n" + "=" * 80)
    print("MATCHING RESULTS")
    print("=" * 80)
    print(f"\nTotal narratives tested: {total_recent}")
    print(f"Matches found (≥0.6 similarity): {matches_found}")
    print(f"New narratives (<0.6 similarity): {new_narratives}")
    print(f"Match rate: {match_rate:.1f}%")
    
    print(f"\nTop 5 similarity scores achieved:")
    for idx, score in enumerate(top_5_similarities, 1):
        print(f"  {idx}. {score:.3f}")
    
    if match_details:
        print(f"\nTop 5 matches:")
        for idx, match in enumerate(match_details[:5], 1):
            print(f"  {idx}. {match['narrative_theme'][:40]:40} → {match['matched_theme'][:40]:40} (similarity: {match['similarity']:.3f})")
    
    return {
        "total_narratives": total_recent,
        "matches_found": matches_found,
        "new_narratives": new_narratives,
        "match_rate": match_rate,
        "top_similarities": top_5_similarities,
        "match_details": match_details[:5]
    }


async def compare_results(matching_stats: Dict[str, Any]):
    """
    Compare before vs after results.
    
    Args:
        matching_stats: Statistics from matching test
    """
    print("\n" + "=" * 80)
    print("PART 3: BEFORE vs AFTER COMPARISON")
    print("=" * 80)
    
    # Before stats (from MATCHING_FAILURE_DEBUG_RESULTS.md)
    before_match_rate = 0.0  # 0% match rate before
    before_top_similarity = 0.5  # Estimated from debug results
    
    # After stats
    after_match_rate = matching_stats["match_rate"]
    after_top_similarity = matching_stats["top_similarities"][0] if matching_stats["top_similarities"] else 0.0
    
    print("\n📊 MATCH RATE")
    print(f"  Before backfill: {before_match_rate:.1f}%")
    print(f"  After backfill:  {after_match_rate:.1f}%")
    
    if after_match_rate > before_match_rate:
        improvement = after_match_rate - before_match_rate
        print(f"  ✓ Improvement: +{improvement:.1f} percentage points")
    else:
        print(f"  ⚠ No improvement detected")
    
    print("\n📈 SIMILARITY SCORES")
    print(f"  Before backfill (best): {before_top_similarity:.3f}")
    print(f"  After backfill (best):  {after_top_similarity:.3f}")
    
    if after_top_similarity > before_top_similarity:
        improvement = after_top_similarity - before_top_similarity
        print(f"  ✓ Improvement: +{improvement:.3f}")
    else:
        print(f"  ⚠ No improvement in top score")
    
    print("\n🎯 THRESHOLD ANALYSIS")
    print(f"  Matching threshold: 0.600")
    print(f"  Narratives above threshold: {matching_stats['matches_found']}")
    print(f"  Narratives below threshold: {matching_stats['new_narratives']}")
    
    # Show how many scores are in different ranges
    if matching_stats["top_similarities"]:
        scores = matching_stats["top_similarities"]
        excellent = sum(1 for s in scores if s >= 0.8)
        good = sum(1 for s in scores if 0.6 <= s < 0.8)
        poor = sum(1 for s in scores if s < 0.6)
        
        print(f"\n📊 SIMILARITY DISTRIBUTION (Top scores)")
        print(f"  Excellent (≥0.8): {excellent}")
        print(f"  Good (0.6-0.8):  {good}")
        print(f"  Poor (<0.6):     {poor}")
    
    print("\n" + "=" * 80)
    print("CONCLUSION")
    print("=" * 80)
    
    if after_match_rate > 0:
        print("\n✅ SUCCESS: Narratives are now matching!")
        print(f"   - {matching_stats['matches_found']} narratives matched successfully")
        print(f"   - Match rate improved from {before_match_rate:.1f}% to {after_match_rate:.1f}%")
        print(f"   - Top similarity score: {after_top_similarity:.3f}")
    else:
        print("\n⚠️  WARNING: No matches found yet")
        print("   Possible reasons:")
        print("   - Not enough narratives in last 24 hours")
        print("   - Narratives are genuinely different")
        print("   - May need to wait for more data")
    
    print()


async def main():
    """Main entry point."""
    try:
        print("\n🔍 NARRATIVE MATCHING VERIFICATION")
        print("Verifying backfill and testing matching improvements\n")
        
        # Part 1: Verify backfill
        backfill_stats = await verify_backfill_stats()
        
        # Part 2: Test matching
        matching_stats = await test_matching_last_24h()
        
        # Part 3: Compare results
        await compare_results(matching_stats)
        
        print("=" * 80)
        print("Verification complete!")
        print("=" * 80)
        
    except KeyboardInterrupt:
        print("\n\nVerification interrupted by user")
    except Exception as e:
        print(f"\n\nFatal error during verification: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Close MongoDB connection
        await mongo_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
