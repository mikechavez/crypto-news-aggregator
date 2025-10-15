"""
Narrative clustering service with salience-aware detection.

This service identifies narratives by:
- Extracting narrative elements (actors, tensions, nucleus entity) from articles
- Clustering articles by nucleus entity and weighted actor/tension overlap
- Merging shallow single-article narratives into substantial clusters
- Generating AI-powered narrative summaries
- Tracking narrative lifecycle (emerging, hot, mature, declining)

Supports both:
- NEW: Salience-based clustering (default) - uses nucleus entity and actor salience
- OLD: Theme-based clustering (fallback) - uses predefined theme categories
"""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from math import exp
from itertools import combinations
from collections import defaultdict, Counter

from ..db.mongodb import mongo_manager
from ..llm.factory import get_llm_provider
from ..db.operations.narratives import upsert_narrative
from .narrative_themes import (
    backfill_themes_for_recent_articles,
    get_articles_by_theme,
    generate_narrative_from_theme,
    backfill_narratives_for_recent_articles,
    cluster_by_narrative_salience,
    generate_narrative_from_cluster,
    merge_shallow_narratives,
    calculate_fingerprint_similarity,
    compute_narrative_fingerprint,
    THEME_CATEGORIES
)

logger = logging.getLogger(__name__)


# Narrative clustering configuration
SALIENCE_CLUSTERING_CONFIG = {
    'min_cluster_size': 3,           # Minimum articles per narrative
    'link_strength_threshold': 0.8,  # Threshold for clustering (0.0-2.0+)
    'core_actor_salience': 4,        # Minimum salience for "core" actor
    'merge_similarity_threshold': 0.5, # Minimum similarity to merge shallow narratives
    'ubiquitous_entities': {'Bitcoin', 'Ethereum', 'crypto', 'blockchain'},
}


def calculate_momentum(article_dates: List[datetime]) -> str:
    """
    Calculate momentum based on velocity change over time.
    
    Args:
        article_dates: Sorted list of article publication dates
    
    Returns:
        Momentum: "growing", "declining", "stable", or "unknown"
    """
    if len(article_dates) < 3:
        return "unknown"
    
    # Split articles into older and recent halves
    midpoint = len(article_dates) // 2
    recent_articles = article_dates[midpoint:]
    older_articles = article_dates[:midpoint]
    
    # Calculate time spans (in hours), minimum 1 hour to avoid division issues
    recent_span = (recent_articles[-1] - recent_articles[0]).total_seconds() / 3600
    older_span = (older_articles[-1] - older_articles[0]).total_seconds() / 3600
    
    # Use minimum of 1 hour to avoid division by zero or extreme values
    recent_span = max(1.0, recent_span)
    older_span = max(1.0, older_span)
    
    # Calculate velocities (articles per hour)
    recent_velocity = len(recent_articles) / recent_span
    older_velocity = len(older_articles) / older_span
    
    # Calculate velocity change ratio
    velocity_change = recent_velocity / older_velocity if older_velocity > 0 else 1
    
    # Determine momentum based on velocity change
    if velocity_change >= 1.3:
        return "growing"
    elif velocity_change <= 0.7:
        return "declining"
    else:
        return "stable"


def determine_lifecycle_state(
    article_count: int,
    mention_velocity: float,
    first_seen: datetime,
    last_updated: datetime
) -> str:
    """
    Determine the lifecycle state of a narrative based on activity patterns.
    
    Args:
        article_count: Current number of articles in narrative
        mention_velocity: Articles per day rate
        first_seen: When the narrative was first detected
        last_updated: When the narrative was last updated with new articles
    
    Returns:
        Lifecycle state: emerging, rising, hot, cooling, or dormant
    """
    # Calculate days since last update
    now = datetime.now(timezone.utc)
    days_since_update = (now - last_updated).total_seconds() / 86400  # 86400 seconds in a day
    
    # Check for dormant or cooling states first (based on recency)
    if days_since_update >= 7:
        return 'dormant'
    elif days_since_update >= 3:
        return 'cooling'
    
    # Check for hot state (high activity)
    if article_count >= 7 or mention_velocity >= 3.0:
        return 'hot'
    
    # Check for rising state (moderate velocity, not yet hot)
    if mention_velocity >= 1.5 and article_count < 7:
        return 'rising'
    
    # Default to emerging for new/small narratives
    if article_count < 4:
        return 'emerging'
    
    # Fallback for edge cases (4-6 articles, low velocity, recent)
    return 'emerging'


