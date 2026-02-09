"""
Admin API Endpoints for Cost Monitoring

Provides endpoints for monitoring LLM API costs, cache performance,
and processing statistics.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Security

from ..core.auth import get_api_key
from ..db.mongodb import get_mongodb
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/health")
async def health_check():
    """Health check endpoint for admin routes"""
    return {"status": "ok", "service": "admin"}


@router.get("/api-costs/summary")
async def get_cost_summary(
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
    _api_key: str = Security(get_api_key)
) -> Dict[str, Any]:
    """
    Get monthly cost summary with projections.
    
    Returns:
        - month_to_date: Current month's total cost
        - projected_monthly: Projected end-of-month cost
        - days_elapsed: Days since start of month
        - cache_hit_rate: Percentage of cached responses
        - breakdown_by_operation: Costs by operation type
    """
    start_of_month = datetime.utcnow().replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    
    # Aggregate costs
    pipeline = [
        {"$match": {"timestamp": {"$gte": start_of_month}}},
        {"$group": {
            "_id": "$operation",
            "total_cost": {"$sum": "$cost"},
            "total_calls": {"$sum": 1},
            "cached_calls": {"$sum": {"$cond": ["$cached", 1, 0]}},
            "input_tokens": {"$sum": "$input_tokens"},
            "output_tokens": {"$sum": "$output_tokens"}
        }}
    ]
    
    results = await db.api_costs.aggregate(pipeline).to_list(None)
    
    # Calculate totals
    total_cost = sum(r["total_cost"] for r in results)
    total_calls = sum(r["total_calls"] for r in results)
    total_cached = sum(r["cached_calls"] for r in results)
    
    # Calculate projection
    days_elapsed = (datetime.utcnow() - start_of_month).days + 1
    days_in_month = 30
    projected_monthly = (total_cost / days_elapsed) * days_in_month if days_elapsed > 0 else 0
    
    # Cache hit rate
    cache_hit_rate = (total_cached / total_calls * 100) if total_calls > 0 else 0
    
    # Format breakdown
    breakdown = {
        r["_id"]: {
            "cost": round(r["total_cost"], 4),
            "calls": r["total_calls"],
            "cached_calls": r["cached_calls"],
            "input_tokens": r["input_tokens"],
            "output_tokens": r["output_tokens"]
        }
        for r in results
    }
    
    return {
        "month_to_date": round(total_cost, 2),
        "projected_monthly": round(projected_monthly, 2),
        "days_elapsed": days_elapsed,
        "total_calls": total_calls,
        "cached_calls": total_cached,
        "cache_hit_rate_percent": round(cache_hit_rate, 2),
        "breakdown_by_operation": breakdown
    }


@router.get("/api-costs/daily")
async def get_daily_costs(
    days: int = 7,
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
    _api_key: str = Security(get_api_key)
) -> Dict[str, Any]:
    """Get daily cost breakdown for the last N days"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    pipeline = [
        {"$match": {"timestamp": {"$gte": start_date}}},
        {"$group": {
            "_id": {
                "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
                "operation": "$operation"
            },
            "total_cost": {"$sum": "$cost"},
            "total_calls": {"$sum": 1},
            "cached_calls": {"$sum": {"$cond": ["$cached", 1, 0]}}
        }},
        {"$sort": {"_id.date": 1}}
    ]
    
    results = await db.api_costs.aggregate(pipeline).to_list(None)
    
    # Group by date
    daily_data: Dict[str, Dict[str, Any]] = {}
    for r in results:
        date = r["_id"]["date"]
        operation = r["_id"]["operation"]
        
        if date not in daily_data:
            daily_data[date] = {
                "date": date,
                "total_cost": 0,
                "total_calls": 0,
                "cached_calls": 0,
                "operations": {}
            }
        
        daily_data[date]["total_cost"] += r["total_cost"]
        daily_data[date]["total_calls"] += r["total_calls"]
        daily_data[date]["cached_calls"] += r["cached_calls"]
        daily_data[date]["operations"][operation] = {
            "cost": round(r["total_cost"], 4),
            "calls": r["total_calls"]
        }
    
    # Format response
    daily_list = [
        {
            **v,
            "total_cost": round(v["total_cost"], 2),
            "cache_hit_rate": round(
                (v["cached_calls"] / v["total_calls"] * 100) if v["total_calls"] > 0 else 0,
                2
            )
        }
        for v in daily_data.values()
    ]
    
    return {
        "days_requested": days,
        "daily_costs": daily_list,
        "total_cost": round(sum(d["total_cost"] for d in daily_list), 2)
    }


