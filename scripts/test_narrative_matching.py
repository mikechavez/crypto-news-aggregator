#!/usr/bin/env python3
"""
Test script to verify narrative matching logic.

This script runs narrative detection for the last 72 hours and shows:
- Each cluster's fingerprint (nucleus entity + top 3 actors)
- Whether it matched an existing narrative or created a new one
- Similarity scores for top 3 candidate matches
- Before/after counts of narratives

Runs in dry-run mode to avoid actually saving changes.
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from collections import Counter

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from crypto_news_aggregator.db.mongodb import mongo_manager
from crypto_news_aggregator.services.narrative_service import (
    find_matching_narrative,
    calculate_fingerprint_similarity,
    compute_narrative_fingerprint
)
from crypto_news_aggregator.services.narrative_themes import (
    cluster_by_narrative_salience,
    backfill_narratives_for_recent_articles
)


async def get_narrative_count() -> int:
    """Get current count of narratives in database."""
    db = await mongo_manager.get_async_database()
    narratives_collection = db.narratives
    return await narratives_collection.count_documents({})


async def get_recent_narratives(hours: int = 72) -> List[Dict[str, Any]]:
    """Get narratives created or updated in the last N hours."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    db = await mongo_manager.get_async_database()
    narratives_collection = db.narratives
    
    cursor = narratives_collection.find({
        'last_updated': {'$gte': cutoff}
    }).sort('last_updated', -1)
    
    return await cursor.to_list(length=None)


def format_fingerprint(cluster: Dict[str, Any]) -> str:
    """Format a cluster's fingerprint for display."""
    nucleus = cluster.get('nucleus_entity', 'Unknown')
    actors = cluster.get('actors', [])[:3]  # Top 3 actors
    
    fingerprint = f"Nucleus: {nucleus}"
    if actors:
        fingerprint += f"\n  Actors: {', '.join(actors)}"
    
    return fingerprint