def update_lifecycle_history(
    narrative: Dict[str, Any],
    lifecycle_state: str,
    article_count: int,
    mention_velocity: float
) -> List[Dict[str, Any]]:
    """
    Update lifecycle history by tracking state transitions.
    
    Checks if the current lifecycle_state differs from the last entry in
    lifecycle_history. If different or if lifecycle_history doesn't exist,
    appends a new entry with state, timestamp, article_count, and mention_velocity.
    
    Args:
        narrative: Narrative dict (may or may not have lifecycle_history)
        lifecycle_state: Current lifecycle state to track
        article_count: Current number of articles in narrative
        mention_velocity: Current articles per day rate
    
    Returns:
        Updated lifecycle_history array
    
    Example:
        >>> narrative = {'lifecycle_history': [{'state': 'emerging', 'timestamp': ...}]}
        >>> history = update_lifecycle_history(narrative, 'rising', 5, 2.3)
        >>> len(history)
        2
    """
    # Get existing lifecycle_history or initialize as empty array
    lifecycle_history = narrative.get('lifecycle_history', [])
    
    # Check if we need to add a new entry
    should_add_entry = False
    
    if not lifecycle_history:
        # No history exists, add first entry
        should_add_entry = True
    else:
        # Check if state differs from last entry
        last_entry = lifecycle_history[-1]
        last_state = last_entry.get('state')
        
        if last_state != lifecycle_state:
            should_add_entry = True
    
    # Add new entry if needed
    if should_add_entry:
        new_entry = {
            'state': lifecycle_state,
            'timestamp': datetime.now(timezone.utc),
            'article_count': article_count,
            'mention_velocity': round(mention_velocity, 2)
        }
        lifecycle_history.append(new_entry)
        
        logger.debug(
            f"Added lifecycle history entry: {lifecycle_state} "
            f"(articles: {article_count}, velocity: {mention_velocity:.2f})"
        )
    
    return lifecycle_history


def determine_lifecycle_stage(
    article_count: int,
    mention_velocity: float,
    momentum: str = "unknown"
) -> str:
    """
    Determine the lifecycle stage of a narrative with momentum awareness.
    
    DEPRECATED: Use determine_lifecycle_state instead for new code.
    
    Args:
        article_count: Current number of articles in narrative
        mention_velocity: Articles per day rate
        momentum: Momentum indicator (growing, declining, stable, unknown)
    
    Returns:
        Lifecycle stage: emerging, rising, hot, heating, mature, cooling, or declining
    """
    # Calculate base lifecycle with adjusted thresholds
    if mention_velocity >= 5:
        lifecycle = "mature"
    elif mention_velocity >= 1.5:
        lifecycle = "hot"
    elif article_count >= 5:
        lifecycle = "hot"
    else:
        lifecycle = "emerging"
    
    # Integrate momentum to refine lifecycle
    if lifecycle == "mature" and momentum == "declining":
        return "cooling"
    elif lifecycle == "hot" and momentum == "growing":
        return "heating"
    elif lifecycle == "emerging" and momentum == "growing":
        return "rising"
    
    return lifecycle


