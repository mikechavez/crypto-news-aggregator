"""
Theme extraction service for narrative detection.

This service uses Claude Sonnet to extract thematic categories from articles,
enabling theme-based narrative clustering instead of entity co-occurrence.
"""

import json
import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from ..db.mongodb import mongo_manager
from ..llm.factory import get_llm_provider

logger = logging.getLogger(__name__)


def clean_json_response(response: str) -> str:
    """
    Clean JSON response from LLM to handle control characters and newlines.
    
    Claude often includes newlines and control characters in JSON string values,
    which breaks json.loads(). This function:
    1. Strips markdown code blocks
    2. Replaces control characters (newlines, carriage returns, tabs) with spaces
    3. Normalizes multiple spaces to single space
    
    Args:
        response: Raw LLM response string
    
    Returns:
        Cleaned JSON string ready for parsing
    """
    # Strip markdown code blocks
    response_clean = response.strip()
    if response_clean.startswith("```json"):
        response_clean = response_clean[7:]
    if response_clean.startswith("```"):
        response_clean = response_clean[3:]
    if response_clean.endswith("```"):
        response_clean = response_clean[:-3]
    response_clean = response_clean.strip()
    
    # Replace control characters with spaces
    # This handles newlines (\n), carriage returns (\r), and tabs (\t)
    response_clean = response_clean.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    
    # Normalize multiple spaces to single space
    response_clean = re.sub(r'\s+', ' ', response_clean)
    
    return response_clean

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
        
        # Parse JSON response with cleaning
        response_clean = clean_json_response(response)
        
        try:
            themes = json.loads(response_clean)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON for article {article_id}: {e}. Response: {response_clean[:200]}")
            return []
        
        # Validate themes are in our predefined list
        valid_themes = [t for t in themes if t in THEME_CATEGORIES]
        
        if not valid_themes:
            logger.warning(f"No valid themes extracted for article {article_id}. Response: {themes}")
            return []
        
        logger.debug(f"Extracted themes for article {article_id}: {valid_themes}")
        return valid_themes
    
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
    min_articles: int = 2
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


async def discover_narrative_from_article(
    article_id: str,
    title: str,
    summary: str
) -> Optional[Dict[str, Any]]:
    """
    Layer 1: Discover narrative elements from an article using natural language extraction.
    
    Extracts actors, actions, tensions, implications, and narrative summary with salience scoring.
    
    Args:
        article_id: Article ID for logging
        title: Article title
        summary: Article summary/description
    
    Returns:
        Dict with narrative elements including actor_salience and nucleus_entity, or None if extraction fails
    """
    if not title and not summary:
        logger.warning(f"Article {article_id} has no title or summary for narrative discovery")
        return None
    
    # Build prompt for Claude with salience scoring
    prompt = f"""You are a narrative analyst studying emerging patterns in crypto news.

Given the following article, describe:

1. The main *actors* (people, organizations, protocols, assets, regulators)
   - For each actor, assign a salience score from 1-5:
     * 5 = central protagonist of the story (the article is ABOUT this entity)
     * 4 = key participant (actively involved in the main events)
     * 3 = secondary participant (mentioned with some relevance)
     * 2 = supporting context (provides background but not central)
     * 1 = passing mention (could remove without changing story)
   
   **IMPORTANT**: Only include actors with salience >= 2 in your final list.
   Background mentions (salience 1) should be excluded.

2. **Nucleus entity** (required): The ONE entity this article is primarily about.
   This is the anchor of the story - if you had to summarize in one word, which entity?

3. The main *actions or events* (what happened)

4. The *forces or tensions* at play (e.g., regulation vs innovation, centralization vs decentralization)

5. The *implications* or *stakes* (why it matters)

Then summarize in 2-3 sentences what broader narrative this article contributes to.

Article Title: {title}
Article Summary: {summary[:500]}

Output valid JSON:
{{
  "actors": ["list of actors with salience >= 2"],
  "actor_salience": {{
    "EntityName": 4,
    "AnotherEntity": 3
  }},
  "nucleus_entity": "PrimaryEntityName",
  "actions": ["list of key events"],
  "tensions": ["list of forces or tensions"],
  "implications": "why this matters",
  "narrative_summary": "2-3 sentence description"
}}

Example:
Article about "SEC sues Binance for regulatory violations"
{{
  "actors": ["SEC", "Binance", "Coinbase"],
  "actor_salience": {{
    "SEC": 5,
    "Binance": 4,
    "Coinbase": 2
  }},
  "nucleus_entity": "SEC",
  "actions": ["SEC filed lawsuit against Binance"],
  "tensions": ["Regulation vs Innovation", "Compliance vs Growth"],
  "implications": "Signals escalation in regulatory enforcement",
  "narrative_summary": "Regulators are intensifying enforcement against major exchanges as the SEC targets Binance for alleged securities violations, with implications for the broader industry."
}}

JSON output:"""
    
    try:
        # Call LLM
        llm_client = get_llm_provider()
        response = llm_client._get_completion(prompt)
        
        if not response:
            logger.warning(f"Empty response from LLM for article {article_id}")
            return None
        
        # Parse JSON response with cleaning
        response_clean = clean_json_response(response)
        
        try:
            narrative_data = json.loads(response_clean)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON for article {article_id}: {e}. Response: {response_clean[:200]}")
            return None
        
        # Validate required fields
        required_fields = ["actors", "actor_salience", "nucleus_entity", "actions", "tensions", "implications", "narrative_summary"]
        for field in required_fields:
            if field not in narrative_data:
                logger.warning(f"Missing required field '{field}' for article {article_id}")
                return None
        
        # Validate that we have meaningful data
        if not narrative_data.get("actors") or not narrative_data.get("actions"):
            logger.warning(f"Empty actors or actions for article {article_id}")
            return None
        
        logger.debug(f"Discovered narrative for article {article_id}: {narrative_data.get('narrative_summary', '')[:100]}")
        return narrative_data
    
    except Exception as e:
        logger.exception(f"Error discovering narrative for article {article_id}: {e}")
        return None


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

