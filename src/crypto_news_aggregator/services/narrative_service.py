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
    'core_actor_salience': 4.5,      # Minimum salience for "core" actor
    'merge_similarity_threshold': 0.5, # Minimum similarity to merge shallow narratives
    'ubiquitous_entities': {'Bitcoin', 'Ethereum', 'crypto', 'blockchain'},
}


def determine_lifecycle_stage(
    article_count: int,
    mention_velocity: float,
    previous_count: Optional[int] = None
) -> str:
    """
    Determine the lifecycle stage of a narrative.
    
    Args:
        article_count: Current number of articles in narrative
        mention_velocity: Articles per day rate
        previous_count: Previous article count (for trend detection)
    
    Returns:
        Lifecycle stage: emerging, hot, mature, or declining
    """
    # Check if declining (requires previous count)
    if previous_count is not None and article_count < previous_count:
        return "declining"
    
    # Emerging: 2-4 articles
    if article_count <= 4:
        return "emerging"
    
    # Hot: 5-10 articles with high velocity
    if 5 <= article_count <= 10 and mention_velocity > 2.0:
        return "hot"
    
    # Mature: 10+ articles or sustained activity
    if article_count > 10 or mention_velocity > 3.0:
        return "mature"
    
    # Default to emerging
    return "emerging"


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
                
                # Determine lifecycle stage
                lifecycle = determine_lifecycle_stage(article_count, mention_velocity)
                
                # Use nucleus_entity as theme for database compatibility
                theme = narrative_data.get("nucleus_entity", "unknown")
                
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
                
                # Get previous count for lifecycle tracking
                previous_count = None
                first_seen = datetime.now(timezone.utc)
                if theme in existing_narratives:
                    previous_count = existing_narratives[theme].get("article_count")
                    first_seen = existing_narratives[theme].get("first_seen", first_seen)
                
                # Determine lifecycle stage
                lifecycle = determine_lifecycle_stage(article_count, mention_velocity, previous_count)
                
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
                    "lifecycle": lifecycle
                }
                
                narratives.append(narrative)
                logger.info(f"Created narrative for theme '{theme}': {article_count} articles, lifecycle={lifecycle}")
                
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
