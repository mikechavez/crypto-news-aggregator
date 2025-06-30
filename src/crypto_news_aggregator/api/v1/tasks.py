"""Task-related API endpoints."""
from fastapi import APIRouter, status
from typing import Any, Optional
from pydantic import BaseModel
from celery.result import AsyncResult

router = APIRouter(tags=["tasks"])

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