Return valid JSON with no newlines in string values: {{"title": "...", "summary": "..."}}"""
    
    try:
        # Call Claude
        llm_client = get_llm_provider()
        response = llm_client._get_completion(prompt)
        
        if not response:
            logger.warning(f"Empty response from LLM for theme {theme}")
            return None
        
        # Parse JSON response with cleaning
        response_clean = clean_json_response(response)
        
        try:
            narrative_data = json.loads(response_clean)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON for theme {theme}: {e}. Using fallback. Response: {response_clean[:200]}")
            # Fallback
            return {
                "title": f"{theme.replace('_', ' ').title()} Narrative",
                "summary": f"Multiple articles discussing {theme.replace('_', ' ')} in the crypto space."
            }
        
        return {
            "title": narrative_data.get("title", f"{theme.replace('_', ' ').title()} Narrative"),
            "summary": narrative_data.get("summary", "")
        }
    
    except Exception as e:
        logger.exception(f"Error generating narrative for theme {theme}: {e}")
        return None


async def cluster_by_narrative_salience(
    articles: List[Dict],
    min_cluster_size: int = 3
) -> List[List[Dict]]:
    """
    Cluster articles by nucleus entity and weighted actor/tension overlap.
    
    Clustering logic uses weighted link strength:
    - Same nucleus entity: +1.0 (strongest signal)
    - 2+ shared high-salience actors (≥4): +0.7
    - 1 shared high-salience actor: +0.4
    - 1+ shared tensions: +0.3
    
    Articles cluster together if link_strength >= 0.8
    
    Args:
        articles: List of article dicts with actors, actor_salience, nucleus_entity, tensions
        min_cluster_size: Minimum articles required to form a cluster
    
    Returns:
        List of article clusters (each cluster is a list of articles)
    """
    clusters = []
    
    for article in articles:
        nucleus = article.get('nucleus_entity')
        actors = article.get('actors', [])
        actor_salience = article.get('actor_salience', {})
        tensions = article.get('tensions', [])
        
        # Get high-salience actors only (salience >= 4)
        # These are the key players, not background mentions
        core_actors = [a for a in actors if actor_salience.get(a, 0) >= 4]
        
        # Try to match with existing cluster
        matched = False
        best_cluster = None
        best_strength = 0.0
        
        for cluster in clusters:
            # Get cluster properties from first article (representative)
            cluster_nucleus = cluster[0].get('nucleus_entity')
            
            # Aggregate cluster properties
            cluster_actors = set()
            cluster_core_actors = set()
            cluster_tensions = set()
            
            for cluster_article in cluster:
                cluster_actors.update(cluster_article.get('actors', []))
                cluster_tensions.update(cluster_article.get('tensions', []))
                c_salience = cluster_article.get('actor_salience', {})
                cluster_core_actors.update(
                    a for a in cluster_article.get('actors', [])
                    if c_salience.get(a, 0) >= 4
                )
            
            # Calculate weighted link strength
            link_strength = 0.0
            
            # Strongest signal: Same nucleus entity
            # e.g., Both articles are fundamentally about "SEC"
            if nucleus and nucleus == cluster_nucleus:
                link_strength += 1.0
            
            # Medium signal: High-salience actors overlap
            # e.g., Both feature "Binance" and "Coinbase" as key players
            shared_core = len(set(core_actors) & cluster_core_actors)
            if shared_core >= 2:
                link_strength += 0.7
            elif shared_core >= 1:
                link_strength += 0.4
            
            # Weaker signal: Shared tensions/themes
            # e.g., Both involve "Regulation vs Innovation"
            shared_tensions = len(set(tensions) & cluster_tensions)
            if shared_tensions >= 1:
                link_strength += 0.3
            
            # Track best matching cluster
            if link_strength > best_strength:
                best_strength = link_strength
                best_cluster = cluster
        
        # Cluster if link strength is strong enough (threshold: 0.8)
        if best_strength >= 0.8 and best_cluster is not None:
            best_cluster.append(article)
            matched = True
        
        # Create new cluster if no good match
        if not matched:
            clusters.append([article])
    
    # Filter out small clusters (below minimum size)
    substantial_clusters = [c for c in clusters if len(c) >= min_cluster_size]
    
    return substantial_clusters
