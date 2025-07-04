"""Article-related API endpoints."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timedelta, timezone

router = APIRouter()

# Temporary models - will be moved to models.py later
class ArticleBase(BaseModel):
    """Base article model."""
    title: str
    url: str
    source: str
    published_at: datetime
    content: Optional[str] = None

class Article(ArticleBase):
    """Article model with ID."""
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Temporary data storage - will be replaced with database
articles_db = {}

@router.get("/", response_model=List[Article])
async def list_articles(
    limit: int = Query(10, ge=1, le=100, description="Number of articles to return"),
    offset: int = Query(0, ge=0, description="Number of articles to skip"),
    source: Optional[str] = None,
    days: int = Query(7, ge=1, description="Number of days to look back")
) -> List[Article]:
    """
    List articles with optional filtering by source and time range.
    """
    # In a real implementation, this would query the database
    filtered = list(articles_db.values())
    
    if source:
        filtered = [a for a in filtered if a.source.lower() == source.lower()]
    
    time_threshold = datetime.now(timezone.utc) - timedelta(days=days)
    filtered = [a for a in filtered if a.published_at >= time_threshold]
    
    return filtered[offset:offset + limit]

@router.get("/{article_id}", response_model=Article)
async def get_article(article_id: int) -> Article:
    """Get a single article by ID."""
    if article_id not in articles_db:
        raise HTTPException(status_code=404, detail="Article not found")
    return articles_db[article_id]
