#!/usr/bin/env python3
"""
Debug script to analyze why new narratives were created instead of matching existing ones.

This script examines narratives created in the last 24 hours and investigates:
1. Their fingerprints (nucleus_entity, top_actors, key_actions)
2. Top 3 similarity scores from find_matching_narrative when they were created
3. Why they didn't match (similarity below 0.6? no candidates found? grace period excluded matches?)
4. If there's an existing narrative with the same nucleus_entity that should have matched

Usage:
    poetry run python scripts/debug_production_matching.py
    poetry run python scripts/debug_production_matching.py --hours 72
"""

import asyncio
import argparse
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from collections import defaultdict

from crypto_news_aggregator.db.mongodb import mongo_manager
from crypto_news_aggregator.services.narrative_themes import calculate_fingerprint_similarity

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def format_fingerprint(fingerprint: Dict[str, Any]) -> str:
    """Format a fingerprint for display."""
    nucleus = fingerprint.get('nucleus_entity', 'N/A')
    actors = fingerprint.get('top_actors', [])
    actions = fingerprint.get('key_actions', [])
    
    return (
        f"  Nucleus: {nucleus}\n"
        f"  Actors: {', '.join(actors) if actors else 'None'}\n"
        f"  Actions: {', '.join(actions) if actions else 'None'}"
    )


async def find_candidate_narratives(
    fingerprint: Dict[str, Any],
    created_at: datetime,
    within_days: int = 14
) -> List[Dict[str, Any]]:
    """
    Find candidate narratives that could have matched at creation time.
    
    Simulates the find_matching_narrative logic to see what candidates
    were available when this narrative was created.
    
    Args:
        fingerprint: The fingerprint of the new narrative
        created_at: When the narrative was created
        within_days: Time window in days to search for matching narratives
    
    Returns:
        List of candidate narratives with similarity scores
    """
    db = await mongo_manager.get_async_database()
    narratives_collection = db.narratives
    
    # Calculate time window relative to when narrative was created
    cutoff_time = created_at - timedelta(days=within_days)
    
    # Query for active narratives within time window (before this narrative was created)
    active_statuses = ['emerging', 'rising', 'hot', 'cooling', 'dormant']
    query = {
        'first_seen': {'$lt': created_at},  # Existed before this narrative
        'last_updated': {'$gte': cutoff_time},  # Active within time window
        '$or': [
            {'status': {'$in': active_statuses}},
            {'lifecycle_state': {'$in': active_statuses}}
        ]
    }
    
    cursor = narratives_collection.find(query)
    candidates = await cursor.to_list(length=None)
    
    # Calculate similarity for each candidate
    candidates_with_scores = []
    for candidate in candidates:
        # Extract fingerprint from candidate narrative
        candidate_fingerprint = candidate.get('fingerprint')
        if not candidate_fingerprint:
            # Try to construct fingerprint from legacy fields
            candidate_fingerprint = {
                'nucleus_entity': candidate.get('theme', ''),
                'top_actors': candidate.get('entities', []),
                'key_actions': []  # Legacy narratives may not have actions
            }
        
        # Calculate similarity
        similarity = calculate_fingerprint_similarity(fingerprint, candidate_fingerprint)
        
        candidates_with_scores.append({
            'narrative': candidate,
            'similarity': similarity,
            'fingerprint': candidate_fingerprint
        })
    
    # Sort by similarity (descending)
    candidates_with_scores.sort(key=lambda x: x['similarity'], reverse=True)
    
    return candidates_with_scores


