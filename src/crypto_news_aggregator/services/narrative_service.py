"""
Narrative clustering service for detecting co-occurring crypto entities.

This service identifies narratives by:
- Finding entities that frequently appear together in articles
- Generating AI-powered summaries of the narrative themes
- Tracking narrative strength by article count
"""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from ..db.mongodb import mongo_manager
from crypto_news_aggregator.db.operations.signal_scores import get_trending_entities
from ..llm.factory import get_llm_provider

logger = logging.getLogger(__name__)


async def find_cooccurring_entities(
    top_entities: List[Dict[str, Any]], 
    min_shared_articles: int = 2
) -> List[Dict[str, Any]]:
    """
    Find entities that co-occur in articles.
    
    Groups entities that appear together in at least min_shared_articles.
    Uses a simple co-occurrence approach without complex graph algorithms.
    
    Args:
        top_entities: List of entity dicts with 'entity' field
        min_shared_articles: Minimum number of shared articles to form a group
    
    Returns:
        List of groups: [{entities: [list], article_ids: [list]}]
    """
    db = await mongo_manager.get_async_database()
    entity_mentions_collection = db.entity_mentions
    
    # Build a map of entity -> article_ids
    entity_to_articles: Dict[str, set] = {}
    
    for entity_data in top_entities:
        entity = entity_data.get("entity")
        if not entity:
            continue
            
        # Get all article IDs that mention this entity
        cursor = entity_mentions_collection.find({"entity": entity})
        article_ids = set()
        async for mention in cursor:
            article_id = mention.get("article_id")
            if article_id:
                article_ids.add(str(article_id))
        
        entity_to_articles[entity] = article_ids
    
    # Find co-occurring entity groups
    groups = []
    processed_entities = set()
    
    entity_list = list(entity_to_articles.keys())
    
    for i, entity1 in enumerate(entity_list):
        if entity1 in processed_entities:
            continue
            
        articles1 = entity_to_articles[entity1]
        if len(articles1) == 0:
            continue
        
        # Find entities that share articles with entity1
        group_entities = [entity1]
        group_articles = articles1.copy()
        
        for entity2 in entity_list[i+1:]:
            if entity2 in processed_entities:
                continue
                
            articles2 = entity_to_articles[entity2]
            shared = articles1 & articles2
            
            if len(shared) >= min_shared_articles:
                group_entities.append(entity2)
                group_articles = group_articles & articles2  # Intersection for tighter grouping
        
        # Only create group if we have co-occurrence
        if len(group_entities) > 1 and len(group_articles) >= min_shared_articles:
            groups.append({
                "entities": group_entities,
                "article_ids": list(group_articles)
            })
            processed_entities.update(group_entities)
    
    return groups


async def generate_narrative_summary(entity_group: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Generate a narrative summary for a group of co-occurring entities.
    
    Uses Claude to analyze a sample article and generate a concise narrative theme.
    
    Args:
        entity_group: Dict with 'entities' and 'article_ids' keys
    
    Returns:
        Dict with {theme, entities, story, article_count} or None if generation fails
    """
    entities = entity_group.get("entities", [])
    article_ids = entity_group.get("article_ids", [])
    
    if not entities or not article_ids:
        return None
    
    # Get one sample article
    db = await mongo_manager.get_async_database()
    articles_collection = db.articles
    
    try:
        # Try to get article by ID (handle both string and ObjectId)
        from bson import ObjectId
        sample_article_id = article_ids[0]
        
        # Try as ObjectId first, fall back to string
        try:
            if ObjectId.is_valid(sample_article_id):
                sample_article = await articles_collection.find_one({"_id": ObjectId(sample_article_id)})
            else:
                sample_article = await articles_collection.find_one({"_id": sample_article_id})
        except Exception:
            sample_article = await articles_collection.find_one({"_id": sample_article_id})
        
        if not sample_article:
            logger.warning(f"Could not find sample article {sample_article_id} for narrative generation")
            return None
        
        # Extract article content
        title = sample_article.get("title", "")
        text = sample_article.get("text", "") or sample_article.get("content", "") or sample_article.get("description", "")
        snippet = text[:300] if text else ""
        
        # Get entity types from entity_mentions
        entity_mentions_collection = db.entity_mentions
        entity_details = []
        for entity in entities:
            mention = await entity_mentions_collection.find_one({"entity": entity})
            entity_type = mention.get("entity_type", "unknown") if mention else "unknown"
            entity_details.append(f"{entity} ({entity_type})")
        
        # Build prompt for Claude
        prompt = f"""These crypto entities appear together in articles:
Entities: {', '.join(entity_details)}
Sample article title: {title}
Sample text: {snippet}

In 1-2 sentences, describe the narrative connecting these entities.
Return JSON: {{"theme": "short title", "story": "1-2 sentence summary"}}"""
        
        # Call Claude
        llm_client = get_llm_provider()
        response = llm_client._get_completion(prompt)
        
        if not response:
            logger.warning("Empty response from LLM for narrative generation")
            return None
        
        # Parse JSON response
        try:
            # Try to extract JSON from response
            response_clean = response.strip()
            if response_clean.startswith("```json"):
                response_clean = response_clean[7:]
            if response_clean.startswith("```"):
                response_clean = response_clean[3:]
            if response_clean.endswith("```"):
                response_clean = response_clean[:-3]
            response_clean = response_clean.strip()
            
            narrative_data = json.loads(response_clean)
            
            return {
                "theme": narrative_data.get("theme", "Untitled Narrative"),
                "entities": entities,
                "story": narrative_data.get("story", ""),
                "article_count": len(article_ids)
            }
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response from LLM: {e}. Response: {response}")
            # Fallback: create a simple narrative
            return {
                "theme": f"{entities[0]} & Related",
                "entities": entities,
                "story": f"Multiple articles discuss {', '.join(entities[:3])} together.",
                "article_count": len(article_ids)
            }
    
    except Exception as e:
        logger.exception(f"Error generating narrative summary: {e}")
        return None


async def detect_narratives(
    min_score: float = 5.0,
    max_narratives: int = 5
) -> List[Dict[str, Any]]:
    """
    Detect active narratives from trending entities.
    
    Main entry point for narrative detection. Finds co-occurring entities
    and generates summaries for the top narratives.
    
    Args:
        min_score: Minimum signal score for entities to consider
        max_narratives: Maximum number of narratives to return
    
    Returns:
        List of narrative dicts with theme, entities, story, article_count
    """
    try:
        # Get top trending entities
        top_entities = await get_trending_entities(limit=20, min_score=min_score)
        
        if not top_entities:
            logger.info("No trending entities found for narrative detection")
            return []
        
        logger.info(f"Found {len(top_entities)} trending entities for narrative detection")
        
        # Find co-occurring entity groups
        groups = await find_cooccurring_entities(top_entities, min_shared_articles=2)
        
        if not groups:
            logger.info("No co-occurring entity groups found")
            return []
        
        logger.info(f"Found {len(groups)} co-occurring entity groups")
        
        # Sort groups by article count (descending)
        groups.sort(key=lambda g: len(g.get("article_ids", [])), reverse=True)
        
        # Take top max_narratives groups
        top_groups = groups[:max_narratives]
        
        # Generate summaries for each group
        narratives = []
        for group in top_groups:
            narrative = await generate_narrative_summary(group)
            if narrative:
                narratives.append(narrative)
        
        logger.info(f"Generated {len(narratives)} narrative summaries")
        return narratives
    
    except Exception as e:
        logger.exception(f"Error in detect_narratives: {e}")
        return []