async def find_matching_narrative(
    fingerprint: Dict[str, Any],
    within_days: int = 14
) -> Optional[Dict[str, Any]]:
    """
    Find an existing narrative that matches the given fingerprint.
    
    Searches for narratives within a time window and calculates similarity
    using fingerprint comparison. Returns the best matching narrative if
    similarity exceeds threshold.
    
    Args:
        fingerprint: Narrative fingerprint dict with nucleus_entity, top_actors, key_actions
        within_days: Time window in days to search for matching narratives (default 14)
    
    Returns:
        Best matching narrative dict if similarity > 0.6, otherwise None
    
    Example:
        >>> fingerprint = {
        ...     'nucleus_entity': 'SEC',
        ...     'top_actors': ['SEC', 'Binance', 'Coinbase'],
        ...     'key_actions': ['filed lawsuit', 'regulatory enforcement']
        ... }
        >>> narrative = await find_matching_narrative(fingerprint, within_days=14)
        >>> if narrative:
        ...     print(f"Found matching narrative: {narrative['title']}")
    """
    try:
        db = await mongo_manager.get_async_database()
        narratives_collection = db.narratives
        
        # Calculate time window
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=within_days)
        
        # Query for active narratives within time window
        active_statuses = ['emerging', 'rising', 'hot', 'cooling', 'dormant']
        query = {
            'last_updated': {'$gte': cutoff_time},
            'status': {'$in': active_statuses}
        }
        
        cursor = narratives_collection.find(query)
        candidates = await cursor.to_list(length=None)
        
        if not candidates:
            logger.debug(f"No candidate narratives found within {within_days} days")
            return None
        
        logger.info(f"Evaluating {len(candidates)} candidate narratives for similarity")
        
        # Calculate similarity for each candidate
        best_match = None
        best_similarity = 0.0
        
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
            
            logger.debug(
                f"Narrative '{candidate.get('title', 'unknown')}' similarity: {similarity:.3f}"
            )
            
            # Track best match
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = candidate
        
        # Return best match if above threshold
        if best_similarity > 0.6:
            logger.info(
                f"Found matching narrative: '{best_match.get('title')}' "
                f"(similarity: {best_similarity:.3f})"
            )
            return best_match
        else:
            logger.info(
                f"No matching narrative found (best similarity: {best_similarity:.3f})"
            )
            return None
    
    except Exception as e:
        logger.exception(f"Error finding matching narrative: {e}")
        return None


async def extract_entities_from_articles(articles: List[Dict[str, Any]]) -> List[str]:
    """
    Extract all unique entities mentioned across a list of articles.
    
    Args:
        articles: List of article documents
    
    Returns:
        List of unique entity names
    """
    from bson import ObjectId
    
    db = await mongo_manager.get_async_database()
    entity_mentions_collection = db.entity_mentions
    
    entities = set()
    
    for article in articles:
        article_id = article.get("_id")
        
        # entity_mentions.article_id has mixed formats (ObjectId and string)
        # Query for both to handle legacy data
        cursor = entity_mentions_collection.find({
            "$or": [
                {"article_id": article_id},        # ObjectId format
                {"article_id": str(article_id)}    # String format
            ]
        })
        async for mention in cursor:
            entity = mention.get("entity")
            if entity:
                entities.add(entity)
    
    return list(entities)


