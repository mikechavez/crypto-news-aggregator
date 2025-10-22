"""
Signals API endpoints for trending entity detection.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from fastapi import APIRouter, Query, HTTPException
from typing import List, Dict, Any, Optional
from bson import ObjectId

from ....db.operations.signal_scores import get_trending_entities
from ....core.redis_rest_client import redis_client
from ....db.mongodb import mongo_manager

router = APIRouter()
logger = logging.getLogger(__name__)

# In-memory cache as fallback when Redis is not available
_memory_cache: Dict[str, tuple[Any, datetime]] = {}
_cache_duration = timedelta(seconds=60)  # Cache for 60 seconds

# In-memory cache for pre-computed signal data
_signals_cache: Dict[str, tuple[Any, datetime]] = {}
_signals_cache_ttl = timedelta(minutes=5)  # 5 minute TTL


def get_from_cache(cache_key: str) -> Optional[Any]:
    """
    Get data from cache (Redis or in-memory fallback).
    
    Args:
        cache_key: The cache key to retrieve
        
    Returns:
        Cached data if available and fresh, None otherwise
    """
    # Try Redis first
    if redis_client.enabled:
        try:
            cached_result = redis_client.get(cache_key)
            if cached_result:
                try:
                    return json.loads(cached_result)
                except (json.JSONDecodeError, TypeError):
                    pass
        except Exception:
            # If Redis fails, fall through to in-memory cache
            pass
    
    # Fallback to in-memory cache
    if cache_key in _memory_cache:
        cached_data, cached_time = _memory_cache[cache_key]
        if datetime.now() - cached_time < _cache_duration:
            return cached_data
        else:
            # Remove expired entry
            del _memory_cache[cache_key]
    
    return None


def set_in_cache(cache_key: str, data: Any, ttl_seconds: int = 120):
    """
    Set data in cache (Redis or in-memory fallback).
    
    Args:
        cache_key: The cache key to set
        data: The data to cache
        ttl_seconds: Time to live in seconds (default 120)
    """
    # Try Redis first
    if redis_client.enabled:
        try:
            redis_client.set(cache_key, json.dumps(data), ex=ttl_seconds)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to cache in Redis: {e}")
    
    # Clean up old entries BEFORE adding new one (keep cache size manageable)
    if len(_memory_cache) >= 100:
        now = datetime.now()
        expired_keys = [
            key for key, (_, timestamp) in _memory_cache.items()
            if now - timestamp >= _cache_duration
        ]
        for key in expired_keys:
            del _memory_cache[key]
    
    # Always set in memory cache as fallback
    _memory_cache[cache_key] = (data, datetime.now())


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


async def get_recent_articles_for_entity(entity: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Fetch recent articles mentioning a specific entity.
    
    Args:
        entity: The entity name to search for
        limit: Maximum number of articles to return (default 5)
    
    Returns:
        List of article dicts with title, url, source, published_at
    """
    db = await mongo_manager.get_async_database()
    
    # First, get article IDs from entity_mentions (these are MongoDB ObjectIds)
    mentions_collection = db.entity_mentions
    cursor = mentions_collection.find(
        {"entity": entity}
    ).sort("timestamp", -1).limit(limit * 2)  # Get more mentions to ensure we have enough unique articles
    
    article_object_ids = []
    seen_ids = set()
    async for mention in cursor:
        article_id = mention.get("article_id")
        if article_id and article_id not in seen_ids:
            try:
                # Convert string to ObjectId if needed
                if isinstance(article_id, str):
                    article_object_ids.append(ObjectId(article_id))
                else:
                    article_object_ids.append(article_id)
                seen_ids.add(article_id)
                if len(article_object_ids) >= limit:
                    break
            except Exception:
                continue
    
    if not article_object_ids:
        return []
    
    # Fetch article details using _id field
    articles_collection = db.articles
    cursor = articles_collection.find(
        {"_id": {"$in": article_object_ids}}
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


@router.get("")
async def get_signals() -> Dict[str, Any]:
    """
    Get top 20 trending signals sorted by score descending.
    
    Results are cached in-memory for 5 minutes to reduce database load.
    
    Returns:
        List of top 20 signals with entity, score, and metadata
    """
    cache_key = "signals:top20"
    
    # Check in-memory cache
    if cache_key in _signals_cache:
        cached_data, cached_time = _signals_cache[cache_key]
        if datetime.now() - cached_time < _signals_cache_ttl:
            return cached_data
        else:
            # Remove expired entry
            del _signals_cache[cache_key]
    
    # Cache miss - fetch from database
    try:
        db = await mongo_manager.get_async_database()
        collection = db.signal_scores
        
        # Define async function to fetch signals
        async def fetch_signals():
            cursor = collection.find({}).sort("score", -1).limit(20)
            signals = []
            async for signal in cursor:
                signals.append({
                    "entity": signal.get("entity", ""),
                    "entity_type": signal.get("entity_type", ""),
                    "score": signal.get("score", 0.0),
                    "velocity": signal.get("velocity", 0.0),
                    "source_count": signal.get("source_count", 0),
                    "sentiment": signal.get("sentiment", {}),
                    "is_emerging": signal.get("is_emerging", False),
                    "narrative_ids": signal.get("narrative_ids", []),
                    "first_seen": signal.get("first_seen").isoformat() if signal.get("first_seen") else None,
                    "last_updated": signal.get("last_updated").isoformat() if signal.get("last_updated") else None,
                })
            return signals
        
        # Define async function to count narratives for entities
        async def fetch_narrative_counts(entity_list):
            narrative_counts = await db.narratives.aggregate([
                {"$match": {"entities": {"$in": entity_list}}},
                {"$unwind": "$entities"},
                {"$match": {"entities": {"$in": entity_list}}},
                {"$group": {"_id": "$entities", "count": {"$sum": 1}}}
            ]).to_list(length=None)
            
            counts = {}
            for doc in narrative_counts:
                counts[doc["_id"]] = doc["count"]
            return counts
        
        # First, get entity list from top 20 signals (lightweight query)
        cursor = collection.find({}, {"entity": 1}).sort("score", -1).limit(20)
        entity_list = []
        async for doc in cursor:
            entity_list.append(doc.get("entity", ""))
        
        # Fetch signals and narrative counts in parallel using asyncio.gather
        signals, narrative_counts = await asyncio.gather(
            fetch_signals(),
            fetch_narrative_counts(entity_list)
        )
        
        # Merge narrative_count into each signal
        for signal in signals:
            entity = signal["entity"]
            signal["narrative_count"] = narrative_counts.get(entity, 0)
        
        response = {
            "count": len(signals),
            "signals": signals,
            "cached_at": datetime.now().isoformat(),
        }
        
        # Store in cache with current timestamp
        _signals_cache[cache_key] = (response, datetime.now())
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch signals: {str(e)}"
        )


