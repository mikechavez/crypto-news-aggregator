"""
Narrative clustering service using theme-based detection.

This service identifies narratives by:
- Extracting themes from articles using Claude Sonnet
- Grouping articles by shared themes (not entity co-occurrence)
- Generating AI-powered narrative summaries
- Tracking narrative lifecycle (emerging, hot, mature, declining)
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
    THEME_CATEGORIES
)

logger = logging.getLogger(__name__)


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
    min_articles: int = 2
) -> List[Dict[str, Any]]:
    """
    Detect active narratives using theme-based clustering.
    
    Main entry point for narrative detection. Groups articles by shared themes
    and generates narrative summaries for active themes.
    
    Args:
        hours: Look back this many hours for articles (default 48)
        min_articles: Minimum articles per theme to create narrative (default 2)
    
    Returns:
        List of narrative dicts with full structure including lifecycle tracking
    """
    try:
        # Step 1: Backfill themes for recent articles that don't have them
        logger.info(f"Backfilling themes for articles from last {hours} hours")
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
