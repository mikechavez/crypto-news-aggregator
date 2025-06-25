from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any, Optional
from pydantic import BaseModel
from ..tasks import fetch_news, analyze_sentiment, process_article, update_trends
from celery.result import AsyncResult

router = APIRouter(prefix="/api/v1", tags=["tasks"])

class TaskResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[Any] = None

@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task_status(task_id: str):
    """
    Get the status of a background task by its ID
    """
    task_result = AsyncResult(task_id)
    
    response = {
        "task_id": task_id,
        "status": task_result.status,
    }
    
    if task_result.ready():
        response["result"] = task_result.result
    
    return response

@router.post("/news/fetch", response_model=TaskResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_news_fetch(source: Optional[str] = None):
    """
    Trigger a news fetch task
    """
    task = fetch_news.delay(source)
    return {
        "task_id": task.id,
        "status": "PENDING"
    }

@router.post("/sentiment/analyze/{article_id}", response_model=TaskResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_sentiment_analysis(article_id: int):
    """
    Trigger sentiment analysis for a specific article
    """
    task = analyze_sentiment.delay(article_id)
    return {
        "task_id": task.id,
        "status": "PENDING"
    }

@router.post("/trends/update", response_model=TaskResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_trends_update():
    """
    Trigger an update of the trends data
    """
    task = update_trends.delay()
    return {
        "task_id": task.id,
        "status": "PENDING"
    }