async def test_narrative_matching():
    """Test narrative matching logic in dry-run mode."""
    print("=" * 80)
    print("NARRATIVE MATCHING TEST - DRY RUN MODE")
    print("=" * 80)
    print()
    
    # Get initial state
    print("📊 INITIAL STATE")
    print("-" * 80)
    initial_count = await get_narrative_count()
    print(f"Total narratives in database: {initial_count}")
    
    recent_narratives = await get_recent_narratives(hours=72)
    print(f"Narratives active in last 72 hours: {len(recent_narratives)}")
    print()
    
    # Show existing narratives
    if recent_narratives:
        print("📋 EXISTING NARRATIVES (Last 72 hours)")
        print("-" * 80)
        for i, narrative in enumerate(recent_narratives[:10], 1):  # Show first 10
            fingerprint = narrative.get('fingerprint', {})
            print(f"\n{i}. Narrative #{narrative.get('_id')}")
            print(f"   Title: {narrative.get('title', 'N/A')}")
            print(f"   Nucleus: {fingerprint.get('nucleus_entity', 'N/A')}")
            actors = fingerprint.get('top_actors', [])[:3]
            print(f"   Actors: {', '.join(actors) if actors else 'None'}")
            print(f"   Articles: {narrative.get('article_count', 0)}")
            print(f"   Last updated: {narrative.get('last_updated', 'N/A')}")
        
        if len(recent_narratives) > 10:
            print(f"\n... and {len(recent_narratives) - 10} more narratives")
        print()
    
    # Run narrative detection
    print("🔍 RUNNING NARRATIVE DETECTION")
    print("-" * 80)
    print("Detecting narratives from articles in last 72 hours...")
    print()
    
    # Backfill narrative data for recent articles
    hours = 72
    backfilled_count = await backfill_narratives_for_recent_articles(hours=hours)
    print(f"Backfilled narrative data for {backfilled_count} articles")
    print()
    
    # Get articles from last 72 hours with narrative data
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    db = await mongo_manager.get_async_database()
    articles_collection = db.articles
    
    cursor = articles_collection.find({
        "published_at": {"$gte": cutoff},
        "narrative_summary": {"$exists": True}
    })
    
    articles = await cursor.to_list(length=None)
    print(f"Found {len(articles)} articles with narrative data to analyze")
    print()
    
    if not articles:
        print("⚠️  No articles with narrative data found in the last 72 hours.")
        print("   Cannot test matching. Try running backfill first.")
        return
    
    # Cluster articles by narrative salience
    min_cluster_size = 3
    clusters = await cluster_by_narrative_salience(articles, min_cluster_size=min_cluster_size)
    
    print(f"📦 DETECTED CLUSTERS: {len(clusters)}")
    print("-" * 80)
    print()
    
    # For each cluster, test matching logic
    new_narratives = 0
    updated_narratives = 0
    
    for i, cluster in enumerate(clusters, 1):
        print(f"🔸 CLUSTER #{i}")
        print("-" * 40)
        
        # Build cluster data for fingerprint computation
        nucleus_entities = []
        all_actors = {}
        all_actions = []
        
        for article in cluster:
            if not isinstance(article, dict):
                continue
            
            nucleus = article.get('nucleus_entity')
            if nucleus:
                nucleus_entities.append(nucleus)
            
            # Aggregate actors with salience
            actors = article.get('actors', [])
            actor_salience = article.get('actor_salience', {})
            
            if isinstance(actors, list):
                for actor in actors:
                    salience = actor_salience.get(actor, 3) if isinstance(actor_salience, dict) else 3
                    all_actors[actor] = max(all_actors.get(actor, 0), salience)
            
            # Aggregate actions
            narrative_summary = article.get('narrative_summary', {})
            if isinstance(narrative_summary, dict):
                actions = narrative_summary.get('actions', [])
                if isinstance(actions, list):
                    all_actions.extend(actions)
        
        # Determine primary nucleus (most common)
        nucleus_counts = Counter(nucleus_entities)
        primary_nucleus = nucleus_counts.most_common(1)[0][0] if nucleus_counts else ''
        
        # Build cluster dict for fingerprint
        cluster_data = {
            'nucleus_entity': primary_nucleus,
            'actors': all_actors,
            'actions': list(set(all_actions))[:5]
        }
        
        # Compute fingerprint
        fingerprint = compute_narrative_fingerprint(cluster_data)
        
        print(f"Nucleus: {fingerprint.get('nucleus_entity', 'Unknown')}")
        top_actors = fingerprint.get('top_actors', [])[:3]
        if top_actors:
            print(f"Actors: {', '.join(top_actors)}")
        print(f"Articles in cluster: {len(cluster)}")
        print()
        
        if not primary_nucleus:
            print("⚠️  No nucleus entity - skipping")
            print()
            continue
        
        # Calculate cluster velocity for adaptive grace period
        cluster_article_count = len(cluster)
        cluster_time_span_days = hours / 24.0
        cluster_velocity = cluster_article_count / cluster_time_span_days if cluster_time_span_days > 0 else 0
        
        # Find candidate matches
        print("🔎 Finding candidate matches...")
        matching_narrative = await find_matching_narrative(
            fingerprint,
            cluster_velocity=cluster_velocity
        )
        
        if not matching_narrative:
            print("✨ NO MATCHES FOUND - Would create NEW narrative")
            new_narratives += 1
            print()
            print()
            continue
        
        # Get top candidates for comparison
        db = await mongo_manager.get_async_database()
        narratives_collection = db.narratives
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=14)
        active_statuses = ['emerging', 'rising', 'hot', 'cooling', 'dormant', 'echo', 'reactivated']
        
        cursor = narratives_collection.find({
            'last_updated': {'$gte': cutoff_time},
            '$or': [
                {'status': {'$in': active_statuses}},
                {'lifecycle_state': {'$in': active_statuses}}
            ]
        }).limit(5)
        
        candidates = await cursor.to_list(length=5)
        
        print(f"Found {len(candidates)} candidate narratives")
        print()
        
        # Calculate similarity scores for top 3 candidates
        print("📊 TOP 3 CANDIDATE MATCHES:")
        top_matches = []
        
        for j, candidate in enumerate(candidates[:3], 1):
            # Extract fingerprint from candidate
            candidate_fingerprint = candidate.get('fingerprint')
            if not candidate_fingerprint:
                candidate_fingerprint = {
                    'nucleus_entity': candidate.get('theme', ''),
                    'top_actors': candidate.get('entities', []),
                    'key_actions': []
                }
            
            # Calculate similarity
            similarity = calculate_fingerprint_similarity(fingerprint, candidate_fingerprint)
            top_matches.append((candidate, similarity))
            
            print(f"\n  {j}. Narrative #{candidate.get('_id')}")
            print(f"     Title: {candidate.get('title', 'N/A')}")
            print(f"     Nucleus: {candidate_fingerprint.get('nucleus_entity', 'N/A')}")
            c_actors = candidate_fingerprint.get('top_actors', [])[:3]
            print(f"     Actors: {', '.join(c_actors) if c_actors else 'None'}")
            print(f"     Similarity Score: {similarity:.3f}")
            print(f"     Articles: {candidate.get('article_count', 0)}")
            print(f"     Last updated: {candidate.get('last_updated', 'N/A')}")
        
        print()
        
        # Determine if best match exceeds threshold
        best_match, best_score = top_matches[0] if top_matches else (None, 0.0)
        threshold = 0.6  # Default threshold from find_matching_narrative
        
        if best_score >= threshold:
            print(f"✅ MATCH FOUND - Would UPDATE Narrative #{matching_narrative.get('_id')}")
            print(f"   Match score: {best_score:.3f} >= {threshold:.3f} (threshold)")
            updated_narratives += 1
        else:
            print(f"❌ NO SUFFICIENT MATCH - Would create NEW narrative")
            print(f"   Best score: {best_score:.3f} < {threshold:.3f} (threshold)")
            new_narratives += 1
        
        print()
        print()
    
    # Summary
    print("=" * 80)
    print("📈 SUMMARY")
    print("=" * 80)
    print(f"Narratives before detection:  {initial_count}")
    print(f"Clusters detected:            {len(clusters)}")
    print(f"Would create NEW narratives:  {new_narratives}")
    print(f"Would UPDATE existing:        {updated_narratives}")
    print(f"Narratives after detection:   {initial_count + new_narratives} (projected)")
    print()
    
    # Analysis
    if new_narratives > 0 and updated_narratives > 0:
        print("✅ Matching logic is working - both creating and updating narratives")
    elif new_narratives > 0 and updated_narratives == 0:
        print("⚠️  WARNING: Only creating new narratives, not matching existing ones")
        print("   This suggests potential duplicate narrative creation")
    elif new_narratives == 0 and updated_narratives > 0:
        print("✅ All clusters matched existing narratives - no duplicates")
    else:
        print("ℹ️  No clusters detected or all clusters skipped")
    
    print()
    print("=" * 80)
    print("DRY RUN COMPLETE - No changes were saved to database")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_narrative_matching())