async def detect_narratives(
    hours: int = 48,
    min_articles: int = 3,
    use_salience_clustering: bool = True
) -> List[Dict[str, Any]]:
    """
    Detect narratives using salience-aware clustering.
    
    Args:
        hours: Lookback window for articles
        min_articles: Minimum articles per narrative cluster
        use_salience_clustering: Use new salience-based system (vs old theme-based)
    
    Returns:
        List of narrative dicts with full structure including lifecycle tracking
    """
    try:
        if use_salience_clustering:
            # NEW: Use salience-aware clustering
            logger.info(f"Using salience-based narrative detection for last {hours} hours")
            
            # Backfill narrative data for recent articles if needed
            backfilled_count = await backfill_narratives_for_recent_articles(hours=hours)
            logger.info(f"Backfilled narrative data for {backfilled_count} articles")
            
            # Get recent articles with narrative data
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            db = await mongo_manager.get_async_database()
            articles_collection = db.articles
            
            cursor = articles_collection.find({
                "published_at": {"$gte": cutoff_time},
                "narrative_summary": {"$exists": True}  # Has narrative data
            })
            
            articles = await cursor.to_list(length=None)
            logger.info(f"Found {len(articles)} articles with narrative data in last {hours}h")
            
            if not articles:
                logger.warning("No articles with narrative data found")
                return []
            
            # Cluster articles by nucleus entity and weighted overlap
            clusters = await cluster_by_narrative_salience(
                articles,
                min_cluster_size=min_articles
            )
            
            logger.info(f"Created {len(clusters)} narrative clusters")
            
            # Process each cluster: compute fingerprint, check for matches, merge or create
            saved_narratives = []
            matched_count = 0
            created_count = 0
            
            for cluster in clusters:
                # Build cluster data dict for fingerprint computation
                # Aggregate nucleus entities, actors, and actions from cluster articles
                nucleus_entities = []
                all_actors = {}
                all_actions = []
                
                for article in cluster:
                    # Skip if article is not a dict (defensive programming)
                    if not isinstance(article, dict):
                        logger.warning(f"Skipping non-dict article in cluster: {type(article)}")
                        continue
                    
                    nucleus = article.get('nucleus_entity')
                    if nucleus:
                        nucleus_entities.append(nucleus)
                    
                    # Aggregate actors with salience
                    actors = article.get('actors', [])
                    actor_salience = article.get('actor_salience', {})
                    
                    # Handle actors as list or dict
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
                    'actions': list(set(all_actions))[:5]  # Unique actions, top 5
                }
                
                # Compute fingerprint from cluster data
                fingerprint = compute_narrative_fingerprint(cluster_data)
                logger.debug(f"Computed fingerprint for cluster with nucleus_entity: {fingerprint.get('nucleus_entity')}")
                
                # Check for matching existing narrative
                matching_narrative = await find_matching_narrative(fingerprint, within_days=14)
                
                if matching_narrative:
                    # Update existing narrative by appending new articles
                    matched_count += 1
                    narrative_id = str(matching_narrative['_id'])
                    
                    # Get existing article_ids and append new ones from cluster
                    existing_article_ids = set(matching_narrative.get('article_ids', []))
                    # Extract article_ids from cluster articles
                    new_article_ids = set(str(article.get('_id')) for article in cluster if isinstance(article, dict))
                    combined_article_ids = list(existing_article_ids | new_article_ids)
                    
                    # Calculate updated metrics for lifecycle_state
                    updated_article_count = len(combined_article_ids)
                    first_seen = matching_narrative.get('first_seen', datetime.now(timezone.utc))
                    last_updated = datetime.now(timezone.utc)
                    
                    # Calculate mention velocity based on time since first_seen
                    time_span = (last_updated - first_seen).total_seconds() / 86400  # days
                    mention_velocity = updated_article_count / time_span if time_span > 0 else 0
                    
                    # Calculate lifecycle_state for updated narrative
                    lifecycle_state = determine_lifecycle_state(
                        updated_article_count, mention_velocity, first_seen, last_updated
                    )
                    
                    # Update lifecycle history
                    lifecycle_history = update_lifecycle_history(
                        matching_narrative,
                        lifecycle_state,
                        updated_article_count,
                        mention_velocity
                    )
                    
                    # Update the narrative in database
                    db = await mongo_manager.get_async_database()
                    narratives_collection = db.narratives
                    
                    update_data = {
                        'article_ids': combined_article_ids,
                        'article_count': updated_article_count,
                        'last_updated': last_updated,
                        'mention_velocity': round(mention_velocity, 2),
                        'lifecycle_state': lifecycle_state,
                        'lifecycle_history': lifecycle_history,
                        'needs_summary_update': True,
                        'fingerprint': fingerprint
                    }
                    
                    await narratives_collection.update_one(
                        {'_id': matching_narrative['_id']},
                        {'$set': update_data}
                    )
                    
                    logger.info(
                        f"Merged {len(new_article_ids)} new articles into existing narrative: "
                        f"'{matching_narrative.get('title')}' (ID: {narrative_id})"
                    )
                    
                    # Add to saved narratives for return value
                    matching_narrative.update(update_data)
                    saved_narratives.append(matching_narrative)
                    
                else:
                    # No match found - create new narrative
                    created_count += 1
                    narrative = await generate_narrative_from_cluster(cluster)
                    
                    if not narrative:
                        logger.warning(f"Failed to generate narrative for cluster with nucleus: {cluster.get('nucleus_entity')}")
                        continue
                    
                    # Add fingerprint to narrative data
                    narrative['fingerprint'] = fingerprint
                    narrative['needs_summary_update'] = False  # Fresh summary, no update needed
                    
                    narrative_data = narrative
                    # Calculate mention velocity (articles per day)
                    article_count = narrative_data.get("article_count", 0)
                    time_span_days = hours / 24.0
                    mention_velocity = article_count / time_span_days if time_span_days > 0 else 0
                    
                    # Calculate momentum from article dates
                    # Get articles for this narrative to extract dates
                    article_ids = narrative_data.get("article_ids", [])
                    article_dates = []
                    for article in articles:
                        if str(article.get("_id")) in article_ids:
                            pub_date = article.get("published_at")
                            if pub_date:
                                article_dates.append(pub_date)
                    
                    # Sort dates and calculate momentum
                    article_dates.sort()
                    momentum = calculate_momentum(article_dates)
                    
                    # Calculate recency score (0-1, higher = more recent)
                    newest_article = article_dates[-1] if article_dates else None
                    if newest_article:
                        hours_since_last_update = (datetime.now(timezone.utc) - newest_article).total_seconds() / 3600
                        recency_score = exp(-hours_since_last_update / 24)  # 24h half-life
                    else:
                        recency_score = 0.0
                    
                    # Determine lifecycle stage with momentum awareness (legacy)
                    lifecycle = determine_lifecycle_stage(article_count, mention_velocity, momentum)
                    
                    # Determine lifecycle state (new approach)
                    first_seen = datetime.now(timezone.utc)
                    last_updated = datetime.now(timezone.utc)
                    lifecycle_state = determine_lifecycle_state(
                        article_count, mention_velocity, first_seen, last_updated
                    )
                    
                    # Initialize lifecycle history for new narrative
                    lifecycle_history = update_lifecycle_history(
                        {},  # Empty dict for new narrative
                        lifecycle_state,
                        article_count,
                        mention_velocity
                    )
                    
                    # Use nucleus_entity as theme for database compatibility
                    theme = narrative_data.get("nucleus_entity", "unknown")
                    
                    # Enrich narrative_data with computed fields for return value
                    narrative_data["theme"] = theme
                    narrative_data["entities"] = narrative_data.get("actors", [])[:10]
                    narrative_data["mention_velocity"] = round(mention_velocity, 2)
                    narrative_data["lifecycle"] = lifecycle
                    narrative_data["lifecycle_state"] = lifecycle_state
                    narrative_data["lifecycle_history"] = lifecycle_history
                    narrative_data["momentum"] = momentum
                    narrative_data["recency_score"] = round(recency_score, 3)
                    
                    try:
                        # Save new narrative to database with fingerprint
                        db = await mongo_manager.get_async_database()
                        narratives_collection = db.narratives
                        
                        narrative_doc = {
                            "theme": theme,
                            "title": narrative_data["title"],
                            "summary": narrative_data["summary"],
                            "entities": narrative_data.get("actors", [])[:10],
                            "article_ids": narrative_data["article_ids"],
                            "article_count": article_count,
                            "mention_velocity": round(mention_velocity, 2),
                            "lifecycle": lifecycle,
                            "lifecycle_state": lifecycle_state,
                            "lifecycle_history": lifecycle_history,
                            "momentum": momentum,
                            "recency_score": round(recency_score, 3),
                            "entity_relationships": narrative_data.get("entity_relationships", []),
                            "fingerprint": fingerprint,
                            "needs_summary_update": False,
                            "first_seen": first_seen,
                            "last_updated": last_updated,
                            "timeline_data": [],
                            "peak_activity": {
                                "date": datetime.now(timezone.utc).date().isoformat(),
                                "article_count": article_count,
                                "velocity": round(mention_velocity, 2)
                            },
                            "days_active": 1
                        }
                        
                        result = await narratives_collection.insert_one(narrative_doc)
                        narrative_id = str(result.inserted_id)
                        
                        logger.info(f"Created new narrative {narrative_id}: {narrative_data['title']}")
                        saved_narratives.append(narrative_data)
                    except Exception as e:
                        logger.exception(f"Failed to save narrative '{narrative_data.get('title')}': {e}")
            
            logger.info(
                f"Narrative detection complete: {matched_count} merged into existing, "
                f"{created_count} newly created, {len(saved_narratives)} total"
            )
            return saved_narratives
        
        else:
            # OLD: Use theme-based clustering (fallback)
            logger.info(f"Using theme-based narrative detection for last {hours} hours")
            
            # Step 1: Backfill themes for recent articles that don't have them
            backfilled = await backfill_themes_for_recent_articles(hours=hours, limit=100)
            logger.info(f"Backfilled themes for {backfilled} articles")
            
            # Step 2: Get existing narratives for comparison (lifecycle tracking)
            db = await mongo_manager.get_async_database()
            narratives_collection = db.narratives
            existing_narratives = {}
            async for narrative in narratives_collection.find({}):
                theme = narrative.get("theme")
                if theme:
                    existing_narratives[theme] = narrative
            
            # Step 3: For each theme, find articles and create narratives
            narratives = []
            
            for theme in THEME_CATEGORIES:
                # Get articles for this theme
                articles = await get_articles_by_theme(theme, hours=hours, min_articles=min_articles)
                
                if not articles:
                    continue
                
                logger.info(f"Found {len(articles)} articles for theme '{theme}'")
                
                # Extract entities from these articles
                entities = await extract_entities_from_articles(articles)
                
                # Generate narrative summary
                narrative_content = await generate_narrative_from_theme(theme, articles)
                
                if not narrative_content:
                    logger.warning(f"Failed to generate narrative for theme '{theme}'")
                    continue
                
                # Calculate mention velocity (articles per day)
                article_count = len(articles)
                time_span_days = hours / 24.0
                mention_velocity = article_count / time_span_days if time_span_days > 0 else 0
                
                # Get first_seen for lifecycle tracking
                first_seen = datetime.now(timezone.utc)
                if theme in existing_narratives:
                    first_seen = existing_narratives[theme].get("first_seen", first_seen)
                
                # Calculate momentum from article dates
                article_dates = sorted([a.get("published_at") for a in articles if a.get("published_at")])
                momentum = calculate_momentum(article_dates)
                
                # Calculate recency score (0-1, higher = more recent)
                newest_article = article_dates[-1] if article_dates else None
                if newest_article:
                    hours_since_last_update = (datetime.now(timezone.utc) - newest_article).total_seconds() / 3600
                    recency_score = exp(-hours_since_last_update / 24)  # 24h half-life
                else:
                    recency_score = 0.0
                
                # Determine lifecycle stage with momentum awareness (legacy)
                lifecycle = determine_lifecycle_stage(article_count, mention_velocity, momentum)
                
                # Determine lifecycle state (new approach)
                last_updated = datetime.now(timezone.utc)
                lifecycle_state = determine_lifecycle_state(
                    article_count, mention_velocity, first_seen, last_updated
                )
                
                # Update lifecycle history (check existing narrative for history)
                existing_narrative = existing_narratives.get(theme, {})
                lifecycle_history = update_lifecycle_history(
                    existing_narrative,
                    lifecycle_state,
                    article_count,
                    mention_velocity
                )
                
                # Build narrative document
                narrative = {
                    "theme": theme,
                    "title": narrative_content["title"],
                    "summary": narrative_content["summary"],
                    "entities": entities[:10],  # Limit to top 10 entities
                    "article_ids": [str(a["_id"]) for a in articles],
                    "first_seen": first_seen,
                    "last_updated": last_updated,
                    "article_count": article_count,
                    "mention_velocity": round(mention_velocity, 2),
                    "lifecycle": lifecycle,
                    "lifecycle_state": lifecycle_state,
                    "lifecycle_history": lifecycle_history,
                    "momentum": momentum,
                    "recency_score": round(recency_score, 3)
                }
                
                narratives.append(narrative)
                logger.info(f"Created narrative for theme '{theme}': {article_count} articles, lifecycle={lifecycle}, lifecycle_state={lifecycle_state}, momentum={momentum}")
                
                # Save narrative to database
                try:
                    narrative_id = await upsert_narrative(
                        theme=narrative["theme"],
                        title=narrative["title"],
                        summary=narrative["summary"],
                        entities=narrative["entities"],
                        article_ids=narrative["article_ids"],
                        article_count=narrative["article_count"],
                        mention_velocity=narrative["mention_velocity"],
                        lifecycle=narrative["lifecycle"],
                        momentum=narrative["momentum"],
                        recency_score=narrative["recency_score"],
                        first_seen=narrative["first_seen"],
                        lifecycle_state=narrative["lifecycle_state"],
                        lifecycle_history=narrative["lifecycle_history"]
                    )
                    logger.info(f"Saved narrative {narrative_id} to database")
                except Exception as e:
                    logger.exception(f"Failed to save narrative for theme '{theme}': {e}")
            
            logger.info(f"Generated {len(narratives)} theme-based narratives")
            return narratives
    
    except Exception as e:
        logger.exception(f"Error in detect_narratives: {e}")
        return []
