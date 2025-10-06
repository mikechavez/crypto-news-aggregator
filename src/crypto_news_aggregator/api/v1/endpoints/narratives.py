"""
Narrative API endpoints.

Provides access to detected narrative clusters from co-occurring entities.
"""

import json
import logging
from typing import List
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field

from ....db.operations.narratives import get_active_narratives
from ....core.redis_rest_client import redis_client

logger = logging.getLogger(__name__)

router = APIRouter()


class NarrativeResponse(BaseModel):
    """Response model for a narrative."""
    theme: str = Field(..., description="Theme category (e.g., regulatory, defi_adoption)")
    title: str = Field(..., description="Generated narrative title")
    summary: str = Field(..., description="AI-generated narrative summary")
    entities: List[str] = Field(..., description="List of entities in this narrative")
    article_count: int = Field(..., description="Number of articles supporting this narrative")
    mention_velocity: float = Field(..., description="Articles per day rate")
    lifecycle: str = Field(..., description="Lifecycle stage: emerging, hot, mature, declining")
    first_seen: str = Field(..., description="ISO timestamp when narrative was first detected")
    last_updated: str = Field(..., description="ISO timestamp of last update")
    
    class Config:
        json_schema_extra = {
            "example": {
                "theme": "regulatory",
                "title": "SEC crypto enforcement actions intensify",
                "summary": "The SEC has ramped up enforcement actions against major crypto exchanges, with new lawsuits and regulatory guidance affecting the industry.",
                "entities": ["SEC", "Coinbase", "Binance", "Gary Gensler"],
                "article_count": 15,
                "mention_velocity": 3.1,
                "lifecycle": "hot",
                "first_seen": "2025-10-01T19:30:00Z",
                "last_updated": "2025-10-06T14:20:00Z"
            }
        }


@router.get("/active", response_model=List[NarrativeResponse])
async def get_active_narratives_endpoint(
    limit: int = Query(10, ge=1, le=20, description="Maximum number of narratives to return")
):
    """
    Get active narrative clusters.
    
    Returns the most recently updated narratives, representing groups of
    co-occurring crypto entities with AI-generated thematic summaries.
    
    Results are cached for 10 minutes to reduce database load.
    
    Args:
        limit: Maximum number of narratives (1-20, default 10)
    
    Returns:
        List of narrative objects with theme, entities, story, and metadata
    """
    # Try to get from cache
    cache_key = f"narratives:active:{limit}"
    
    try:
        if redis_client.enabled:
            cached = redis_client.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for {cache_key}")
                # Parse cached JSON
                try:
                    narratives_data = json.loads(cached) if isinstance(cached, str) else cached
                    return [NarrativeResponse(**n) for n in narratives_data]
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(f"Failed to parse cached narratives: {e}")
                    # Continue to fetch from database
    except Exception as e:
        logger.warning(f"Redis cache read error: {e}")
        # Continue without cache
    
    # Fetch from database
    try:
        narratives = await get_active_narratives(limit=limit)
        
        if not narratives:
            return []
        
        # Convert to response models
        response_data = []
        for narrative in narratives:
            # Convert datetime to ISO string
            last_updated = narrative.get("last_updated")
            if last_updated:
                last_updated_str = last_updated.isoformat() if hasattr(last_updated, 'isoformat') else str(last_updated)
            else:
                last_updated_str = ""
            
            first_seen = narrative.get("first_seen")
            if first_seen:
                first_seen_str = first_seen.isoformat() if hasattr(first_seen, 'isoformat') else str(first_seen)
            else:
                first_seen_str = ""
            
            response_data.append({
                "theme": narrative.get("theme", ""),
                "title": narrative.get("title", ""),
                "summary": narrative.get("summary", ""),
                "entities": narrative.get("entities", []),
                "article_count": narrative.get("article_count", 0),
                "mention_velocity": narrative.get("mention_velocity", 0.0),
                "lifecycle": narrative.get("lifecycle", "emerging"),
                "first_seen": first_seen_str,
                "last_updated": last_updated_str
            })
        
        # Cache the results for 10 minutes (600 seconds)
        try:
            if redis_client.enabled:
                cache_value = json.dumps(response_data)
                redis_client.set(cache_key, cache_value, ex=600)
                logger.debug(f"Cached {len(response_data)} narratives for {cache_key}")
        except Exception as e:
            logger.warning(f"Redis cache write error: {e}")
            # Continue without caching
        
        return [NarrativeResponse(**n) for n in response_data]
    
    except Exception as e:
        logger.exception(f"Error fetching active narratives: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch narratives")
