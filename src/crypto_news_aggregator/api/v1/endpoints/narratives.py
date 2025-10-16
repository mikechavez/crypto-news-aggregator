"""
Narrative API endpoints.

Provides access to detected narrative clusters from co-occurring entities.
"""

import json
import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field
from bson import ObjectId

from ....db.operations.narratives import get_active_narratives, get_narrative_timeline
from ....core.redis_rest_client import redis_client
from ....db.mongodb import mongo_manager

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_articles_for_narrative(article_ids: List[str], limit: int = 20) -> List[Dict[str, Any]]:
    """
    Fetch article details for a list of article IDs.
    
    Args:
        article_ids: List of article MongoDB ObjectIds (as strings)
        limit: Maximum number of articles to return (default 20)
    
    Returns:
        List of article dicts with title, url, source, published_at
    """
    if not article_ids:
        return []
    
    db = await mongo_manager.get_async_database()
    articles_collection = db.articles
    
    # Convert string IDs to ObjectIds
    object_ids = []
    for article_id in article_ids[:limit]:
        try:
            if isinstance(article_id, str):
                object_ids.append(ObjectId(article_id))
            else:
                object_ids.append(article_id)
        except Exception:
            continue
    
    if not object_ids:
        return []
    
    # Fetch articles by _id
    cursor = articles_collection.find(
        {"_id": {"$in": object_ids}}
    ).sort("published_at", -1).limit(limit)
    
    articles = []
    async for article in cursor:
        articles.append({
            "title": article.get("title", ""),
            "url": article.get("url", ""),
            "source": article.get("source", ""),
            "published_at": article.get("published_at").isoformat() if article.get("published_at") else None
        })
    
    return articles


class TimelineSnapshot(BaseModel):
    """Timeline snapshot for a single day."""
    date: str = Field(..., description="Date in ISO format (YYYY-MM-DD)")
    article_count: int = Field(..., description="Number of articles on this day")
    entities: List[str] = Field(..., description="Top entities mentioned on this day")
    velocity: float = Field(..., description="Articles per day rate")


class PeakActivity(BaseModel):
    """Peak activity metrics for a narrative."""
    date: str = Field(..., description="Date of peak activity")
    article_count: int = Field(..., description="Number of articles at peak")
    velocity: float = Field(..., description="Velocity at peak")


class LifecycleHistoryEntry(BaseModel):
    """Lifecycle history entry."""
    state: str = Field(..., description="Lifecycle state (emerging, rising, hot, cooling, dormant)")
    timestamp: str = Field(..., description="ISO timestamp when state changed")
    article_count: int = Field(..., description="Article count at time of change")
    velocity: float = Field(..., description="Velocity at time of change")


