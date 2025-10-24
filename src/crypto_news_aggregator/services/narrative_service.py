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

# Blacklist of entities that should not become narrative nucleus entities
# These are typically advertising/promotional content or irrelevant entities
BLACKLIST_ENTITIES = {'Benzinga', 'Sarah Edwards'}


def calculate_recent_velocity(article_dates: List[datetime], lookback_days: int = 7) -> float:
    """
    Calculate article velocity based on recent activity (last N days).
    
    This provides a more accurate measure of current narrative momentum
    compared to dividing total articles by total time span.
    
    Args:
        article_dates: List of article publication dates
        lookback_days: Number of days to look back for velocity calculation (default: 7)
    
    Returns:
        Articles per day over the lookback period
    """
    if not article_dates:
        return 0.0
    
    # Get current time
    now = datetime.now(timezone.utc)
    
    # Filter articles from the last N days
    cutoff_date = now - timedelta(days=lookback_days)
    recent_articles = [d for d in article_dates if d >= cutoff_date]
    
    # Debug logging
    logger.info(f"[VELOCITY DEBUG] ========== VELOCITY CALCULATION START ==========")
    logger.info(f"[VELOCITY DEBUG] Total articles: {len(article_dates)}")
    logger.info(f"[VELOCITY DEBUG] Current time (now): {now} (UTC)")
    logger.info(f"[VELOCITY DEBUG] Cutoff date ({lookback_days} days ago): {cutoff_date} (UTC)")
    logger.info(f"[VELOCITY DEBUG] Time delta calculation: ({now} - {cutoff_date}).total_seconds() / 86400")
    logger.info(f"[VELOCITY DEBUG] Time delta result: {(now - cutoff_date).total_seconds() / 86400:.2f} days")
    logger.info(f"[VELOCITY DEBUG] Time delta in seconds: {(now - cutoff_date).total_seconds():.0f} seconds")
    
    # Log all article dates for debugging
    if article_dates:
        logger.info(f"[VELOCITY DEBUG] All article dates (sorted):")
        for i, date in enumerate(sorted(article_dates, reverse=True)):
            in_window = "✓ IN WINDOW" if date >= cutoff_date else "✗ EXCLUDED"
            logger.info(f"[VELOCITY DEBUG]   [{i+1}] {date} {in_window}")
    
    logger.info(f"[VELOCITY DEBUG] Articles within window: {len(recent_articles)}")
    if recent_articles:
        oldest = min(recent_articles)
        newest = max(recent_articles)
        logger.info(f"[VELOCITY DEBUG] Oldest article in window: {oldest}")
        logger.info(f"[VELOCITY DEBUG] Newest article in window: {newest}")
        logger.info(f"[VELOCITY DEBUG] Article span: {(newest - oldest).total_seconds() / 86400:.2f} days")
    
    logger.info(f"[VELOCITY DEBUG] Final calculation: {len(recent_articles)} articles / {lookback_days} days")
    logger.info(f"[VELOCITY DEBUG] Result: {len(recent_articles) / lookback_days:.2f} articles/day")
    logger.info(f"[VELOCITY DEBUG] ========== VELOCITY CALCULATION END ==========")
    
    # If no recent articles, return 0
    if not recent_articles:
        return 0.0
    
    # Calculate velocity: articles / lookback period
    # Always use the full lookback_days window for consistent velocity measurement
    return len(recent_articles) / lookback_days


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
    last_updated: datetime,
    previous_state: Optional[str] = None
) -> str:
    """
    Determine the lifecycle state of a narrative based on activity patterns.
    
    Args:
        article_count: Current number of articles in narrative
        mention_velocity: Articles per day rate
        first_seen: When the narrative was first detected
        last_updated: When the narrative was last updated with new articles
        previous_state: Previous lifecycle state from lifecycle_history (optional)
    
    Returns:
        Lifecycle state: emerging, rising, hot, cooling, dormant, echo, or reactivated
    """
    # Calculate days since last update
    now = datetime.now(timezone.utc)
    days_since_update = (now - last_updated).total_seconds() / 86400  # 86400 seconds in a day
    
    # Calculate recent activity (last 24h and 48h)
    cutoff_24h = now - timedelta(hours=24)
    cutoff_48h = now - timedelta(hours=48)
    
    # Estimate articles in last 24h and 48h based on velocity
    # This is an approximation; in practice, you'd query actual article timestamps
    articles_last_24h = mention_velocity * 1.0  # velocity is articles/day
    articles_last_48h = mention_velocity * 2.0
    
    # Check for reactivated state first: echo or dormant narrative with sustained activity (4+ articles in 48h)
    # This takes priority over echo to handle the transition properly
    if previous_state in ['echo', 'dormant'] and articles_last_48h >= 4:
        return 'reactivated'
    
    # Check for echo state: dormant narrative with light activity (1-3 articles in 24h) but NOT sustained (< 4 in 48h)
    # Echo represents a brief "pulse" of activity, not sustained reactivation
    if previous_state == 'dormant' and 1 <= articles_last_24h <= 3 and articles_last_48h < 4:
        return 'echo'
    
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
) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Update lifecycle history by tracking state transitions and resurrection metrics.
    
    Checks if the current lifecycle_state differs from the last entry in
    lifecycle_history. If different or if lifecycle_history doesn't exist,
    appends a new entry with state, timestamp, article_count, and mention_velocity.
    
    When transitioning to 'reactivated' state, also tracks resurrection metrics:
    - reawakening_count: Number of times narrative has been reactivated
    - reawakened_from: Timestamp when narrative went dormant
    - resurrection_velocity: Articles per day in last 48 hours
    
    Args:
        narrative: Narrative dict (may or may not have lifecycle_history)
        lifecycle_state: Current lifecycle state to track
        article_count: Current number of articles in narrative
        mention_velocity: Current articles per day rate
    
    Returns:
        Tuple of (updated lifecycle_history array, resurrection_fields dict)
    
    Example:
        >>> narrative = {'lifecycle_history': [{'state': 'emerging', 'timestamp': ...}]}
        >>> history, resurrection = update_lifecycle_history(narrative, 'rising', 5, 2.3)
        >>> len(history)
        2
    """
    # Get existing lifecycle_history or initialize as empty array
    lifecycle_history = narrative.get('lifecycle_history', [])
    
    # Initialize resurrection fields dict
    resurrection_fields = {}
    
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
            
            # Track resurrection if transitioning to 'reactivated' state
            if lifecycle_state == 'reactivated':
                # Find when narrative went dormant by looking backwards in history
                dormant_timestamp = None
                for entry in reversed(lifecycle_history):
                    if entry.get('state') in ['dormant', 'echo']:
                        dormant_timestamp = entry.get('timestamp')
                        break
                
                # Increment reawakening_count
                current_count = narrative.get('reawakening_count', 0)
                resurrection_fields['reawakening_count'] = current_count + 1
                
                # Set reawakened_from timestamp
                if dormant_timestamp:
                    resurrection_fields['reawakened_from'] = dormant_timestamp
                
                # Calculate resurrection_velocity (articles in last 48 hours / 2)
                # Use mention_velocity as proxy: velocity is articles/day, so multiply by 2 for 48h
                resurrection_velocity = mention_velocity * 2.0
                resurrection_fields['resurrection_velocity'] = round(resurrection_velocity, 2)
                
                logger.info(
                    f"Resurrection detected: count={resurrection_fields['reawakening_count']}, "
                    f"velocity={resurrection_fields['resurrection_velocity']:.2f}"
                )
    
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
    
    return lifecycle_history, resurrection_fields


def calculate_grace_period(mention_velocity: float) -> int:
    """
    Calculate adaptive grace period based on narrative velocity.
    
    Fast-burning narratives get shorter matching windows, slow-burn narratives
    get longer windows. This prevents stale matches for hot topics while allowing
    longer-term tracking of slower narratives.
    
    Args:
        mention_velocity: Articles per day rate
    
    Returns:
        Grace period in days (7-30 days)
    
    Examples:
        >>> calculate_grace_period(3.0)  # High velocity
        7
        >>> calculate_grace_period(1.0)  # Medium velocity
        14
        >>> calculate_grace_period(0.3)  # Low velocity
        30
    """
    # Formula: min(30, max(7, int(14 / max(mention_velocity, 0.5))))
    # - High velocity (>2 articles/day): 7 days
    # - Medium velocity (~1 article/day): 14 days
    # - Low velocity (<0.5 articles/day): 30 days
    return min(30, max(7, int(14 / max(mention_velocity, 0.5))))


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
    within_days: int = 14,
    cluster_velocity: Optional[float] = None
) -> Optional[Dict[str, Any]]:
    """
    Find an existing narrative that matches the given fingerprint.
    
    Searches for narratives within a time window and calculates similarity
    using fingerprint comparison. Uses adaptive thresholds based on narrative
    recency to allow easier continuation of recent stories while maintaining
    strict matching for older narratives.
    
    Adaptive Threshold Strategy:
    - Recent narratives (updated within 48h): 0.5 threshold
      Allows near-term continuations to merge more easily, accounting for
      natural variance in actor mentions and phrasing.
    - Older narratives (>48h): 0.6 threshold
      Maintains strict matching to prevent unrelated stories from merging.
    
    Args:
        fingerprint: Narrative fingerprint dict with nucleus_entity, top_actors, key_actions
        within_days: Time window in days to search for matching narratives (default 14)
        cluster_velocity: Optional cluster mention velocity for adaptive grace period
    
    Returns:
        Best matching narrative dict if similarity exceeds adaptive threshold, otherwise None
    
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
        # Calculate adaptive grace period if cluster velocity provided
        if cluster_velocity is not None:
            within_days = calculate_grace_period(cluster_velocity)
            logger.debug(
                f"Using adaptive grace period: {within_days} days "
                f"(velocity: {cluster_velocity:.2f} articles/day)"
            )
        
        db = await mongo_manager.get_async_database()
        narratives_collection = db.narratives
        
        # Calculate time window
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=within_days)
        
        # Query for active narratives within time window
        active_statuses = ['emerging', 'rising', 'hot', 'cooling', 'dormant', 'echo', 'reactivated']
        query = {
            'last_updated': {'$gte': cutoff_time},
            '$or': [
                {'status': {'$in': active_statuses}},
                {'lifecycle_state': {'$in': active_statuses}}
            ]
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
        best_threshold = 0.6  # Track which threshold applies to best match
        
        # Calculate 48-hour cutoff for adaptive threshold
        now = datetime.now(timezone.utc)
        recent_cutoff = now - timedelta(hours=48)
        
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
            
            # Determine adaptive threshold based on last_updated
            candidate_last_updated = candidate.get('last_updated')
            # Ensure timezone-aware for comparison
            if candidate_last_updated and candidate_last_updated.tzinfo is None:
                candidate_last_updated = candidate_last_updated.replace(tzinfo=timezone.utc)
            if candidate_last_updated and candidate_last_updated >= recent_cutoff:
                # Recent narrative (within 48h): use lower threshold (0.5)
                threshold = 0.5
                recency_label = "recent (48h)"
            else:
                # Older narrative: use stricter threshold (0.6)
                threshold = 0.6
                recency_label = "older (>48h)"
            
            logger.debug(
                f"Narrative '{candidate.get('title', 'unknown')}' similarity: {similarity:.3f} "
                f"(threshold: {threshold}, {recency_label})"
            )
            
            # Track best match that meets its threshold
            if similarity >= threshold and similarity > best_similarity:
                best_similarity = similarity
                best_match = candidate
                best_threshold = threshold
        
        # Return best match if found
        if best_match:
            logger.info(
                f"Found matching narrative: '{best_match.get('title')}' "
                f"(similarity: {best_similarity:.3f}, threshold: {best_threshold})"
            )
            return best_match
        else:
            logger.info(
                f"No matching narrative found - best similarity: {best_similarity:.3f} "
                f"(adaptive thresholds: 0.5 for recent, 0.6 for older)"
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
                
                # Check if nucleus_entity is blacklisted (advertising/promotional content)
                nucleus_entity = fingerprint.get('nucleus_entity', '')
                if nucleus_entity in BLACKLIST_ENTITIES:
                    logger.info(f"Skipping blacklisted nucleus_entity: {nucleus_entity}")
                    continue
                
                # Calculate cluster velocity for adaptive grace period
                cluster_article_count = len(cluster)
                # Use the detection window (hours) to estimate velocity
                cluster_time_span_days = hours / 24.0
                cluster_velocity = cluster_article_count / cluster_time_span_days if cluster_time_span_days > 0 else 0
                
                # Check for matching existing narrative with adaptive grace period
                matching_narrative = await find_matching_narrative(
                    fingerprint,
                    cluster_velocity=cluster_velocity
                )
                
                if matching_narrative:
                    # Update existing narrative by appending new articles
                    matched_count += 1
                    narrative_id = str(matching_narrative['_id'])
                    logger.debug(
                        f"Match found for cluster with nucleus '{primary_nucleus}': "
                        f"merging into narrative '{matching_narrative.get('title')}' (ID: {narrative_id})"
                    )
                    
                    # Get existing article_ids and append new ones from cluster
                    existing_article_ids = set(matching_narrative.get('article_ids', []))
                    # Extract article_ids from cluster articles
                    new_article_ids = set(str(article.get('_id')) for article in cluster if isinstance(article, dict))
                    combined_article_ids = list(existing_article_ids | new_article_ids)
                    
                    # Calculate updated metrics for lifecycle_state
                    updated_article_count = len(combined_article_ids)
                    first_seen = matching_narrative.get('first_seen', datetime.now(timezone.utc))
                    # Ensure first_seen is timezone-aware
                    if first_seen.tzinfo is None:
                        first_seen = first_seen.replace(tzinfo=timezone.utc)
                    last_updated = datetime.now(timezone.utc)
                    
                    # Calculate mention velocity based on recent activity (last 7 days)
                    # Fetch article dates for velocity calculation
                    article_dates = []
                    for article in articles:
                        if str(article.get('_id')) in combined_article_ids:
                            pub_date = article.get('published_at')
                            if pub_date:
                                # Ensure timezone-aware
                                if pub_date.tzinfo is None:
                                    pub_date = pub_date.replace(tzinfo=timezone.utc)
                                article_dates.append(pub_date)
                    
                    # Use recent velocity calculation (last 7 days) for more accurate current activity
                    mention_velocity = calculate_recent_velocity(article_dates, lookback_days=7)
                    
                    # Get previous state from lifecycle_history
                    lifecycle_history_existing = matching_narrative.get('lifecycle_history', [])
                    previous_state = lifecycle_history_existing[-1].get('state') if lifecycle_history_existing else None
                    
                    # Calculate lifecycle_state for updated narrative
                    lifecycle_state = determine_lifecycle_state(
                        updated_article_count, mention_velocity, first_seen, last_updated, previous_state
                    )
                    
                    # Update lifecycle history and get resurrection fields
                    lifecycle_history, resurrection_fields = update_lifecycle_history(
                        matching_narrative,
                        lifecycle_state,
                        updated_article_count,
                        mention_velocity
                    )
                    
                    # Use upsert_narrative to ensure timestamp validation
                    # Get theme from existing narrative or fingerprint
                    theme = matching_narrative.get('theme') or fingerprint.get('nucleus_entity', 'unknown')
                    title = matching_narrative.get('title', 'Unknown')
                    summary = matching_narrative.get('summary', '')
                    
                    try:
                        narrative_id = await upsert_narrative(
                            theme=theme,
                            title=title,
                            summary=summary,
                            entities=matching_narrative.get('entities', []),
                            article_ids=combined_article_ids,
                            article_count=updated_article_count,
                            mention_velocity=round(mention_velocity, 2),
                            lifecycle=matching_narrative.get('lifecycle', 'unknown'),
                            momentum=matching_narrative.get('momentum', 'unknown'),
                            recency_score=matching_narrative.get('recency_score', 0.0),
                            entity_relationships=matching_narrative.get('entity_relationships', []),
                            first_seen=first_seen,
                            lifecycle_state=lifecycle_state,
                            lifecycle_history=lifecycle_history,
                            reawakening_count=resurrection_fields.get('reawakening_count') if resurrection_fields else None,
                            reawakened_from=resurrection_fields.get('reawakened_from') if resurrection_fields else None,
                            resurrection_velocity=resurrection_fields.get('resurrection_velocity') if resurrection_fields else None
                        )
                        
                        logger.info(
                            f"Merged {len(new_article_ids)} new articles into existing narrative: "
                            f"'{title}' (ID: {narrative_id})"
                        )
                        
                        # Fetch updated narrative for return value
                        db = await mongo_manager.get_async_database()
                        updated_narrative = await db.narratives.find_one({'_id': matching_narrative['_id']})
                        if updated_narrative:
                            saved_narratives.append(updated_narrative)
                    except Exception as e:
                        logger.exception(f"Failed to update narrative '{theme}': {e}")
                        # Still add to saved narratives with local data
                        matching_narrative['article_ids'] = combined_article_ids
                        matching_narrative['article_count'] = updated_article_count
                        matching_narrative['last_updated'] = last_updated
                        matching_narrative['mention_velocity'] = round(mention_velocity, 2)
                        matching_narrative['lifecycle_state'] = lifecycle_state
                        matching_narrative['lifecycle_history'] = lifecycle_history
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
                    # Calculate mention velocity (articles per day) based on recent activity
                    article_count = narrative_data.get("article_count", 0)
                    
                    # Get articles for this narrative to extract dates
                    article_ids = narrative_data.get("article_ids", [])
                    article_dates = []
                    for article in articles:
                        if str(article.get("_id")) in article_ids:
                            pub_date = article.get("published_at")
                            if pub_date:
                                # Ensure timezone-aware
                                if pub_date.tzinfo is None:
                                    pub_date = pub_date.replace(tzinfo=timezone.utc)
                                article_dates.append(pub_date)
                    
                    # Use recent velocity calculation (last 7 days) for more accurate current activity
                    mention_velocity = calculate_recent_velocity(article_dates, lookback_days=7)
                    
                    # Calculate momentum from article dates
                    
                    # Sort dates and calculate momentum
                    article_dates.sort()
                    momentum = calculate_momentum(article_dates)
                    
                    # Calculate recency score (0-1, higher = more recent)
                    newest_article = article_dates[-1] if article_dates else None
                    if newest_article:
                        # Ensure newest_article is timezone-aware
                        if newest_article.tzinfo is None:
                            newest_article = newest_article.replace(tzinfo=timezone.utc)
                        hours_since_last_update = (datetime.now(timezone.utc) - newest_article).total_seconds() / 3600
                        recency_score = exp(-hours_since_last_update / 24)  # 24h half-life
                    else:
                        recency_score = 0.0
                    
                    # Determine lifecycle stage with momentum awareness (legacy)
                    lifecycle = determine_lifecycle_stage(article_count, mention_velocity, momentum)
                    
                    # Determine lifecycle state (new approach)
                    first_seen = datetime.now(timezone.utc)
                    last_updated = datetime.now(timezone.utc)
                    # No previous state for new narratives
                    lifecycle_state = determine_lifecycle_state(
                        article_count, mention_velocity, first_seen, last_updated, previous_state=None
                    )
                    
                    # Initialize lifecycle history for new narrative
                    lifecycle_history, resurrection_fields = update_lifecycle_history(
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
                            "nucleus_entity": narrative_data.get("nucleus_entity", ""),
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
                            "days_active": 1,
                            "status": lifecycle_state  # Add status field for matching logic
                        }
                        
                        # Validate fingerprint before insertion
                        if not fingerprint or not fingerprint.get('nucleus_entity'):
                            logger.error(f"Cannot create narrative - invalid fingerprint: {fingerprint}")
                            raise ValueError("Narrative fingerprint must have a valid nucleus_entity")
                        
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
                    # Ensure newest_article is timezone-aware
                    if newest_article.tzinfo is None:
                        newest_article = newest_article.replace(tzinfo=timezone.utc)
                    hours_since_last_update = (datetime.now(timezone.utc) - newest_article).total_seconds() / 3600
                    recency_score = exp(-hours_since_last_update / 24)  # 24h half-life
                else:
                    recency_score = 0.0
                
                # Determine lifecycle stage with momentum awareness (legacy)
                lifecycle = determine_lifecycle_stage(article_count, mention_velocity, momentum)
                
                # Get previous state from existing narrative's lifecycle_history
                existing_narrative = existing_narratives.get(theme, {})
                lifecycle_history_existing = existing_narrative.get('lifecycle_history', [])
                previous_state = lifecycle_history_existing[-1].get('state') if lifecycle_history_existing else None
                
                # Determine lifecycle state (new approach)
                last_updated = datetime.now(timezone.utc)
                lifecycle_state = determine_lifecycle_state(
                    article_count, mention_velocity, first_seen, last_updated, previous_state
                )
                
                # Update lifecycle history (check existing narrative for history)
                lifecycle_history, resurrection_fields = update_lifecycle_history(
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
                    # Prepare upsert arguments with resurrection fields if present
                    upsert_args = {
                        "theme": narrative["theme"],
                        "title": narrative["title"],
                        "summary": narrative["summary"],
                        "entities": narrative["entities"],
                        "article_ids": narrative["article_ids"],
                        "article_count": narrative["article_count"],
                        "mention_velocity": narrative["mention_velocity"],
                        "lifecycle": narrative["lifecycle"],
                        "momentum": narrative["momentum"],
                        "recency_score": narrative["recency_score"],
                        "first_seen": narrative["first_seen"],
                        "lifecycle_state": narrative["lifecycle_state"],
                        "lifecycle_history": narrative["lifecycle_history"]
                    }
                    
                    # Add resurrection fields if present
                    if resurrection_fields:
                        if "reawakening_count" in resurrection_fields:
                            upsert_args["reawakening_count"] = resurrection_fields["reawakening_count"]
                        if "reawakened_from" in resurrection_fields:
                            upsert_args["reawakened_from"] = resurrection_fields["reawakened_from"]
                        if "resurrection_velocity" in resurrection_fields:
                            upsert_args["resurrection_velocity"] = resurrection_fields["resurrection_velocity"]
                    
                    narrative_id = await upsert_narrative(**upsert_args)
                    logger.info(f"Saved narrative {narrative_id} to database")
                except Exception as e:
                    logger.exception(f"Failed to save narrative for theme '{theme}': {e}")
            
            logger.info(f"Generated {len(narratives)} theme-based narratives")
            return narratives
    
    except Exception as e:
        logger.exception(f"Error in detect_narratives: {e}")
        return []
