"""
Article API endpoints.
"""

from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from bson import ObjectId

from ....db.mongodb_models import (
    ArticleInDB,
    ArticleResponse,
    SentimentAnalysis,
    SentimentLabel,
)
from ....services.article_service import article_service
from ....core.security import get_current_user
from ....models.user import UserInDB

router = APIRouter()


@router.get("/", response_model=List[ArticleResponse])
async def list_articles(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of items per page"),
    source_id: Optional[str] = Query(None, description="Filter by source ID"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
    keywords: Optional[str] = Query(
        None, description="Comma-separated list of keywords"
    ),
    min_sentiment: Optional[float] = Query(
        None, ge=-1.0, le=1.0, description="Minimum sentiment score (-1 to 1)"
    ),
    max_sentiment: Optional[float] = Query(
        None, ge=-1.0, le=1.0, description="Maximum sentiment score (-1 to 1)"
    ),
    current_user: UserInDB = Depends(get_current_user),
):
    """
    List articles with filtering and pagination.
    """
    # Parse keywords if provided
    keyword_list = [k.strip() for k in keywords.split(",")] if keywords else None

    # Adjust end date to end of day if only date is provided
    if end_date:
        end_date = end_date.replace(hour=23, minute=59, second=59)

    articles, total = await article_service.list_articles(
        skip=skip,
        limit=limit,
        source_id=source_id,
        start_date=start_date,
        end_date=end_date,
        keywords=keyword_list,
        min_sentiment=min_sentiment,
        max_sentiment=max_sentiment,
    )

    # Add X-Total-Count header for pagination
    response = JSONResponse(
        content=[article.model_dump(by_alias=True) for article in articles]
    )
    response.headers["X-Total-Count"] = str(total)
    return response


@router.get("/recent")
async def get_recent_articles(
    limit: int = Query(100, ge=1, le=200, description="Number of recent articles to return"),
    current_user: UserInDB = Depends(get_current_user),
):
    """
    Get recent articles in chronological order with clickable links.
    Returns title, url, source, published_at, and first 3 entities.
    """
    from ....db.mongodb import mongo_manager
    
    db = await mongo_manager.get_async_database()
    articles_collection = db.articles
    entity_mentions_collection = db.entity_mentions
    
    # Fetch recent articles sorted by published_at DESC
    cursor = articles_collection.find(
        {},
        {
            "title": 1,
            "url": 1,
            "source": 1,
            "published_at": 1,
            "_id": 1
        }
    ).sort("published_at", -1).limit(limit)
    
    articles = []
    async for article in cursor:
        article_id = str(article["_id"])
        
        # Fetch entities for this article (first 3)
        entity_cursor = entity_mentions_collection.find(
            {"article_id": article_id},
            {"entity_name": 1, "entity_type": 1}
        ).limit(3)
        
        entities = []
        async for entity in entity_cursor:
            entities.append({
                "name": entity.get("entity_name", ""),
                "type": entity.get("entity_type", "")
            })
        
        articles.append({
            "id": article_id,
            "title": article.get("title", ""),
            "url": article.get("url", ""),
            "source": article.get("source", ""),
            "published_at": article.get("published_at").isoformat() if article.get("published_at") else None,
            "entities": entities
        })
    
    return {"articles": articles, "total": len(articles)}


@router.get("/search", response_model=List[ArticleResponse])
async def search_articles(
    q: str = Query(..., min_length=2, description="Search query"),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of items per page"),
    source_id: Optional[str] = Query(None, description="Filter by source ID"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
    current_user: UserInDB = Depends(get_current_user),
):
    """
    Search articles by text query.
    """
    # Adjust end date to end of day if only date is provided
    if end_date:
        end_date = end_date.replace(hour=23, minute=59, second=59)

    articles, total = await article_service.search_articles(
        query=q,
        skip=skip,
        limit=limit,
        source_id=source_id,
        start_date=start_date,
        end_date=end_date,
    )

    # Add X-Total-Count header for pagination
    response = JSONResponse(
        content=[article.model_dump(by_alias=True) for article in articles]
    )
    response.headers["X-Total-Count"] = str(total)
    return response


@router.get("/{article_id}", response_model=ArticleResponse)
async def get_article(
    article_id: str, current_user: UserInDB = Depends(get_current_user)
):
    """
    Get a single article by ID.
    """
    if not ObjectId.is_valid(article_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid article ID format"
        )

    article = await article_service.get_article(article_id)
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Article not found"
        )

    return article


@router.get("/trending/keywords", response_model=List[dict])
async def get_trending_keywords(
    hours: int = Query(24, ge=1, le=168, description="Time window in hours (1-168)"),
    limit: int = Query(10, ge=1, le=50, description="Number of keywords to return"),
    min_mentions: int = Query(2, ge=1, description="Minimum number of mentions"),
    current_user: UserInDB = Depends(get_current_user),
):
    """
    Get trending keywords from recent articles.
    """
    # Calculate time window
    time_window = datetime.utcnow() - timedelta(hours=hours)

    # This is a simplified implementation - in a real app, you might want to use
    # a more sophisticated approach like TF-IDF or a dedicated search engine
    pipeline = [
        {"$match": {"published_at": {"$gte": time_window}}},
        {"$unwind": "$keywords"},
        {"$group": {"_id": "$keywords", "count": {"$sum": 1}}},
        {"$match": {"count": {"$gte": min_mentions}}},
        {"$sort": {"count": -1}},
        {"$limit": limit},
        {"$project": {"keyword": "$_id", "count": 1, "_id": 0}},
    ]

    collection = await article_service._get_collection()
    cursor = collection.aggregate(pipeline)
    results = await cursor.to_list(length=limit)

    return results


@router.get("/sentiment/trends", response_model=dict)
async def get_sentiment_trends(
    hours: int = Query(24, ge=1, le=168, description="Time window in hours (1-168)"),
    interval: int = Query(1, ge=1, le=24, description="Time interval in hours"),
    current_user: UserInDB = Depends(get_current_user),
):
    """
    Get sentiment trends over time.
    """
    # Calculate time window
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours)

    # Generate time buckets
    time_buckets = []
    current = start_time.replace(minute=0, second=0, microsecond=0)
    while current <= end_time:
        time_buckets.append(current)
        current += timedelta(hours=interval)

    # If the last bucket is too far in the future, remove it
    if time_buckets and time_buckets[-1] > end_time:
        time_buckets = time_buckets[:-1]

    if not time_buckets:
        return {"timestamps": [], "scores": [], "counts": []}

    # Build the aggregation pipeline
    pipeline = [
        {
            "$match": {
                "published_at": {"$gte": start_time, "$lte": end_time},
                "sentiment.score": {"$exists": True},
            }
        },
        {
            "$project": {
                "timestamp": "$published_at",
                "score": "$sentiment.score",
                "time_bucket": {
                    "$let": {
                        "vars": {
                            "time_diff": {"$subtract": ["$published_at", start_time]},
                            "interval_ms": interval * 60 * 60 * 1000,
                        },
                        "in": {
                            "$add": [
                                start_time,
                                {
                                    "$multiply": [
                                        {
                                            "$floor": {
                                                "$divide": [
                                                    "$$time_diff",
                                                    "$$interval_ms",
                                                ]
                                            }
                                        },
                                        "$$interval_ms",
                                    ]
                                },
                            ]
                        },
                    }
                },
            }
        },
        {
            "$group": {
                "_id": "$time_bucket",
                "avg_score": {"$avg": "$score"},
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"_id": 1}},
    ]

    collection = await article_service._get_collection()
    cursor = collection.aggregate(pipeline)
    results = await cursor.to_list(length=None)

    # Prepare the response
    timestamps = []
    scores = []
    counts = []

    # Fill in the data points
    for bucket in time_buckets:
        timestamps.append(bucket.isoformat())

        # Find the matching result for this bucket
        match = next((r for r in results if r["_id"] == bucket), None)
        if match:
            scores.append(round(match["avg_score"], 3))
            counts.append(match["count"])
        else:
            scores.append(0.0)
            counts.append(0)

    return {"timestamps": timestamps, "scores": scores, "counts": counts}


@router.get("/sources/stats", response_model=List[dict])
async def get_source_stats(
    hours: int = Query(24, ge=1, le=168, description="Time window in hours (1-168)"),
    limit: int = Query(10, ge=1, le=50, description="Number of sources to return"),
    current_user: UserInDB = Depends(get_current_user),
):
    """
    Get statistics by source.
    """
    # Calculate time window
    time_window = datetime.utcnow() - timedelta(hours=hours)

    pipeline = [
        {"$match": {"published_at": {"$gte": time_window}}},
        {
            "$group": {
                "_id": "$source.id",
                "source_name": {"$first": "$source.name"},
                "count": {"$sum": 1},
                "avg_sentiment": {"$avg": "$sentiment.score"},
            }
        },
        {"$match": {"avg_sentiment": {"$ne": None}}},
        {"$sort": {"count": -1}},
        {"$limit": limit},
        {
            "$project": {
                "source_id": "$_id",
                "source_name": 1,
                "article_count": "$count",
                "avg_sentiment": {"$round": ["$avg_sentiment", 3]},
                "_id": 0,
            }
        },
    ]

    collection = await article_service._get_collection()
    cursor = collection.aggregate(pipeline)
    results = await cursor.to_list(length=limit)

    return results
