"""
Narrative discovery service using two-layer approach.

Layer 1 (Discovery): Extract natural narrative elements (actors, actions, tensions, implications)
Layer 2 (Mapping): Optionally map narratives to themes for analytics and backward compatibility
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


async def discover_narrative_from_article(
    article_id: str,
    title: str,
    summary: str
) -> Optional[Dict[str, Any]]:
    """
    Layer 1: Discover natural narrative elements from an article.
    
    Extracts actors, actions, tensions, implications, and a natural narrative summary
    without forcing the article into predefined categories.
    
    Args:
        article_id: Article ID for logging
        title: Article title
        summary: Article summary/description
    
    Returns:
        Dict with narrative discovery data or None if extraction fails
    """
    if not title and not summary:
        logger.warning(f"Article {article_id} has no title or summary for narrative discovery")
        return None
    
    # Build Layer 1 discovery prompt
    prompt = f"""You are a narrative analyst studying emerging patterns in crypto news.

Given the following article, describe:
1. The main *actors* (people, organizations, protocols, assets, regulators)
2. The main *actions or events* (what happened)
3. The *forces or tensions* at play (e.g., regulation vs innovation, centralization vs decentralization, institutional adoption vs retail, security vs usability)
4. The *implications* or *stakes* (why it matters, what's shifting in the ecosystem)

Then summarize in 2-3 sentences what broader narrative this article contributes to.

Article Title: {title}
Article Summary: {summary[:500]}

Express narratives naturally, such as:
- "Regulators are tightening control over centralized exchanges"
- "Ethereum's scaling race intensifies as new L2 solutions gain traction"
- "Traditional finance firms are racing to launch Bitcoin ETF products"
- "DeFi protocols face growing security concerns after recent exploits"

Output valid JSON:
{{
  "actors": ["list of key actors"],
  "actions": ["list of key events or actions"],
  "tensions": ["list of forces or tensions"],
  "implications": "why this matters",
  "narrative_summary": "2-3 sentence natural narrative description"
}}

Do not use predefined categories. Describe what you observe."""
    
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
        required_fields = ["actors", "actions", "tensions", "implications", "narrative_summary"]
        if not all(field in narrative_data for field in required_fields):
            logger.warning(f"Missing required fields in narrative data for article {article_id}")
            return None
        
        logger.debug(f"Discovered narrative for article {article_id}: {narrative_data.get('narrative_summary', '')[:100]}")
        return narrative_data
    
    except Exception as e:
        logger.exception(f"Error discovering narrative for article {article_id}: {e}")
        return None


async def map_narrative_to_themes(
    narrative_summary: str,
    article_id: str
) -> Dict[str, Any]:
    """
    Layer 2: Map a natural narrative to predefined themes for analytics.
    
    This provides backward compatibility and enables theme-based filtering
    while preserving the rich narrative discovery from Layer 1.
    
    Args:
        narrative_summary: Natural narrative description from Layer 1
        article_id: Article ID for logging
    
    Returns:
        Dict with themes and optional suggested_new_theme
    """
    if not narrative_summary:
        logger.warning(f"Empty narrative summary for article {article_id}")
        return {"themes": ["emerging"], "suggested_new_theme": None}
    
    # Build Layer 2 mapping prompt
    prompt = f"""Given this narrative summary: "{narrative_summary}"

Map it to 1-3 relevant high-level themes from this list:
{THEME_CATEGORIES}

If no existing category fits well, return ["emerging"] and suggest a new category label based on the narrative.

Output JSON:
{{
  "themes": ["theme1", "theme2"],
  "suggested_new_theme": "optional new category if needed"
}}"""
    
    try:
        # Call LLM
        llm_client = get_llm_provider()
        response = llm_client._get_completion(prompt)
        
        if not response:
            logger.warning(f"Empty response from LLM for article {article_id}")
            return {"themes": ["emerging"], "suggested_new_theme": None}
        
        # Parse JSON response with cleaning
        response_clean = clean_json_response(response)
        
        try:
            mapping_data = json.loads(response_clean)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON for article {article_id}: {e}. Response: {response_clean[:200]}")
            return {"themes": ["emerging"], "suggested_new_theme": None}
        
        # Validate themes are in our predefined list (or "emerging")
        themes = mapping_data.get("themes", [])
        valid_themes = [t for t in themes if t in THEME_CATEGORIES or t == "emerging"]
        
        if not valid_themes:
            valid_themes = ["emerging"]
        
        result = {
            "themes": valid_themes,
            "suggested_new_theme": mapping_data.get("suggested_new_theme")
        }
        
        logger.debug(f"Mapped narrative to themes for article {article_id}: {valid_themes}")
        return result
    
    except Exception as e:
        logger.exception(f"Error mapping narrative to themes for article {article_id}: {e}")
        return {"themes": ["emerging"], "suggested_new_theme": None}


async def extract_themes_from_article(
    article_id: str,
    title: str,
    summary: str
) -> List[str]:
    """
    Legacy function for backward compatibility.
    
    Now uses the two-layer approach internally:
    1. Discover narrative (Layer 1)
    2. Map to themes (Layer 2)
    
    Args:
        article_id: Article ID for logging
        title: Article title
        summary: Article summary/description
    
    Returns:
        List of theme strings (e.g., ["regulatory", "institutional_investment"])
    """
    # Use new two-layer approach
    narrative_data = await discover_narrative_from_article(article_id, title, summary)
    
    if not narrative_data:
        return []
    
    # Map narrative to themes
    mapping = await map_narrative_to_themes(narrative_data.get("narrative_summary", ""), article_id)
    
    return mapping.get("themes", [])


async def backfill_narratives_for_recent_articles(hours: int = 48, limit: int = 100) -> int:
    """
    Backfill narrative discovery data for recent articles.
    
    Uses the two-layer approach:
    - Layer 1: Discover narrative elements (actors, actions, tensions, etc.)
    - Layer 2: Map to themes for backward compatibility
    
    Args:
        hours: Look back this many hours for articles
        limit: Maximum number of articles to process
    
    Returns:
        Number of articles updated with narrative data
    """
    db = await mongo_manager.get_async_database()
    articles_collection = db.articles
    
    from datetime import timedelta
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    # Find recent articles without narrative data
    cursor = articles_collection.find({
        "published_at": {"$gte": cutoff_time},
        "$or": [
            {"narrative_summary": {"$exists": False}},
            {"themes": {"$exists": False}},
            {"themes": {"$size": 0}}
        ]
    }).limit(limit)
    
    updated_count = 0
    
    async for article in cursor:
        article_id = str(article.get("_id"))
        title = article.get("title", "")
        summary = article.get("description", "") or article.get("text", "") or article.get("content", "")
        
        # Layer 1: Discover narrative
        narrative_data = await discover_narrative_from_article(article_id, title, summary)
        
        if narrative_data:
            # Layer 2: Map to themes
            mapping = await map_narrative_to_themes(narrative_data.get("narrative_summary", ""), article_id)
            
            # Update article with both narrative discovery and theme mapping
            update_data = {
                "actors": narrative_data.get("actors", []),
                "actions": narrative_data.get("actions", []),
                "tensions": narrative_data.get("tensions", []),
                "implications": narrative_data.get("implications", ""),
                "narrative_summary": narrative_data.get("narrative_summary", ""),
                "mapped_themes": mapping.get("themes", []),
                "themes": mapping.get("themes", []),  # Keep for backward compatibility
                "suggested_new_theme": mapping.get("suggested_new_theme"),
                "narrative_extracted_at": datetime.now(timezone.utc)
            }
            
            await articles_collection.update_one(
                {"_id": article["_id"]},
                {"$set": update_data}
            )
            updated_count += 1
            logger.info(f"Updated article {article_id} with narrative: {narrative_data.get('narrative_summary', '')[:80]}...")
    
    logger.info(f"Backfilled narratives for {updated_count} articles")
    return updated_count


async def backfill_themes_for_recent_articles(hours: int = 48, limit: int = 100) -> int:
    """
    Legacy function for backward compatibility.
    Now calls backfill_narratives_for_recent_articles.
    
    Args:
        hours: Look back this many hours for articles
        limit: Maximum number of articles to process
    
    Returns:
        Number of articles updated
    """
    return await backfill_narratives_for_recent_articles(hours, limit)


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


async def get_articles_by_narrative_similarity(
    hours: int = 48,
    min_articles: int = 2
) -> List[List[Dict[str, Any]]]:
    """
    Group articles by narrative similarity using actors and tensions.
    
    This creates richer narrative clusters than theme-based grouping alone.
    Articles are grouped if they share:
    - Similar actors (people, organizations, protocols)
    - Similar tensions (forces at play)
    
    Args:
        hours: Look back this many hours
        min_articles: Minimum articles per cluster
    
    Returns:
        List of article clusters (each cluster is a list of articles)
    """
    db = await mongo_manager.get_async_database()
    articles_collection = db.articles
    
    from datetime import timedelta
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    # Find articles with narrative data
    cursor = articles_collection.find({
        "published_at": {"$gte": cutoff_time},
        "narrative_summary": {"$exists": True},
        "actors": {"$exists": True, "$ne": []}
    }).sort("published_at", -1)
    
    articles = []
    async for article in cursor:
        articles.append(article)
    
    if not articles:
        return []
    
    # Group articles by shared actors and tensions
    clusters = []
    processed = set()
    
    for i, article in enumerate(articles):
        if str(article["_id"]) in processed:
            continue
        
        article_actors = set(article.get("actors", []))
        article_tensions = set(article.get("tensions", []))
        
        # Start a new cluster
        cluster = [article]
        processed.add(str(article["_id"]))
        
        # Find similar articles
        for j, other_article in enumerate(articles[i+1:], start=i+1):
            if str(other_article["_id"]) in processed:
                continue
            
            other_actors = set(other_article.get("actors", []))
            other_tensions = set(other_article.get("tensions", []))
            
            # Check for shared actors or tensions
            shared_actors = article_actors & other_actors
            shared_tensions = article_tensions & other_tensions
            
            # Group if they share at least 2 actors OR 1 tension
            if len(shared_actors) >= 2 or len(shared_tensions) >= 1:
                cluster.append(other_article)
                processed.add(str(other_article["_id"]))
        
        # Only keep clusters that meet minimum size
        if len(cluster) >= min_articles:
            clusters.append(cluster)
    
    logger.info(f"Found {len(clusters)} narrative clusters from {len(articles)} articles")
    return clusters


async def generate_narrative_from_cluster(
    articles: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    Generate a rich narrative summary from a cluster of related articles.
    
    Uses the narrative_summary from each article to create a cohesive
    narrative title and description.
    
    Args:
        articles: List of article documents with narrative data
    
    Returns:
        Dict with narrative data or None if generation fails
    """
    if not articles:
        return None
    
    # Collect narrative summaries and key elements
    narrative_summaries = []
    all_actors = set()
    all_tensions = set()
    
    for article in articles[:5]:  # Use up to 5 articles for context
        narrative_summary = article.get("narrative_summary", "")
        if narrative_summary:
            narrative_summaries.append(f"- {narrative_summary}")
        
        all_actors.update(article.get("actors", []))
        all_tensions.update(article.get("tensions", []))
    
    summaries_text = "\n".join(narrative_summaries)
    actors_text = ", ".join(list(all_actors)[:10])
    tensions_text = ", ".join(list(all_tensions)[:5])
    
    # Build prompt using narrative summaries
    prompt = f"""Analyze these related crypto news narratives:

{summaries_text}

Key actors involved: {actors_text}
Key tensions: {tensions_text}

Create a cohesive narrative that captures what's happening:
1. Generate a specific, descriptive title (max 80 characters) that names the key actors and action
2. Write a 2-3 sentence summary that explains the broader narrative

Examples of good titles:
- "SEC vs Major Exchanges: Regulators intensify enforcement against Binance and Coinbase"
- "Ethereum L2 Competition: Arbitrum, Optimism, and Base compete for DeFi market share"
- "Bitcoin ETF Race: BlackRock and Fidelity push for regulatory approval"

Return valid JSON with no newlines in string values: {{"title": "...", "summary": "..."}}"""
    
    try:
        # Call LLM
        llm_client = get_llm_provider()
        response = llm_client._get_completion(prompt)
        
        if not response:
            logger.warning(f"Empty response from LLM for narrative cluster")
            return None
        
        # Parse JSON response with cleaning
        response_clean = clean_json_response(response)
        
        try:
            narrative_data = json.loads(response_clean)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON for narrative cluster: {e}. Response: {response_clean[:200]}")
            return None
        
        return {
            "title": narrative_data.get("title", "Emerging Narrative"),
            "summary": narrative_data.get("summary", "")
        }
    
    except Exception as e:
        logger.exception(f"Error generating narrative from cluster: {e}")
        return None


async def generate_narrative_from_theme(
    theme: str,
    articles: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    Legacy function for backward compatibility.
    Now uses narrative summaries if available, falls back to old approach.
    
    Args:
        theme: The theme connecting these articles
        articles: List of article documents
    
    Returns:
        Dict with narrative data or None if generation fails
    """
    if not articles:
        return None
    
    # Check if articles have narrative summaries
    has_narratives = any(article.get("narrative_summary") for article in articles)
    
    if has_narratives:
        # Use new narrative-based approach
        return await generate_narrative_from_cluster(articles)
    
    # Fallback to old theme-based approach
    article_snippets = []
    for article in articles[:5]:
        title = article.get("title", "")
        summary = article.get("description", "") or article.get("text", "")[:200]
        article_snippets.append(f"- {title}: {summary}")
    
    snippets_text = "\n".join(article_snippets)
    
    prompt = f"""Analyze these crypto news articles that share the theme "{theme}":

{snippets_text}

Generate a narrative summary:
1. Create a concise title (max 60 characters) that captures the main story
2. Write a 2-3 sentence summary of what's happening in this narrative

Return valid JSON with no newlines in string values: {{"title": "...", "summary": "..."}}"""
    
    try:
        llm_client = get_llm_provider()
        response = llm_client._get_completion(prompt)
        
        if not response:
            logger.warning(f"Empty response from LLM for theme {theme}")
            return None
        
        response_clean = clean_json_response(response)
        
        try:
            narrative_data = json.loads(response_clean)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON for theme {theme}: {e}. Using fallback. Response: {response_clean[:200]}")
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
