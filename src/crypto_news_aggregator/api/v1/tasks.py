"""Task-related API endpoints."""
import logging
from fastapi import APIRouter, Depends, status, Response, HTTPException
from fastapi.responses import JSONResponse
from typing import Any, Optional, Type, Callable, Dict, List, Union, TypeVar
from pydantic import BaseModel, ConfigDict, field_serializer
import json
from celery.result import AsyncResult as CeleryAsyncResult
from src.crypto_news_aggregator.tasks import fetch_news, analyze_sentiment, update_trends

# Set up logging
logger = logging.getLogger(__name__)
router = APIRouter(tags=["tasks"])

def check_serializable(obj: Any) -> bool:
    """Check if an object is JSON serializable."""
    try:
        json.dumps(obj, default=str)
        return True
    except (TypeError, ValueError) as e:
        return False

def is_serializable(obj: Any) -> bool:
    """Check if an object is JSON serializable."""
    try:
        json.dumps(obj, default=str)
        return True
    except (TypeError, ValueError):
        return False

def has_non_serializable(obj: Any, path: str = "") -> tuple[bool, str]:
    """
    Recursively check if an object contains any non-serializable values.
    
    Args:
        obj: The object to check
        path: Current path in the object (for error messages)
        
    Returns:
        Tuple of (has_non_serializable, error_message)
    """
    # First, check if the object is a function or method
    if callable(obj):
        return True, f"Callable object of type {type(obj).__name__} found at path: {path or 'root'}"
    
    # Check basic types that are always serializable
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return False, ""
    
    # Check for containers
    if isinstance(obj, (list, tuple, set)):
        for i, item in enumerate(obj):
            has_issue, msg = has_non_serializable(item, f"{path}[{i}]")
            if has_issue:
                return True, msg
        return False, ""
    
    # Check for dictionaries
    if isinstance(obj, dict):
        for k, v in obj.items():
            # Check the key first
            if not isinstance(k, (str, int, float, bool)) and k is not None:
                return True, f"Non-serializable key of type {type(k).__name__} found at path: {path}"
            
            # Check the value
            new_path = f"{path}.{k}" if path else str(k)
            has_issue, msg = has_non_serializable(v, new_path)
            if has_issue:
                return True, msg
        return False, ""
    
    # For other types, try to serialize them
    try:
        json.dumps(obj, default=str)
        return False, ""
    except (TypeError, ValueError):
        # If we can't serialize it, it's not serializable
        return True, f"Non-serializable object of type {type(obj).__name__} found at path: {path or 'root'}"

class TaskResponse(BaseModel):
    """Response model for task status."""
    task_id: str
    status: str
    result: Optional[Any] = None
    error: Optional[str] = None
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_encoders={
            # Add custom encoders here if needed
            "default": lambda x: str(x)  # Default to string for non-serializable types
        }
    )
    
    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Override model_dump to ensure all fields are serializable."""
        data = super().model_dump(**kwargs)
        return make_serializable(data)
    
    @field_serializer('result')
    def serialize_result(self, v: Any) -> Any:
        """Custom serializer for the result field."""
        if v is None:
            return None
        try:
            # Try to serialize directly
            json.dumps(v, default=str)
            return v
        except (TypeError, ValueError):
            # Fall back to string representation if not directly serializable
            return str(v)

def get_async_result_class() -> Type[CeleryAsyncResult]:
    """Get the AsyncResult class to use.
    
    This function allows us to override the AsyncResult class in tests.
    """
    return CeleryAsyncResult



def make_serializable(obj: Any) -> Any:
    """Recursively convert non-serializable objects to strings."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    elif isinstance(obj, (list, tuple, set)):
        return [make_serializable(item) for item in obj]
    elif isinstance(obj, dict):
        return {str(k): make_serializable(v) for k, v in obj.items()}
    elif hasattr(obj, '__dict__'):
        return {str(k): make_serializable(v) for k, v in obj.__dict__.items()}
    elif hasattr(obj, '__slots__'):
        return {slot: make_serializable(getattr(obj, slot, None)) for slot in obj.__slots__}
    else:
        try:
            # Try to serialize the object directly first
            json.dumps(obj, default=str)
            return obj
        except (TypeError, ValueError):
            # For all other types, convert to string
            return str(obj)

class SerializableResponse(JSONResponse):
    """Custom JSON response that handles non-serializable objects."""
    
    def render(self, content: Any) -> bytes:
        """
        Render the content to bytes, ensuring it's JSON serializable.
        
        Args:
            content: The content to serialize to JSON
            
        Returns:
            bytes: The serialized content as bytes
            
        Raises:
            ValueError: If content cannot be serialized to JSON
        """
        if content is None:
            return b""
            
        try:
            # First try to serialize using Pydantic's model_dump() if available
            if hasattr(content, 'model_dump'):
                content = content.model_dump()
            
            # Then apply our custom serialization
            serialized = make_serializable(content)
            
            # Use orjson for better performance if available
            if hasattr(self, 'render'):
                return super().render(serialized)
                
            # Fallback to standard JSON serialization
            return json.dumps(serialized, default=str).encode(self.charset)
            
        except Exception as e:
            logger.exception("Error serializing response")
            # Fall back to a safe error response
            error_content = {
                "error": "Error serializing response",
                "details": str(e),
                "type": type(e).__name__
            }
            return json.dumps(error_content, default=str).encode(self.charset)

