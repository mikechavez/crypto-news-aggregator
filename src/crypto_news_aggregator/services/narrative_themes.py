"""
Theme extraction service for narrative detection.

This service uses Claude Sonnet to extract thematic categories from articles,
enabling theme-based narrative clustering instead of entity co-occurrence.
"""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from ..db.mongodb import mongo_manager
from ..llm.factory import get_llm_provider

logger = logging.getLogger(__name__)

# Predefined theme categories for crypto news
THEME_CATEGORIES = [
    "regulatory",           # SEC actions, legal frameworks, compliance
    "defi_adoption",        # DeFi protocols, TVL changes, yield farming
    "institutional_investment",  # Corporate adoption, ETFs, institutional flows
    "payments",             # Payment rails, merchant adoption, remittances
    "layer2_scaling",       # L2 solutions, rollups, scaling tech
    "security",             # Hacks, exploits, security audits
    "infrastructure",       # Node operators, validators, network upgrades
    "nft_gaming",           # NFTs, gaming, metaverse
    "stablecoin",           # Stablecoin regulation, depegs, adoption
    "market_analysis",      # Price action, trading volumes, market sentiment
    "technology",           # Protocol upgrades, new tech, research
    "partnerships",         # Collaborations, integrations, ecosystem growth
]


async def extract_themes_from_article(
    article_id: str,
    title: str,
    summary: str
) -> List[str]:
    """
    Extract thematic categories from an article using Claude Sonnet.
    
    Args:
        article_id: Article ID for logging
        title: Article title
        summary: Article summary/description
    
    Returns:
        List of theme strings (e.g., ["regulatory", "institutional_investment"])
    """
    if not title and not summary:
        logger.warning(f"Article {article_id} has no title or summary for theme extraction")
        return []
    
    # Build prompt for Claude
    prompt = f"""Analyze this crypto news article and identify the primary themes.

Article Title: {title}
Article Summary: {summary[:500]}

Available themes:
{', '.join(THEME_CATEGORIES)}

Return ONLY a JSON array of 1-3 most relevant themes from the list above.
Example: ["regulatory", "institutional_investment"]

JSON array:"""
    
    try:
        # Call Claude
        llm_client = get_llm_provider()
        response = llm_client._get_completion(prompt)
        
        if not response:
            logger.warning(f"Empty response from LLM for article {article_id}")
            return []
        
        # Parse JSON response
        response_clean = response.strip()
        if response_clean.startswith("```json"):
            response_clean = response_clean[7:]
        if response_clean.startswith("```"):
            response_clean = response_clean[3:]
        if response_clean.endswith("```"):
            response_clean = response_clean[:-3]
        response_clean = response_clean.strip()
        
        themes = json.loads(response_clean)
        
        # Validate themes are in our predefined list
        valid_themes = [t for t in themes if t in THEME_CATEGORIES]
        
        if not valid_themes:
            logger.warning(f"No valid themes extracted for article {article_id}. Response: {themes}")
            return []
        
        logger.debug(f"Extracted themes for article {article_id}: {valid_themes}")
        return valid_themes
    
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse JSON response for article {article_id}: {e}. Response: {response}")
        return []
    except Exception as e:
        logger.exception(f"Error extracting themes for article {article_id}: {e}")
        return []


async def backfill_themes_for_recent_articles(hours: int = 48, limit: int = 100) -> int:
    """
    Backfill themes for recent articles that don't have them yet.
    
    Args:
        hours: Look back this many hours for articles
        limit: Maximum number of articles to process
    
    Returns:
        Number of articles updated with themes
    """
    db = await mongo_manager.get_async_database()
    articles_collection = db.articles
    
    from datetime import timedelta
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    # Find recent articles without themes
    cursor = articles_collection.find({
        "published_at": {"$gte": cutoff_time},
        "$or": [
            {"themes": {"$exists": False}},
            {"themes": {"$size": 0}}
        ]
    }).limit(limit)
    
    updated_count = 0
    
    async for article in cursor:
        article_id = str(article.get("_id"))
        title = article.get("title", "")
        summary = article.get("description", "") or article.get("text", "") or article.get("content", "")
        
        # Extract themes
        themes = await extract_themes_from_article(article_id, title, summary)
        
        if themes:
            # Update article with themes
            await articles_collection.update_one(
                {"_id": article["_id"]},
                {"$set": {"themes": themes, "themes_extracted_at": datetime.now(timezone.utc)}}
            )
            updated_count += 1
            logger.info(f"Updated article {article_id} with themes: {themes}")
    
    logger.info(f"Backfilled themes for {updated_count} articles")
    return updated_count


async def get_articles_by_theme(
    theme: str,
    hours: int = 48,
    min_articles: int = 3
) -> Optional[List[Dict[str, Any]]]:
    """
    Get articles that share a specific theme within a time window.
    
    Args:
        theme: Theme to filter by
        hours: Look back this many hours
        min_articles: Minimum number of articles required to return results
    
    Returns:
        List of article documents or None if below threshold
    """
    db = await mongo_manager.get_async_database()
    articles_collection = db.articles
    
    from datetime import timedelta
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    # Find articles with this theme
    cursor = articles_collection.find({
        "themes": theme,
        "published_at": {"$gte": cutoff_time}
    }).sort("published_at", -1)
    
    articles = []
    async for article in cursor:
        articles.append(article)
    
    if len(articles) < min_articles:
        return None
    
    return articles


async def generate_narrative_from_theme(
    theme: str,
    articles: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    Generate a narrative summary for a theme-based article cluster.
    
    Args:
        theme: The theme connecting these articles
        articles: List of article documents
    
    Returns:
        Dict with narrative data or None if generation fails
    """
    if not articles:
        return None
    
    # Collect article titles and summaries
    article_snippets = []
    for article in articles[:5]:  # Use up to 5 articles for context
        title = article.get("title", "")
        summary = article.get("description", "") or article.get("text", "")[:200]
        article_snippets.append(f"- {title}: {summary}")
    
    snippets_text = "\n".join(article_snippets)
    
    # Build prompt for Claude
    prompt = f"""Analyze these crypto news articles that share the theme "{theme}":

{snippets_text}

Generate a narrative summary:
1. Create a concise title (max 60 characters) that captures the main story
2. Write a 2-3 sentence summary of what's happening in this narrative

Return JSON: {{"title": "...", "summary": "..."}}"""
    
    try:
        # Call Claude
        llm_client = get_llm_provider()
        response = llm_client._get_completion(prompt)
        
        if not response:
            logger.warning(f"Empty response from LLM for theme {theme}")
            return None
        
        # Parse JSON response
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
            "title": narrative_data.get("title", f"{theme.replace('_', ' ').title()} Narrative"),
            "summary": narrative_data.get("summary", "")
        }
    
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse JSON response for theme {theme}: {e}. Response: {response}")
        # Fallback
        return {
            "title": f"{theme.replace('_', ' ').title()} Narrative",
            "summary": f"Multiple articles discussing {theme.replace('_', ' ')} in the crypto space."
        }
    except Exception as e:
        logger.exception(f"Error generating narrative for theme {theme}: {e}")
        return None