class NarrativeResponse(BaseModel):
    """Response model for a narrative."""
    theme: str = Field(..., description="Theme category (e.g., regulatory, defi_adoption)")
    title: str = Field(..., description="Generated narrative title")
    summary: str = Field(..., description="AI-generated narrative summary")
    entities: List[str] = Field(..., description="List of entities in this narrative")
    article_count: int = Field(..., description="Number of articles supporting this narrative")
    mention_velocity: float = Field(..., description="Articles per day rate")
    lifecycle: str = Field(..., description="Lifecycle stage: emerging, hot, mature, declining")
    lifecycle_state: Optional[str] = Field(default=None, description="New lifecycle state (emerging, rising, hot, cooling, dormant)")
    lifecycle_history: Optional[List[LifecycleHistoryEntry]] = Field(default=None, description="History of lifecycle state transitions")
    fingerprint: Optional[List[float]] = Field(default=None, description="Narrative fingerprint vector for similarity matching")
    momentum: Optional[str] = Field(default="unknown", description="Momentum trend: growing, declining, stable, or unknown")
    recency_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Freshness score (0-1), higher = more recent, 24h half-life")
    entity_relationships: Optional[List[Dict[str, Any]]] = Field(default=[], description="Top 5 entity co-occurrence pairs with weights: [{'a': 'SEC', 'b': 'Binance', 'weight': 3}]")
    first_seen: str = Field(..., description="ISO timestamp when narrative was first detected")
    last_updated: str = Field(..., description="ISO timestamp of last update")
    days_active: int = Field(default=1, description="Number of days narrative has been active")
    peak_activity: Optional[PeakActivity] = Field(default=None, description="Peak activity metrics")
    articles: List[Dict[str, Any]] = Field(default=[], description="Recent articles in this narrative")
    
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
                "recency_score": 0.607,
                "first_seen": "2025-10-01T19:30:00Z",
                "last_updated": "2025-10-06T14:20:00Z",
                "days_active": 6,
                "peak_activity": {
                    "date": "2025-10-05",
                    "article_count": 18,
                    "velocity": 4.2
                }
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
        
        # Convert to response models and fetch articles
        response_data = []
        for narrative in narratives:
            # Handle both old (updated_at) and new (last_updated) field names
            last_updated = narrative.get("last_updated") or narrative.get("updated_at")
            if last_updated:
                last_updated_str = last_updated.isoformat() if hasattr(last_updated, 'isoformat') else str(last_updated)
            else:
                # Fallback to current time if no timestamp
                from datetime import datetime, timezone as tz
                last_updated_str = datetime.now(tz.utc).isoformat()
            
            first_seen = narrative.get("first_seen") or narrative.get("created_at")
            if first_seen:
                first_seen_str = first_seen.isoformat() if hasattr(first_seen, 'isoformat') else str(first_seen)
            else:
                # Use last_updated as fallback
                first_seen_str = last_updated_str
            
            # Handle both old (story) and new (summary) field names
            summary = narrative.get("summary") or narrative.get("story", "")
            
            # Get timeline tracking fields
            days_active = narrative.get("days_active", 1)
            peak_activity = narrative.get("peak_activity")
            
            # Fetch articles for this narrative
            article_ids = narrative.get("article_ids", [])
            articles = await get_articles_for_narrative(article_ids, limit=20)
            
            # Get new lifecycle fields and normalize them
            lifecycle_state = narrative.get("lifecycle_state")
            
            # Normalize lifecycle_history: convert timestamps and rename mention_velocity to velocity
            lifecycle_history_raw = narrative.get("lifecycle_history")
            lifecycle_history = None
            if lifecycle_history_raw:
                lifecycle_history = []
                for entry in lifecycle_history_raw:
                    # Convert timestamp to ISO string if it's a datetime
                    timestamp = entry.get("timestamp")
                    if hasattr(timestamp, 'isoformat'):
                        timestamp_str = timestamp.isoformat()
                    else:
                        timestamp_str = str(timestamp)
                    
                    # Use 'velocity' if present, otherwise use 'mention_velocity'
                    velocity = entry.get("velocity", entry.get("mention_velocity", 0.0))
                    
                    lifecycle_history.append({
                        "state": entry.get("state", ""),
                        "timestamp": timestamp_str,
                        "article_count": entry.get("article_count", 0),
                        "velocity": velocity
                    })
            
            # Normalize fingerprint: extract vector if it's a dict with 'vector' field
            fingerprint_raw = narrative.get("fingerprint")
            fingerprint = None
            if fingerprint_raw:
                if isinstance(fingerprint_raw, dict):
                    # Old format: {'vector': [...], 'nucleus_entity': '...', ...}
                    fingerprint = fingerprint_raw.get("vector")
                elif isinstance(fingerprint_raw, list):
                    # New format: already a list
                    fingerprint = fingerprint_raw
            
            response_data.append({
                "theme": narrative.get("theme", ""),
                "title": narrative.get("title", narrative.get("theme", "")),  # Fallback to theme if no title
                "summary": summary,
                "entities": narrative.get("entities", []),
                "article_count": narrative.get("article_count", 0),
                "mention_velocity": narrative.get("mention_velocity", 0.0),
                "lifecycle": narrative.get("lifecycle", "emerging"),
                "lifecycle_state": lifecycle_state,
                "lifecycle_history": lifecycle_history,
                "fingerprint": fingerprint,
                "momentum": narrative.get("momentum", "unknown"),
                "recency_score": narrative.get("recency_score", 0.0),
                "entity_relationships": narrative.get("entity_relationships", []),
                "first_seen": first_seen_str,
                "last_updated": last_updated_str,
                "days_active": days_active,
                "peak_activity": peak_activity,
                "articles": articles,
                # Add backward compatibility fields for old UI
                "updated_at": last_updated_str,
                "story": summary
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


@router.get("/{narrative_id}/timeline", response_model=List[TimelineSnapshot])
async def get_narrative_timeline_endpoint(narrative_id: str):
    """
    Get timeline data for a specific narrative.
    
    Returns daily snapshots showing how the narrative evolved over time,
    including article counts, entities, and velocity metrics.
    
    This data is suitable for charting narrative growth and activity patterns.
    
    Args:
        narrative_id: MongoDB ObjectId of the narrative
    
    Returns:
        List of timeline snapshots, one per day the narrative was active
    
    Raises:
        404: If narrative not found
        500: If database error occurs
    """
    try:
        timeline_data = await get_narrative_timeline(narrative_id)
        
        if timeline_data is None:
            raise HTTPException(status_code=404, detail="Narrative not found")
        
        return [TimelineSnapshot(**snapshot) for snapshot in timeline_data]
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error fetching narrative timeline: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch timeline data")