@router.get("/tasks/{task_id}", response_class=SerializableResponse)
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
    logger.info(f"[ENDPOINT] Getting status for task {task_id}")
    logger.info(f"[ENDPOINT] Using async_result_class: {async_result_class}")
    
    # Create the AsyncResult instance using the injected class
    logger.info("[ENDPOINT] Creating AsyncResult instance...")
    task_result = async_result_class(task_id)
    logger.info(f"[ENDPOINT] Created AsyncResult instance: {task_result}")
    logger.info(f"[ENDPOINT] AsyncResult type: {type(task_result)}")
    
    # Prepare the base response
    response = {
        "task_id": task_id,
    }
    
    try:
        # Try to get the task status
        logger.info("[ENDPOINT] Getting task status...")
        task_status = task_result.status
        response["status"] = task_status
        logger.info(f"[ENDPOINT] Task status: {task_status}")
        logger.info(f"[ENDPOINT] AsyncResult details: id={getattr(task_result, 'id', 'N/A')}, status={getattr(task_result, 'status', 'N/A')}")
        
        # Check if task is ready, handling potential timeouts
        try:
            logger.info("[ENDPOINT] Checking if task is ready...")
            is_ready = task_result.ready()
            logger.info(f"[ENDPOINT] Task ready state: {is_ready}")
            
        except TimeoutError as e:
            logger.warning(f"[ENDPOINT] Task status check timed out: {str(e)}")
            response["status"] = "TIMEOUT"
            response["error"] = str(e) or "Task timed out"
            logger.info(f"[ENDPOINT] Returning timeout response: {response}")
            return make_serializable(response)
            
        except Exception as e:
            logger.error(f"[ENDPOINT] Error checking if task is ready: {str(e)}", exc_info=True)
            response["status"] = "FAILURE"
            response["error"] = f"Error checking task status: {str(e)}"
            return make_serializable(response)
            
        # If we get here, no timeout occurred
        logger.info(f"[ENDPOINT] Task ready state: {is_ready}")
        
    except ConnectionError as e:
        # Handle connection errors
        error_msg = str(e) or "Failed to connect to message broker"
        logger.error(f"[ENDPOINT] Connection error getting task status: {error_msg}", exc_info=True)
        response["status"] = "FAILURE"
        response["error"] = error_msg
        return make_serializable(response)
        
    except Exception as e:
        # Handle other unexpected errors
        error_msg = f"Error getting task status: {str(e)}"
        logger.error(f"[ENDPOINT] Unexpected error: {error_msg}", exc_info=True)
        response["status"] = "FAILURE"
        response["error"] = error_msg
        return make_serializable(response)
        
    logger.info(f"[DEBUG] Initial response: {response}")
    
    if is_ready:
        try:
            result = task_result.result
            logger.info(f"[DEBUG] Task result type: {type(result)}")
            
            # First, check for non-serializable objects in the result
            has_issue, error_msg = has_non_serializable(result)
            
            if has_issue:
                logger.warning(f"[DEBUG] Non-serializable object found: {error_msg}")
                response["error"] = f"Task result is not JSON serializable: {error_msg}"
                # Remove any result to avoid serialization issues
                if "result" in response:
                    del response["result"]
            else:
                # If no non-serializable objects found, try to add the result
                try:
                    # Try to serialize the entire response with the result
                    test_response = response.copy()
                    test_response["result"] = result
                    json.dumps(test_response, default=str)
                    
                    # If we get here, the result is serializable
                    response["result"] = result
                    logger.info("[DEBUG] Successfully added result to response")
                except (TypeError, ValueError) as e:
                    logger.warning(f"[DEBUG] Serialization failed: {str(e)}")
                    response["error"] = "Task result is not JSON serializable"
                    if "result" in response:
                        del response["result"]
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"[DEBUG] Error getting task result: {error_msg}", exc_info=True)
            response["error"] = error_msg
            # Also ensure the status is set to FAILURE if it's not already
            if response.get("status") != "FAILURE":
                response["status"] = "FAILURE"
    
    logger.info(f"[DEBUG] Final response: {response}")
    return response

@router.post("/news/fetch", response_class=SerializableResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_news_fetch(source: Optional[str] = None):
    """
    Trigger a news fetch task
    """
    task = fetch_news.delay(source)
    return {
        "task_id": task.id,
        "status": "PENDING"
    }

@router.post("/sentiment/analyze/{article_id}", response_class=SerializableResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_sentiment_analysis(article_id: int):
    """
    Trigger sentiment analysis for a specific article
    """
    task = analyze_sentiment.delay(article_id)
    return {
        "task_id": task.id,
        "status": "PENDING"
    }

@router.post("/trends/update", response_class=SerializableResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_trends_update():
    """
    Trigger an update of the trends data
    """
    task = update_trends.delay()
    return {
        "task_id": task.id,
        "status": "PENDING"
    }