async def get_recent_articles_batch(entities: List[str], limit_per_entity: int = 5) -> Dict[str, List[Dict[str, Any]]]:
    """
    Batch fetch recent articles for multiple entities using parallel queries.
    Uses the existing indexed get_recent_articles_for_entity function in parallel.
    
    Args:
        entities: List of entity names to fetch articles for
        limit_per_entity: Maximum number of articles per entity (default 5)
    
    Returns:
        Dict mapping entity name to list of article dicts
    """
    if not entities:
        return {}
    
    import asyncio
    
    # Fetch articles for all entities in parallel using existing optimized function
    # This uses the entity+timestamp compound index efficiently
    tasks = [get_recent_articles_for_entity(entity, limit=limit_per_entity) for entity in entities]
    results = await asyncio.gather(*tasks)
    
    # Map results back to entities
    return {entity: articles for entity, articles in zip(entities, results)}


@router.get("/trending")
async def get_trending_signals(
    limit: int = Query(default=50, ge=1, le=100, description="Maximum number of results"),
    min_score: float = Query(default=0.0, ge=0.0, le=10.0, description="Minimum signal score"),
    entity_type: Optional[str] = Query(default=None, description="Filter by entity type (ticker, project, event)"),
    timeframe: str = Query(default="7d", description="Time window for scoring (24h, 7d, or 30d)"),
) -> Dict[str, Any]:
    """
    Get trending entities based on signal scores for a specific timeframe.
    
    Signal scores are calculated based on:
    - Velocity: Rate of mentions over time
    - Source diversity: Number of unique sources
    - Sentiment: Average sentiment and divergence
    
    Results are cached for 2 minutes.
    
    Args:
        limit: Maximum number of results (1-100, default 50)
        min_score: Minimum signal score threshold (0-10, default 0)
        entity_type: Filter by entity type (optional)
        timeframe: Time window for scoring (24h, 7d, or 30d, default 7d)
    
    Returns:
        List of trending entities with signal scores for the specified timeframe
    """
    # Validate entity_type if provided
    if entity_type and entity_type not in ["ticker", "project", "event"]:
        raise HTTPException(
            status_code=400,
            detail="entity_type must be one of: ticker, project, event"
        )
    
    # Validate timeframe
    if timeframe not in ["24h", "7d", "30d"]:
        raise HTTPException(
            status_code=400,
            detail="timeframe must be one of: 24h, 7d, 30d"
        )
    
    # Build cache key including timeframe
    cache_key = f"signals:trending:{limit}:{min_score}:{entity_type or 'all'}:{timeframe}"
    
    # Try to get from cache (Redis or in-memory)
    cached_result = get_from_cache(cache_key)
    if cached_result is not None:
        return cached_result
    
    # Map timeframe to field names
    field_map = {
        "24h": {"score": "score_24h", "velocity": "velocity_24h"},
        "7d": {"score": "score_7d", "velocity": "velocity_7d"},
        "30d": {"score": "score_30d", "velocity": "velocity_30d"},
    }
    
    # Fetch trending entities
    try:
        start_time = time.time()
        query_count = 0
        
        # Query 1: Get trending entities
        trending = await get_trending_entities(
            limit=limit,
            min_score=min_score,
            entity_type=entity_type,
            timeframe=timeframe,
        )
        query_count += 1
        fetch_time = time.time() - start_time
        logger.info(f"[Signals] Fetched {len(trending)} trending entities in {fetch_time:.3f}s")
        
        # Collect all unique narrative IDs and entities for batch fetching
        all_narrative_ids = set()
        entities = []
        for signal in trending:
            narrative_ids = signal.get("narrative_ids", [])
            all_narrative_ids.update(narrative_ids)
            entities.append(signal["entity"])
        
        # Query 2: Batch fetch all narratives in one query
        batch_start = time.time()
        narratives_list = await get_narrative_details(list(all_narrative_ids))
        narratives_by_id = {n["id"]: n for n in narratives_list}
        query_count += 1
        logger.info(f"[Signals] Batch fetched {len(narratives_list)} narratives in {time.time() - batch_start:.3f}s")
        
        # Query 3: Batch fetch all articles in one query
        batch_start = time.time()
        articles_by_entity = await get_recent_articles_batch(entities, limit_per_entity=5)
        query_count += 1
        total_articles = sum(len(articles) for articles in articles_by_entity.values())
        logger.info(f"[Signals] Batch fetched {total_articles} articles for {len(entities)} entities in {time.time() - batch_start:.3f}s")
        
        # Build response with pre-fetched data
        signals_with_narratives = []
        for signal in trending:
            narrative_ids = signal.get("narrative_ids", [])
            narratives = [narratives_by_id[nid] for nid in narrative_ids if nid in narratives_by_id]
            
            # Get pre-fetched articles for this entity
            recent_articles = articles_by_entity.get(signal["entity"], [])
            
            # Get timeframe-specific score and velocity
            score_field = field_map[timeframe]["score"]
            velocity_field = field_map[timeframe]["velocity"]
            
            signals_with_narratives.append({
                "entity": signal["entity"],
                "entity_type": signal["entity_type"],
                "signal_score": signal.get(score_field, signal.get("score", 0.0)),
                "velocity": signal.get(velocity_field, signal.get("velocity", 0.0)),
                "source_count": signal["source_count"],
                "sentiment": signal["sentiment"],
                "is_emerging": signal.get("is_emerging", False),
                "narratives": narratives,
                "recent_articles": recent_articles,
                "first_seen": signal["first_seen"].isoformat() if signal.get("first_seen") else None,
                "last_updated": signal["last_updated"].isoformat() if signal.get("last_updated") else None,
            })
        
        # Format response
        total_time = time.time() - start_time
        payload_size = len(json.dumps(signals_with_narratives)) / 1024  # KB
        
        response = {
            "count": len(trending),
            "filters": {
                "limit": limit,
                "min_score": min_score,
                "entity_type": entity_type,
                "timeframe": timeframe,
            },
            "signals": signals_with_narratives,
            "performance": {
                "total_time_seconds": round(total_time, 3),
                "query_count": query_count,
                "payload_size_kb": round(payload_size, 2),
            }
        }
        
        logger.info(f"[Signals] Total request time: {total_time:.3f}s, Queries: {query_count}, Payload: {payload_size:.2f}KB")
        
        # Cache for 2 minutes (120 seconds) using Redis or in-memory fallback
        set_in_cache(cache_key, response, ttl_seconds=120)
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch trending signals: {str(e)}"
        )