async def analyze_narrative_creation(
    narrative: Dict[str, Any],
    all_narratives: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Analyze why a narrative was created instead of matching an existing one.
    
    Args:
        narrative: The narrative to analyze
        all_narratives: All narratives in the database for comparison
    
    Returns:
        Analysis dict with findings
    """
    narrative_id = str(narrative['_id'])
    title = narrative.get('title', 'Unknown')
    fingerprint = narrative.get('fingerprint', {})
    created_at = narrative.get('first_seen', datetime.now(timezone.utc))
    
    # Ensure created_at is timezone-aware
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    
    logger.info(f"\nAnalyzing narrative: {title}")
    logger.info(f"Created at: {created_at}")
    logger.info(f"Fingerprint:\n{format_fingerprint(fingerprint)}")
    
    # Find candidates that were available at creation time
    candidates = await find_candidate_narratives(fingerprint, created_at, within_days=14)
    
    # Analyze why it didn't match
    analysis = {
        'narrative_id': narrative_id,
        'title': title,
        'created_at': created_at,
        'fingerprint': fingerprint,
        'total_candidates': len(candidates),
        'top_3_candidates': [],
        'reason': 'unknown',
        'same_nucleus_narratives': []
    }
    
    # Get top 3 candidates
    for i, candidate_data in enumerate(candidates[:3]):
        candidate = candidate_data['narrative']
        similarity = candidate_data['similarity']
        candidate_fp = candidate_data['fingerprint']
        
        analysis['top_3_candidates'].append({
            'title': candidate.get('title', 'Unknown'),
            'similarity': similarity,
            'fingerprint': candidate_fp,
            'created_at': candidate.get('first_seen'),
            'last_updated': candidate.get('last_updated')
        })
    
    # Determine reason for not matching
    if not candidates:
        analysis['reason'] = 'no_candidates_found'
        logger.warning("  ❌ No candidate narratives found within time window")
    elif candidates[0]['similarity'] < 0.6:
        analysis['reason'] = 'similarity_below_threshold'
        best_similarity = candidates[0]['similarity']
        logger.warning(f"  ❌ Best similarity ({best_similarity:.3f}) below threshold (0.6)")
    else:
        analysis['reason'] = 'should_have_matched'
        best_similarity = candidates[0]['similarity']
        logger.error(f"  ⚠️  Best similarity ({best_similarity:.3f}) ABOVE threshold - should have matched!")
    
    # Find narratives with same nucleus_entity
    nucleus = fingerprint.get('nucleus_entity', '')
    if nucleus:
        same_nucleus = []
        for n in all_narratives:
            if n.get('fingerprint', {}).get('nucleus_entity') == nucleus and n['_id'] != narrative['_id']:
                n_first_seen = n.get('first_seen', datetime.now(timezone.utc))
                # Ensure timezone-aware comparison
                if n_first_seen.tzinfo is None:
                    n_first_seen = n_first_seen.replace(tzinfo=timezone.utc)
                if n_first_seen < created_at:
                    same_nucleus.append(n)
        
        if same_nucleus:
            logger.info(f"  📌 Found {len(same_nucleus)} narratives with same nucleus entity: {nucleus}")
            for sn in same_nucleus[:3]:  # Show top 3
                sn_fp = sn.get('fingerprint', {})
                similarity = calculate_fingerprint_similarity(fingerprint, sn_fp)
                analysis['same_nucleus_narratives'].append({
                    'title': sn.get('title', 'Unknown'),
                    'similarity': similarity,
                    'created_at': sn.get('first_seen'),
                    'last_updated': sn.get('last_updated')
                })
                logger.info(f"    - {sn.get('title', 'Unknown')} (similarity: {similarity:.3f})")
    
    return analysis


async def debug_production_matching(hours: int = 24):
    """
    Debug why new narratives were created instead of matching existing ones.
    
    Args:
        hours: Look back this many hours for newly created narratives
    """
    logger.info(f"=== Debugging Narrative Matching (last {hours} hours) ===\n")
    
    # Connect to database
    db = await mongo_manager.get_async_database()
    narratives_collection = db.narratives
    
    # Get all narratives for comparison
    all_narratives = await narratives_collection.find({}).to_list(length=None)
    logger.info(f"Total narratives in database: {len(all_narratives)}")
    
    # Find narratives created in the last N hours
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    cursor = narratives_collection.find({
        'first_seen': {'$gte': cutoff_time}
    }).sort('first_seen', 1)  # Sort by creation time (oldest first)
    
    new_narratives = await cursor.to_list(length=None)
    
    logger.info(f"New narratives created in last {hours}h: {len(new_narratives)}\n")
    
    if not new_narratives:
        logger.info("No new narratives found in the specified time window.")
        return
    
    # Analyze each new narrative
    analyses = []
    for narrative in new_narratives:
        analysis = await analyze_narrative_creation(narrative, all_narratives)
        analyses.append(analysis)
        logger.info("")  # Blank line between narratives
    
    # Summary statistics
    logger.info("\n" + "="*80)
    logger.info("SUMMARY")
    logger.info("="*80)
    
    reason_counts = defaultdict(int)
    for analysis in analyses:
        reason_counts[analysis['reason']] += 1
    
    logger.info(f"\nTotal new narratives analyzed: {len(analyses)}")
    logger.info("\nReasons for not matching:")
    for reason, count in reason_counts.items():
        percentage = (count / len(analyses)) * 100
        logger.info(f"  - {reason}: {count} ({percentage:.1f}%)")
    
    # Show narratives that should have matched
    should_have_matched = [a for a in analyses if a['reason'] == 'should_have_matched']
    if should_have_matched:
        logger.info(f"\n⚠️  {len(should_have_matched)} narratives had similarity > 0.6 but didn't match:")
        for analysis in should_have_matched:
            logger.info(f"  - {analysis['title']}")
            if analysis['top_3_candidates']:
                best = analysis['top_3_candidates'][0]
                logger.info(f"    Best match: {best['title']} (similarity: {best['similarity']:.3f})")
    
    # Show narratives with low similarity
    low_similarity = [a for a in analyses if a['reason'] == 'similarity_below_threshold']
    if low_similarity:
        logger.info(f"\n📊 {len(low_similarity)} narratives had similarity < 0.6:")
        for analysis in low_similarity:
            logger.info(f"  - {analysis['title']}")
            if analysis['top_3_candidates']:
                best = analysis['top_3_candidates'][0]
                logger.info(f"    Best match: {best['title']} (similarity: {best['similarity']:.3f})")
            
            # Check if same nucleus exists
            if analysis['same_nucleus_narratives']:
                logger.info(f"    ⚠️  Has {len(analysis['same_nucleus_narratives'])} narratives with same nucleus!")
    
    # Show narratives with no candidates
    no_candidates = [a for a in analyses if a['reason'] == 'no_candidates_found']
    if no_candidates:
        logger.info(f"\n❌ {len(no_candidates)} narratives had no candidates within time window:")
        for analysis in no_candidates:
            logger.info(f"  - {analysis['title']}")
            nucleus = analysis['fingerprint'].get('nucleus_entity', 'N/A')
            logger.info(f"    Nucleus: {nucleus}")
    
    logger.info("\n" + "="*80)
    logger.info("DETAILED ANALYSIS")
    logger.info("="*80)
    
    for i, analysis in enumerate(analyses, 1):
        logger.info(f"\n{i}. {analysis['title']}")
        logger.info(f"   ID: {analysis['narrative_id']}")
        logger.info(f"   Created: {analysis['created_at']}")
        logger.info(f"   Reason: {analysis['reason']}")
        logger.info(f"   Fingerprint:\n{format_fingerprint(analysis['fingerprint'])}")
        
        if analysis['top_3_candidates']:
            logger.info(f"\n   Top 3 Candidate Matches:")
            for j, candidate in enumerate(analysis['top_3_candidates'], 1):
                logger.info(f"   {j}. {candidate['title']}")
                logger.info(f"      Similarity: {candidate['similarity']:.3f}")
                logger.info(f"      Created: {candidate['created_at']}")
                logger.info(f"      Last Updated: {candidate['last_updated']}")
                logger.info(f"      Fingerprint:\n{format_fingerprint(candidate['fingerprint'])}")
        else:
            logger.info(f"\n   No candidates found within time window")
        
        if analysis['same_nucleus_narratives']:
            logger.info(f"\n   Narratives with Same Nucleus Entity:")
            for j, same_nucleus in enumerate(analysis['same_nucleus_narratives'], 1):
                logger.info(f"   {j}. {same_nucleus['title']}")
                logger.info(f"      Similarity: {same_nucleus['similarity']:.3f}")
                logger.info(f"      Created: {same_nucleus['created_at']}")
                logger.info(f"      Last Updated: {same_nucleus['last_updated']}")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Debug why new narratives were created instead of matching existing ones'
    )
    parser.add_argument(
        '--hours',
        type=int,
        default=24,
        help='Look back this many hours for newly created narratives (default: 24)'
    )
    
    args = parser.parse_args()
    
    try:
        await debug_production_matching(hours=args.hours)
    except Exception as e:
        logger.exception(f"Error during analysis: {e}")
        raise
    finally:
        # Close MongoDB connection
        await mongo_manager.close()


if __name__ == '__main__':
    asyncio.run(main())