@router.get("/api-costs/by-model")
async def get_costs_by_model(
    days: int = 30,
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
    _api_key: str = Security(get_api_key)
) -> Dict[str, Any]:
    """Get cost breakdown by model"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    pipeline = [
        {"$match": {"timestamp": {"$gte": start_date}}},
        {"$group": {
            "_id": "$model",
            "total_cost": {"$sum": "$cost"},
            "total_calls": {"$sum": 1},
            "cached_calls": {"$sum": {"$cond": ["$cached", 1, 0]}},
            "input_tokens": {"$sum": "$input_tokens"},
            "output_tokens": {"$sum": "$output_tokens"}
        }},
        {"$sort": {"total_cost": -1}}
    ]
    
    results = await db.api_costs.aggregate(pipeline).to_list(None)
    
    models: List[Dict[str, Any]] = []
    for r in results:
        model_data = {
            "model": r["_id"],
            "total_cost": round(r["total_cost"], 2),
            "total_calls": r["total_calls"],
            "cached_calls": r["cached_calls"],
            "cache_hit_rate_percent": round(
                (r["cached_calls"] / r["total_calls"] * 100) if r["total_calls"] > 0 else 0,
                2
            ),
            "input_tokens": r["input_tokens"],
            "output_tokens": r["output_tokens"],
            "avg_cost_per_call": round(
                r["total_cost"] / r["total_calls"] if r["total_calls"] > 0 else 0,
                4
            )
        }
        models.append(model_data)
    
    return {
        "period_days": days,
        "models": models,
        "total_cost": round(sum(m["total_cost"] for m in models), 2)
    }


@router.get("/cache/stats")
async def get_cache_stats(
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
    _api_key: str = Security(get_api_key)
) -> Dict[str, Any]:
    """Get cache performance statistics"""
    # Get cache entry counts
    total_entries = await db.llm_cache.count_documents({})
    active_entries = await db.llm_cache.count_documents({
        "expires_at": {"$gt": datetime.utcnow()}
    })
    expired_entries = total_entries - active_entries
    
    # Get cache hits from api_costs (current month)
    start_of_month = datetime.utcnow().replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    
    pipeline = [
        {"$match": {"timestamp": {"$gte": start_of_month}}},
        {"$group": {
            "_id": "$cached",
            "count": {"$sum": 1}
        }}
    ]
    
    results = await db.api_costs.aggregate(pipeline).to_list(None)
    
    hits = 0
    misses = 0
    for r in results:
        if r["_id"]:  # cached = True
            hits = r["count"]
        else:  # cached = False
            misses = r["count"]
    
    total_requests = hits + misses
    hit_rate = (hits / total_requests * 100) if total_requests > 0 else 0
    
    return {
        "cache_entries": {
            "total": total_entries,
            "active": active_entries,
            "expired": expired_entries
        },
        "performance": {
            "cache_hits": hits,
            "cache_misses": misses,
            "total_requests": total_requests,
            "hit_rate_percent": round(hit_rate, 2)
        }
    }


@router.post("/cache/clear-expired")
async def clear_expired_cache(
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
    _api_key: str = Security(get_api_key)
) -> Dict[str, Any]:
    """Manually clear expired cache entries"""
    result = await db.llm_cache.delete_many({
        "expires_at": {"$lt": datetime.utcnow()}
    })
    
    return {
        "deleted_count": result.deleted_count,
        "message": f"Cleared {result.deleted_count} expired cache entries"
    }


@router.get("/processing/stats")
async def get_processing_stats(
    days: int = 7,
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
    _api_key: str = Security(get_api_key)
) -> Dict[str, Any]:
    """
    Get article processing statistics.
    Shows LLM vs simple extraction usage.
    """
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get article counts by source
    pipeline = [
        {"$match": {"created_at": {"$gte": start_date}}},
        {"$group": {
            "_id": "$source",
            "count": {"$sum": 1}
        }},
        {"$sort": {"count": -1}}
    ]
    
    article_results = await db.articles.aggregate(pipeline).to_list(None)
    
    # Get entity extraction counts (LLM has confidence >= 0.85, regex < 0.85)
    entity_pipeline = [
        {"$match": {"created_at": {"$gte": start_date}}},
        {"$group": {
            "_id": {
                "source": "$source",
                "method": {
                    "$cond": [
                        {"$gte": ["$confidence", 0.85]},
                        "llm",
                        "regex"
                    ]
                }
            },
            "count": {"$sum": 1}
        }}
    ]
    
    entity_results = await db.entity_mentions.aggregate(entity_pipeline).to_list(None)
    
    # Combine results
    source_stats: Dict[str, Dict[str, Any]] = {}
    for r in article_results:
        source = r["_id"]
        if source is None:
            source = "unknown"
        source_stats[source] = {
            "source": source,
            "total_articles": r["count"],
            "llm_extractions": 0,
            "simple_extractions": 0
        }
    
    for r in entity_results:
        source = r["_id"]["source"]
        if source is None:
            source = "unknown"
        method = r["_id"]["method"]
        
        if source in source_stats:
            if method == "llm":
                source_stats[source]["llm_extractions"] = r["count"]
            else:
                source_stats[source]["simple_extractions"] = r["count"]
    
    # Calculate percentages
    for stats in source_stats.values():
        total = stats["llm_extractions"] + stats["simple_extractions"]
        stats["llm_percentage"] = round(
            (stats["llm_extractions"] / total * 100) if total > 0 else 0,
            1
        )
    
    return {
        "period_days": days,
        "sources": sorted(
            source_stats.values(),
            key=lambda x: x["total_articles"],
            reverse=True
        ),
        "summary": {
            "total_articles": sum(s["total_articles"] for s in source_stats.values()),
            "total_llm_extractions": sum(s["llm_extractions"] for s in source_stats.values()),
            "total_simple_extractions": sum(s["simple_extractions"] for s in source_stats.values())
        }
    }


# ==================== BRIEFING TRIGGER ENDPOINTS ====================


from pydantic import BaseModel
from fastapi import HTTPException


class TaskResponse(BaseModel):
    """Response model for task trigger endpoints."""
    task_id: str
    task_name: str
    kwargs: dict
    message: str


@router.post("/trigger-briefing", response_model=TaskResponse)
async def trigger_briefing(
    briefing_type: str = "morning",
    is_smoke: bool = False
) -> TaskResponse:
    """
    Manually trigger a briefing generation task for testing.

    This endpoint is useful for verifying the briefing pipeline works
    before scheduled runs, especially after deployments.

    Args:
        briefing_type: "morning" or "evening"
        is_smoke: If True, generates but doesn't publish (for testing)

    Returns:
        Task ID and details for monitoring in worker logs

    Usage:
        POST /admin/trigger-briefing?briefing_type=morning&is_smoke=true

    Success response:
        {
            "task_id": "abc123...",
            "task_name": "generate_morning_briefing",
            "kwargs": {"is_smoke": true},
            "message": "✅ Morning briefing task queued. Check celery-worker logs for task_id=abc123..."
        }
    """
    from crypto_news_aggregator.tasks.briefing_tasks import (
        generate_morning_briefing_task,
        generate_evening_briefing_task
    )

    # Validate briefing type
    if briefing_type not in ["morning", "evening"]:
        raise HTTPException(
            status_code=400,
            detail="briefing_type must be 'morning' or 'evening'"
        )

    # Select task based on type
    task = (
        generate_morning_briefing_task
        if briefing_type == "morning"
        else generate_evening_briefing_task
    )

    # Queue the task
    try:
        result = task.apply_async(kwargs={'is_smoke': is_smoke})
        logger.info(
            f"🔬 Manual briefing trigger: {briefing_type} briefing "
            f"(is_smoke={is_smoke}) - task_id={result.id}"
        )

        return TaskResponse(
            task_id=result.id,
            task_name=task.name,
            kwargs={"is_smoke": is_smoke},
            message=(
                f"✅ {briefing_type.capitalize()} briefing task queued. "
                f"Check celery-worker logs for task_id={result.id}"
            )
        )
    except Exception as e:
        logger.error(f"Failed to queue briefing task: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to queue task: {str(e)}"
        )
