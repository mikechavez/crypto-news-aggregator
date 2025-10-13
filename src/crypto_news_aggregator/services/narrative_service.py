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
from collections import defaultdict

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


def determine_lifecycle_stage(
    article_count: int,
    mention_velocity: float,
    momentum: str = "unknown"
) -> str:
    """
    Determine the lifecycle stage of a narrative with momentum awareness.
    
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
            
            # Generate narrative for each cluster
            narratives = []
            for cluster in clusters:
                narrative = await generate_narrative_from_cluster(cluster)
                if narrative:
                    narratives.append(narrative)
            
            logger.info(f"Generated {len(narratives)} narratives before merging")
            
            # Merge shallow narratives
            narratives = await merge_shallow_narratives(narratives)
            
            logger.info(f"After merging: {len(narratives)} final narratives")
            
            # Save narratives to database
            saved_narratives = []
            for narrative_data in narratives:
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
                
                # Determine lifecycle stage with momentum awareness
                lifecycle = determine_lifecycle_stage(article_count, mention_velocity, momentum)
                
                # Use nucleus_entity as theme for database compatibility
                theme = narrative_data.get("nucleus_entity", "unknown")
                
                # Enrich narrative_data with computed fields for return value
                narrative_data["theme"] = theme
                narrative_data["entities"] = narrative_data.get("actors", [])[:10]
                narrative_data["mention_velocity"] = round(mention_velocity, 2)
                narrative_data["lifecycle"] = lifecycle
                narrative_data["momentum"] = momentum
                narrative_data["recency_score"] = round(recency_score, 3)
                
                try:
                    narrative_id = await upsert_narrative(
                        theme=theme,
                        title=narrative_data["title"],
                        summary=narrative_data["summary"],
                        entities=narrative_data.get("actors", [])[:10],
                        article_ids=narrative_data["article_ids"],
                        article_count=article_count,
                        mention_velocity=round(mention_velocity, 2),
                        lifecycle=lifecycle,
                        momentum=momentum,
                        recency_score=round(recency_score, 3),
                        entity_relationships=narrative_data.get("entity_relationships", []),
                        first_seen=None  # Will use current time or existing
                    )
                    logger.info(f"Saved narrative {narrative_id} to database: {narrative_data['title']}")
                    saved_narratives.append(narrative_data)
                except Exception as e:
                    logger.exception(f"Failed to save narrative '{narrative_data.get('title')}': {e}")
            
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
                
                # Determine lifecycle stage with momentum awareness
                lifecycle = determine_lifecycle_stage(article_count, mention_velocity, momentum)
                
                # Build narrative document
                narrative = {
                    "theme": theme,
                    "title": narrative_content["title"],
                    "summary": narrative_content["summary"],
                    "entities": entities[:10],  # Limit to top 10 entities
                    "article_ids": [str(a["_id"]) for a in articles],
                    "first_seen": first_seen,
                    "last_updated": datetime.now(timezone.utc),
                    "article_count": article_count,
                    "mention_velocity": round(mention_velocity, 2),
                    "lifecycle": lifecycle,
                    "momentum": momentum,
                    "recency_score": round(recency_score, 3)
                }
                
                narratives.append(narrative)
                logger.info(f"Created narrative for theme '{theme}': {article_count} articles, lifecycle={lifecycle}, momentum={momentum}")
                
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
                        first_seen=narrative["first_seen"]
                    )
                    logger.info(f"Saved narrative {narrative_id} to database")
                except Exception as e:
                    logger.exception(f"Failed to save narrative for theme '{theme}': {e}")
            
            logger.info(f"Generated {len(narratives)} theme-based narratives")
            return narratives
    
    except Exception as e:
        logger.exception(f"Error in detect_narratives: {e}")
        return []
