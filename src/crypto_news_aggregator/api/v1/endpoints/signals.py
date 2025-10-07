"""
Signals API endpoints for trending entity detection.
"""

import json
from fastapi import APIRouter, Query, HTTPException
from typing import List, Dict, Any, Optional
from bson import ObjectId

from ....db.operations.signal_scores import get_trending_entities
from ....core.redis_rest_client import redis_client
from ....db.mongodb import mongo_manager

router = APIRouter()


async def get_narrative_details(narrative_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Fetch narrative details for a list of narrative IDs.
    
    Args:
        narrative_ids: List of narrative ObjectId strings
    
    Returns:
        List of narrative detail dicts with id, title, theme, lifecycle
    """
    if not narrative_ids:
        return []
    
    db = await mongo_manager.get_async_database()
    collection = db.narratives
    
    # Convert string IDs to ObjectIds
    try:
        object_ids = [ObjectId(nid) for nid in narrative_ids]
    except Exception:
        return []
    
    # Fetch narratives
    cursor = collection.find({"_id": {"$in": object_ids}})
    
    narratives = []
    async for narrative in cursor:
        narratives.append({
            "id": str(narrative["_id"]),
            "title": narrative.get("title", ""),
            "theme": narrative.get("theme", ""),
            "lifecycle": narrative.get("lifecycle", "")
        })
    
    return narratives


@router.get("/trending")
async def get_trending_signals(
    limit: int = Query(default=10, ge=1, le=100, description="Maximum number of results"),
    min_score: float = Query(default=0.0, ge=0.0, le=10.0, description="Minimum signal score"),
    entity_type: Optional[str] = Query(default=None, description="Filter by entity type (ticker, project, event)"),
) -> Dict[str, Any]:
    """
    Get trending entities based on signal scores.
    
    Signal scores are calculated based on:
    - Velocity: Rate of mentions over time
    - Source diversity: Number of unique sources
    - Sentiment: Average sentiment and divergence
    
    Results are cached for 2 minutes.
    
    Args:
        limit: Maximum number of results (1-100, default 10)
        min_score: Minimum signal score threshold (0-10, default 0)
        entity_type: Filter by entity type (optional)
    
    Returns:
        List of trending entities with signal scores
    """
    # Validate entity_type if provided
    if entity_type and entity_type not in ["ticker", "project", "event"]:
        raise HTTPException(
            status_code=400,
            detail="entity_type must be one of: ticker, project, event"
        )
    
    # Build cache key
    cache_key = f"signals:trending:{limit}:{min_score}:{entity_type or 'all'}"
    
    # Try to get from cache
    cached_result = redis_client.get(cache_key)
    if cached_result:
        try:
            # Parse cached JSON
            return json.loads(cached_result)
        except (json.JSONDecodeError, TypeError):
            # If cache is corrupted, continue to fetch fresh data
            pass
    
    # Fetch trending entities
    try:
        trending = await get_trending_entities(
            limit=limit,
            min_score=min_score,
            entity_type=entity_type,
        )
        
        # Fetch narrative details for all signals
        signals_with_narratives = []
        for signal in trending:
            narrative_ids = signal.get("narrative_ids", [])
            narratives = await get_narrative_details(narrative_ids)
            
            signals_with_narratives.append({
                "entity": signal["entity"],
                "entity_type": signal["entity_type"],
                "signal_score": signal["score"],
                "velocity": signal["velocity"],
                "source_count": signal["source_count"],
                "sentiment": signal["sentiment"],
                "is_emerging": signal.get("is_emerging", False),
                "narratives": narratives,
                "first_seen": signal["first_seen"].isoformat() if signal.get("first_seen") else None,
                "last_updated": signal["last_updated"].isoformat() if signal.get("last_updated") else None,
            })
        
        # Format response
        response = {
            "count": len(trending),
            "filters": {
                "limit": limit,
                "min_score": min_score,
                "entity_type": entity_type,
            },
            "signals": signals_with_narratives,
        }
        
        # Cache for 2 minutes (120 seconds)
        try:
            redis_client.set(cache_key, json.dumps(response), ex=120)
        except Exception as e:
            # Log but don't fail if caching fails
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to cache trending signals: {e}")
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch trending signals: {str(e)}"
        )
