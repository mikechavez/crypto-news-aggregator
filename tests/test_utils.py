"""Test utilities for the Crypto News Aggregator test suite."""
from typing import Any, Dict, Optional
from unittest.mock import MagicMock


class MockAsyncResult:
    """A mock implementation of Celery's AsyncResult for testing.
    
    This class provides a consistent way to mock Celery's AsyncResult in tests,
    allowing for easy testing of task status checking and result retrieval.
    """
    def __init__(self, task_id: str, **kwargs):
        """Initialize the mock AsyncResult.
        
        Args:
            task_id: The ID of the task.
            **kwargs: Additional keyword arguments to store as attributes.
        """
        self._id = task_id
        self._result = None
        self._status = 'PENDING'
        # Initialize _ready based on status
        self._ready = kwargs.get('ready', False)
        self._kwargs = kwargs
    
    @property
    def id(self) -> str:
        """Get the task ID."""
        return self._id
    
    @id.setter
    def id(self, value: str) -> None:
        """Set the task ID."""
        self._id = value
    
    @property
    def status(self) -> str:
        """Get the task status."""
        return self._status
    
    @status.setter
    def status(self, value: str) -> None:
        """Set the task status."""
        self._status = value
    
    def ready(self) -> bool:
        """Check if the task is ready."""
        return self._ready
    
    @property
    def result(self) -> Any:
        """Get the task result.
        
        Raises:
            Exception: If the task is not ready.
        """
        if not self._ready:
            raise Exception("Task is not ready")
        return self._result
    
    @result.setter
    def result(self, value: Any) -> None:
        """Set the task result."""
        self._result = value
    
    def set_result(self, result: Any, status: str = 'SUCCESS', ready: bool = None) -> 'MockAsyncResult':
        """Set the task result and status.
        
        Args:
            result: The task result to set.
            status: The status to set (default: 'SUCCESS').
            ready: Whether the task is ready. If None, determined by status.
            
        Returns:
            The MockAsyncResult instance for method chaining.
        """
        self._result = result
        self._status = status
        
        # Default ready to True for terminal states
        if ready is None:
            self._ready = status in ['SUCCESS', 'FAILURE', 'REVOKED', 'RETRY']
        else:
            self._ready = ready
            
        return self
        
    def set_status(self, status: str) -> None:
        """Set the task status and update ready state accordingly."""
        self._status = status
        # Update ready state based on the new status
        self._ready = status in ['SUCCESS', 'FAILURE', 'REVOKED', 'RETRY']
    
    def get(self, *args, **kwargs) -> Any:
        """Get the task result (mimics AsyncResult.get)."""
        return self._result
    
    def successful(self) -> bool:
        """Check if the task completed successfully."""
        return self._status == 'SUCCESS'
        
    def failed(self) -> bool:
        """Check if the task failed."""
        return self._status == 'FAILURE'
        
    def wait(self, *args, **kwargs) -> Any:
        """Wait for the task to complete (mimics AsyncResult.wait)."""
        return self._result
        
    def forget(self) -> None:
        """Forget about the task (mimics AsyncResult.forget)."""
        pass
        
    def revoke(self, *args, **kwargs) -> bool:
        """Revoke the task (mimics AsyncResult.revoke)."""
        self._status = 'REVOKED'
        return True


class MockTask:
    """A mock implementation of a Celery task for testing."""
    
    def __init__(self):
        """Initialize the mock task with MagicMock instances for delay and apply_async."""
        self.delay = MagicMock()
        self.apply_async = MagicMock()
    
    def __call__(self, *args, **kwargs):
        """Make the instance callable like a Celery task."""
        return self.delay(*args, **kwargs)


def create_mock_async_result(task_id: str = 'test-task-id', 
                           result: Optional[Any] = None, 
                           status: str = 'PENDING',
                           ready: bool = None) -> MockAsyncResult:
    """Create a pre-configured MockAsyncResult instance.
    
    Args:
        task_id: The task ID to use (default: 'test-task-id').
        result: The result to set (default: None).
        status: The status to set (default: 'PENDING').
        ready: Whether the task is ready. If None, determined by status.
        
    Returns:
        A configured MockAsyncResult instance.
    """
    mock_result = MockAsyncResult(task_id)
    if result is not None:
        mock_result.set_result(result, status, ready=ready)
    else:
        mock_result.status = status
        # Only set ready if explicitly provided
        if ready is not None:
            mock_result._ready = ready
            
    return mock_result


def create_mock_task() -> MockTask:
    """Create a new MockTask instance.
    
    Returns:
        A new MockTask instance.
    """
    return MockTask()
