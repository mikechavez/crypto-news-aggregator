#!/usr/bin/env python3
"""
Debug script to test similarity calculation between cluster and existing narratives.
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from collections import Counter

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from crypto_news_aggregator.db.mongodb import mongo_manager
from crypto_news_aggregator.services.narrative_themes import (
    calculate_fingerprint_similarity,
    compute_narrative_fingerprint,
    backfill_narratives_for_recent_articles,
    cluster_by_narrative_salience
)


async def debug_similarity():
    """Debug similarity calculation for a specific cluster."""
    print("=" * 80)
    print("SIMILARITY CALCULATION DEBUG")
    print("=" * 80)
    print()
    
    # Backfill narrative data
    print("Backfilling narrative data...")
    backfilled_count = await backfill_narratives_for_recent_articles(hours=72)
    print(f"Backfilled {backfilled_count} articles")
    print()
    
    # Get articles with narrative data
    cutoff = datetime.now(timezone.utc) - timedelta(hours=72)
    db = await mongo_manager.get_async_database()
    articles_collection = db.articles
    
    cursor = articles_collection.find({
        "published_at": {"$gte": cutoff},
        "narrative_summary": {"$exists": True}
    })
    
    articles = await cursor.to_list(length=None)
    print(f"Found {len(articles)} articles with narrative data")
    print()
    
    # Cluster articles
    clusters = await cluster_by_narrative_salience(articles, min_cluster_size=3)
    print(f"Detected {len(clusters)} clusters")
    print()
    
    if not clusters:
        print("No clusters found!")
        return
    
    # Take first cluster as example
    cluster = clusters[0]
    print("=" * 80)
    print("ANALYZING FIRST CLUSTER")
    print("=" * 80)
    print()
    
    # Build cluster data
    nucleus_entities = []
    all_actors = {}
    all_actions = []
    
    for article in cluster:
        if not isinstance(article, dict):
            continue
        
        nucleus = article.get('nucleus_entity')
        if nucleus:
            nucleus_entities.append(nucleus)
        
        actors = article.get('actors', [])
        actor_salience = article.get('actor_salience', {})
        
        if isinstance(actors, list):
            for actor in actors:
                salience = actor_salience.get(actor, 3) if isinstance(actor_salience, dict) else 3
                all_actors[actor] = max(all_actors.get(actor, 0), salience)
        
        narrative_summary = article.get('narrative_summary', {})
        if isinstance(narrative_summary, dict):
            actions = narrative_summary.get('actions', [])
            if isinstance(actions, list):
                all_actions.extend(actions)
    
    # Determine primary nucleus
    nucleus_counts = Counter(nucleus_entities)
    primary_nucleus = nucleus_counts.most_common(1)[0][0] if nucleus_counts else ''
    
    # Build cluster dict
    cluster_data = {
        'nucleus_entity': primary_nucleus,
        'actors': all_actors,
        'actions': list(set(all_actions))[:5]
    }
    
    # Compute fingerprint
    cluster_fingerprint = compute_narrative_fingerprint(cluster_data)
    
    print("CLUSTER FINGERPRINT:")
    print(f"  nucleus_entity: '{cluster_fingerprint.get('nucleus_entity')}'")
    print(f"  top_actors: {cluster_fingerprint.get('top_actors')}")
    print(f"  key_actions: {cluster_fingerprint.get('key_actions')}")
    print()
    
    # Get existing narratives
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
    
    # Test similarity with each candidate
    print("=" * 80)
    print("SIMILARITY CALCULATIONS")
    print("=" * 80)
    print()
    
    for i, candidate in enumerate(candidates, 1):
        print(f"CANDIDATE #{i}: {candidate.get('title')}")
        print("-" * 80)
        
        candidate_fingerprint = candidate.get('fingerprint')
        if not candidate_fingerprint:
            candidate_fingerprint = {
                'nucleus_entity': candidate.get('theme', ''),
                'top_actors': candidate.get('entities', []),
                'key_actions': []
            }
        
        print(f"CANDIDATE FINGERPRINT:")
        print(f"  nucleus_entity: '{candidate_fingerprint.get('nucleus_entity')}'")
        print(f"  top_actors: {candidate_fingerprint.get('top_actors')}")
        print(f"  key_actions: {candidate_fingerprint.get('key_actions')}")
        print()
        
        # Manual calculation
        nucleus1 = cluster_fingerprint.get('nucleus_entity', '')
        nucleus2 = candidate_fingerprint.get('nucleus_entity', '')
        
        actors1 = set(cluster_fingerprint.get('top_actors', []))
        actors2 = set(candidate_fingerprint.get('top_actors', []))
        
        actions1 = set(cluster_fingerprint.get('key_actions', []))
        actions2 = set(candidate_fingerprint.get('key_actions', []))
        
        print(f"COMPARISON:")
        print(f"  Cluster nucleus: '{nucleus1}'")
        print(f"  Candidate nucleus: '{nucleus2}'")
        print(f"  Nucleus match: {nucleus1 == nucleus2}")
        print()
        
        print(f"  Cluster actors: {actors1}")
        print(f"  Candidate actors: {actors2}")
        print(f"  Actor intersection: {actors1 & actors2}")
        print(f"  Actor union: {actors1 | actors2}")
        if actors1 or actors2:
            actor_overlap = len(actors1 & actors2)
            actor_union = len(actors1 | actors2)
            actor_score = actor_overlap / actor_union if actor_union > 0 else 0.0
            print(f"  Actor overlap score: {actor_score:.3f}")
        print()
        
        print(f"  Cluster actions: {actions1}")
        print(f"  Candidate actions: {actions2}")
        print(f"  Action intersection: {actions1 & actions2}")
        if actions1 or actions2:
            action_overlap = len(actions1 & actions2)
            action_union = len(actions1 | actions2)
            action_score = action_overlap / action_union if action_union > 0 else 0.0
            print(f"  Action overlap score: {action_score:.3f}")
        print()
        
        # Calculate similarity using function
        similarity = calculate_fingerprint_similarity(cluster_fingerprint, candidate_fingerprint)
        print(f"FINAL SIMILARITY SCORE: {similarity:.3f}")
        print()
        print()


if __name__ == "__main__":
    asyncio.run(debug_similarity())
