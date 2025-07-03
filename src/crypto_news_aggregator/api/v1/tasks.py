"""Task-related API endpoints."""
import logging
from fastapi import APIRouter, Depends, status
from typing import Any, Optional, Type, Callable
from pydantic import BaseModel
from celery.result import AsyncResult as CeleryAsyncResult
from src.crypto_news_aggregator.tasks import fetch_news, analyze_sentiment, update_trends

# Set up logging
logger = logging.getLogger(__name__)
router = APIRouter(tags=["tasks"])

class TaskResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[Any] = None
    error: Optional[str] = None

def get_async_result_class() -> Type[CeleryAsyncResult]:
    """Get the AsyncResult class to use.
    
    This function allows us to override the AsyncResult class in tests.
    """
    return CeleryAsyncResult

@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task_status(
    task_id: str,
    async_result_class: Type[CeleryAsyncResult] = Depends(get_async_result_class)
):
    """
    Get the status of a background task by its ID.
    
    Args:
        task_id: The ID of the task to check
        async_result_class: The AsyncResult class to use (injected for testing)
    """
    logger.info(f"[DEBUG] Getting status for task {task_id}")
    
    # Create the AsyncResult instance using the injected class
    task_result = async_result_class(task_id)
    logger.info(f"[DEBUG] Created AsyncResult: id={task_result.id}, status={task_result.status}, ready={task_result.ready()}")
    
    # Prepare the response
    response = {
        "task_id": task_id,
        "status": task_result.status,
    }
    logger.info(f"[DEBUG] Initial response: {response}")
    
    # Add result if task is ready
    is_ready = task_result.ready()
    logger.info(f"[DEBUG] Task ready state: {is_ready}")
    
    if is_ready:
        try:
            result = task_result.result
            logger.info(f"[DEBUG] Task result: {result}")
            response["result"] = result
        except Exception as e:
            error_msg = str(e)
            logger.error(f"[DEBUG] Error getting task result: {error_msg}", exc_info=True)
            response["error"] = error_msg
            # Also ensure the status is set to FAILURE if it's not already
            if response.get("status") != "FAILURE":
                response["status"] = "FAILURE"
    
    logger.info(f"[DEBUG] Final response: {response}")
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
