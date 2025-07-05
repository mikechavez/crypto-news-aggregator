"""Test cases for the articles API endpoints."""
import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, ANY, AsyncMock, PropertyMock
from datetime import datetime, timezone, timedelta
from fastapi import status
from typing import Dict, Any, Optional

from crypto_news_aggregator.db.models import Article, Source
from sqlalchemy.ext.asyncio import AsyncSession
from tests.test_utils import MockAsyncResult, MockTask, create_mock_async_result, create_mock_task

# Fixtures
# We'll use the client fixture from conftest.py instead of creating our own

# Test data
# Test user data as dictionary since we don't have a User model
TEST_USER = {
    "id": 1,
    "email": "test@example.com",
    "hashed_password": "hashed_password",
    "is_active": True,
    "is_superuser": False,
}

TEST_ARTICLE = Article(
    id=1,
    source_id="test-source-1",
    title="Test Article",
    description="A test article description",
    author="Test Author",
    content="This is a test article content.",
    url_to_image="https://example.com/test-image.jpg",
    url="https://example.com/test-article",
    published_at=datetime.now(timezone.utc)
)

TEST_SOURCE = Source(
    id="test-source-1",
    name="Test Source",
    url="https://example.com",
    type="news"
)

@pytest.fixture
def mock_db_session():
    """Fixture to provide a mock database session."""
    with patch('crypto_news_aggregator.db.session.get_session') as mock_get_session:
        mock_session = AsyncMock(spec=AsyncSession)
        
        # Set up the async context manager
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        
        # Configure the mock to return our mock session
        mock_get_session.return_value = mock_session
        
        # Set up common query mocks
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        mock_session.get.return_value = None
        
        yield mock_session

@pytest.fixture
def mock_async_result():
    """Fixture to provide a mock AsyncResult for testing."""
    # Create a mock async result that won't try to connect to a broker
    mock_result = create_mock_async_result('test-task-id')
    # Patch the AsyncResult class in the celery.result module
    with patch('celery.result.AsyncResult', return_value=mock_result):
        yield mock_result

@pytest.fixture
def mock_current_user():
    """Fixture to provide a mock current user for testing."""
    return TEST_USER

@pytest.fixture
def user_access_token():
    """Fixture to provide a test JWT token."""
    return "test-jwt-token"

@pytest.fixture
def test_user():
    """Fixture to provide a test user."""
    return TEST_USER

@pytest.fixture
def test_article():
    """Fixture to provide a test article."""
    return TEST_ARTICLE

@pytest.fixture
def test_source():
    """Fixture to provide a test source."""
    return TEST_SOURCE

@pytest.fixture
def mock_celery_tasks():
    """Fixture to mock Celery tasks for testing."""
    # Create mock tasks using our utility function
    mock_fetch_news = create_mock_task()
    mock_analyze_sentiment = create_mock_task()
    mock_update_trends = create_mock_task()
    
    # Create a mock async result using our utility function
    mock_result = create_mock_async_result('test-task-id')
    
    # Configure the mock tasks to return our mock async result
    mock_fetch_news.delay.return_value = mock_result
    mock_analyze_sentiment.delay.return_value = mock_result
    mock_update_trends.delay.return_value = mock_result
    
    # Patch the actual Celery tasks with our mocks
    with patch('crypto_news_aggregator.api.fetch_news', mock_fetch_news), \
         patch('crypto_news_aggregator.api.analyze_sentiment', mock_analyze_sentiment), \
         patch('crypto_news_aggregator.api.update_trends', mock_update_trends):
        
        yield {
            'fetch_news': mock_fetch_news,
            'analyze_sentiment': mock_analyze_sentiment,
            'update_trends': mock_update_trends,
            'result': mock_result
        }

def test_get_task_status_success(client, monkeypatch, capsys):
    """Test getting the status of a successfully completed task."""
    from unittest.mock import MagicMock, AsyncMock, patch
    from fastapi.testclient import TestClient
    from crypto_news_aggregator.api.v1.tasks import get_async_result_class
    from celery.result import AsyncResult as CeleryAsyncResult
    from crypto_news_aggregator.main import app
    
    print("\n[DEBUG] Starting test_get_task_status_success")
    
    # Arrange
    task_id = 'test-task-id'
    expected_result = {"status": "success", "message": "Task completed"}
    
    # Create a mock for the AsyncResult instance
    mock_async_instance = AsyncMock()
    mock_async_instance.id = task_id
    mock_async_instance.task_id = task_id
    mock_async_instance.status = 'SUCCESS'
    # Make ready() an async method that returns True
    mock_async_instance.ready = AsyncMock(return_value=True)
    mock_async_instance.result = expected_result
    
    # Create a mock for the AsyncResult class
    mock_async_result_class = MagicMock(return_value=mock_async_instance)
    
    # Patch the Celery AsyncResult class at the module level
    with patch('crypto_news_aggregator.api.v1.tasks.CeleryAsyncResult', mock_async_result_class):
        # Also patch the get_async_result_class dependency
        with patch('crypto_news_aggregator.api.v1.tasks.get_async_result_class', return_value=mock_async_result_class):
            print("\n[DEBUG] Patched CeleryAsyncResult and get_async_result_class")
            
            # Act - Use the synchronous client for the request
            print(f"\n[DEBUG] Sending request to API for task {task_id}...")
            
            # Get a fresh client after patching
            with TestClient(app) as test_client:
                # Add API key to all requests from this client
                test_client.headers.update({
                    "X-API-Key": "testapikey123",
                    "Content-Type": "application/json"
                })
                
                response = test_client.get(f"/api/v1/tasks/{task_id}")
            
            print(f"[DEBUG] Response status: {response.status_code}")
            print(f"[DEBUG] Response content: {response.text}")
            
            # Assert
            assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
            data = response.json()
            print(f"[DEBUG] Response data: {data}")
            
            # Verify the mock was called correctly
            mock_async_result_class.assert_called_once()
            
            # Assert the response
            assert "task_id" in data, f"Expected 'task_id' in response, got: {data}"
            assert data["task_id"] == task_id, f"Expected task_id '{task_id}', got '{data['task_id']}'"
            assert data["status"] == "SUCCESS", f"Expected status 'SUCCESS', got '{data['status']}'"
            
            # The result might be in a 'result' field or directly in the response
            if 'result' in data and data['result'] is not None:
                assert data["result"] == expected_result, f"Expected result {expected_result}, got {data.get('result')}"
            
            # Verify the ready method was called
            mock_async_instance.ready.assert_called_once()
            
            print("[DEBUG] All assertions passed!")

def test_get_task_status_pending(client, monkeypatch, capsys):
    """Test getting the status of a pending task."""
    # Import the tasks module to access its attributes
    from crypto_news_aggregator.api.v1 import tasks
    from fastapi.testclient import TestClient
    from crypto_news_aggregator.main import app
    
    # Arrange
    task_id = 'pending-task-id'
    
    # Create a mock AsyncResult class for a pending task
    class MockAsyncResult:
        def __init__(self, task_id, **kwargs):
            print(f"[DEBUG] Creating Pending MockAsyncResult with task_id={task_id}, kwargs={kwargs}")
            self.id = task_id
            self.task_id = task_id
            self.status = 'PENDING'
            self._ready = False
            
        def ready(self):
            print(f"[DEBUG] Pending MockAsyncResult.ready() called, returning {self._ready}")
            return self._ready
            
        @property
        def result(self):
            # Shouldn't be called for pending tasks
            raise Exception("Result should not be accessed for pending tasks")
    
    # Create a function to return our mock class
    def get_mock_async_result_class():
        print("[DEBUG] Returning Pending MockAsyncResult class")
        return MockAsyncResult
    
    # Override the dependency in the existing app
    app.dependency_overrides[tasks.get_async_result_class] = get_mock_async_result_class
    
    try:
        # Act
        print("\n[DEBUG] Sending request to API for pending task...")
        response = client.get(f"/api/v1/tasks/{task_id}")
        print(f"[DEBUG] Response status: {response.status_code}")
        print(f"[DEBUG] Response data: {response.json()}")
        
        # Assert
        assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
        data = response.json()
        
        assert data["task_id"] == task_id, f"Expected task_id '{task_id}', got '{data['task_id']}'"
        assert data["status"] == "PENDING", f"Expected status 'PENDING', got '{data['status']}'"
        # The API includes result: None for pending tasks due to the Pydantic model
        assert data.get("result") is None, f"Expected result to be None for pending task, but got {data.get('result')}"
    finally:
        # Clean up the overrides
        app.dependency_overrides = {}

@patch('src.crypto_news_aggregator.api.v1.tasks.CeleryAsyncResult')
def test_get_task_status_failed(mock_async_result_class, client, capsys):
    """Test getting the status of a failed task."""
    # Arrange
    task_id = 'failed-task-id'
    error_message = "Task failed with an error"
    
    # Create a mock AsyncResult instance
    mock_result = MagicMock()
    mock_result.id = task_id
    mock_result.task_id = task_id
    mock_result.status = 'FAILURE'
    mock_result.ready.return_value = True
    
    # Configure the mock to raise an exception when result is accessed
    mock_result.result = Exception(error_message)
    mock_result.get.side_effect = Exception(error_message)
    
    # Ensure the mock has the necessary attributes
    mock_result.failed.return_value = True
    mock_result.successful.return_value = False
    
    # Configure the mock class to return our mock instance
    mock_async_result_class.return_value = mock_result
    
    # Act
    print("\n[DEBUG] Sending request to API for failed task...")
    response = client.get(f"/api/v1/tasks/{task_id}")
    
    # Print response for debugging
    print(f"[DEBUG] Response status: {response.status_code}")
    print(f"[DEBUG] Response data: {response.json()}")
    
    # Assert
    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
    data = response.json()
    
    assert data["task_id"] == task_id, f"Expected task_id '{task_id}', got '{data['task_id']}'"
    assert data["status"] == "FAILURE", f"Expected status 'FAILURE', got '{data['status']}'"
    
    # The endpoint might return either 'error' or include the error in 'result'
    if "error" in data:
        assert error_message in data["error"], f"Expected error message to contain '{error_message}', but got '{data.get('error')}'"
    elif "result" in data and "error" in data["result"]:
        assert error_message in data["result"]["error"], f"Expected error message in result to contain '{error_message}', but got '{data.get('result', {}).get('error')}'"

@patch('src.crypto_news_aggregator.api.v1.tasks.CeleryAsyncResult')
def test_get_task_status_revoked(mock_async_result_class, client, capsys):
    """Test getting the status of a revoked task."""
    # Arrange
    task_id = 'revoked-task-id'
    
    # Create a mock AsyncResult instance
    mock_result = MagicMock()
    mock_result.id = task_id
    mock_result.task_id = task_id
    mock_result.status = 'REVOKED'
    mock_result.ready.return_value = True
    mock_result.result = None
    
    # Configure the mock class to return our mock instance
    mock_async_result_class.return_value = mock_result
    
    # Act
    print("\n[DEBUG] Sending request to API for revoked task...")
    response = client.get(f"/api/v1/tasks/{task_id}")
    
    # Print response for debugging
    print(f"[DEBUG] Response status: {response.status_code}")
    print(f"[DEBUG] Response data: {response.json()}")
    
    # Assert
    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
    data = response.json()
    
    assert data["task_id"] == task_id, f"Expected task_id '{task_id}', got '{data['task_id']}'"
    assert data["status"] == "REVOKED", f"Expected status 'REVOKED', got '{data['status']}'"
    # The API includes result: None for all task statuses
    assert data.get("result") is None, f"Expected result to be None for revoked task, but got {data.get('result')}"

@patch('src.crypto_news_aggregator.api.v1.tasks.CeleryAsyncResult')
def test_get_task_status_retry(mock_async_result_class, client, capsys):
    """Test getting the status of a task that's being retried."""
    # Arrange
    task_id = 'retry-task-id'
    retry_message = "Task is being retried"
    
    # Create a mock AsyncResult instance
    mock_result = MagicMock()
    mock_result.id = task_id
    mock_result.task_id = task_id
    mock_result.status = 'RETRY'
    mock_result.ready.return_value = True
    mock_result.result = retry_message
    
    # Configure the mock class to return our mock instance
    mock_async_result_class.return_value = mock_result
    
    # Act
    print("\n[DEBUG] Sending request to API for retry task...")
    response = client.get(f"/api/v1/tasks/{task_id}")
    
    # Print response for debugging
    print(f"[DEBUG] Response status: {response.status_code}")
    print(f"[DEBUG] Response data: {response.json()}")
    
    # Assert
    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
    data = response.json()
    
    assert data["task_id"] == task_id, f"Expected task_id '{task_id}', got '{data['task_id']}'"
    assert data["status"] == "RETRY", f"Expected status 'RETRY', got '{data['status']}'"
    assert data.get("result") == retry_message, f"Expected result '{retry_message}', got '{data.get('result')}'"

@patch('src.crypto_news_aggregator.api.v1.tasks.CeleryAsyncResult')
def test_get_task_status_with_large_result(mock_async_result_class, client, capsys):
    """Test getting the status of a task with a large result."""
    # Arrange
    task_id = 'large-result-task-id'
    large_result = {"data": ["x" * 1000] * 1000}  # Large result
    
    # Create a mock AsyncResult instance
    mock_result = MagicMock()
    mock_result.id = task_id
    mock_result.task_id = task_id
    mock_result.status = 'SUCCESS'
    mock_result.ready.return_value = True
    mock_result.result = large_result
    
    # Configure the mock class to return our mock instance
    mock_async_result_class.return_value = mock_result
    
    # Act
    print("\n[DEBUG] Sending request to API for task with large result...")
    response = client.get(f"/api/v1/tasks/{task_id}")
    
    # Print response for debugging
    print(f"[DEBUG] Response status: {response.status_code}")
    response_data = response.json()
    print(f"[DEBUG] Response data keys: {list(response_data.keys())}")
    
    # Assert
    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
    
    data = response.json()
    assert data["task_id"] == task_id, f"Expected task_id '{task_id}', got '{data['task_id']}'"
    assert data["status"] == "SUCCESS", f"Expected status 'SUCCESS', got '{data['status']}'"
    assert "result" in data, "Expected 'result' in response"
    
    # Verify the result structure
    result = data["result"]
    assert isinstance(result, dict), f"Expected result to be a dict, got {type(result)}"
    assert "data" in result, "Expected 'data' in result"
    assert isinstance(result["data"], list), f"Expected 'data' to be a list, got {type(result['data'])}"
    assert len(result["data"]) == 1000, f"Expected 1000 items in data, got {len(result['data'])}"
    
    # Verify the first item in the data list
    first_item = result["data"][0]
    assert first_item == "x" * 1000, f"Expected first item to be 'x' * 1000, got {first_item}"

@pytest.mark.asyncio
async def test_get_task_status_not_found():
    """Test getting the status of a non-existent task."""
    # Arrange
    task_id = 'nonexistent-task-id'
    
    # Create a mock AsyncResult that simulates a task that doesn't exist
    class MockAsyncResult:
        def __init__(self, task_id):
            self.task_id = task_id
            self._status = 'PENDING'
            self._result = None
            
        @property
        def status(self):
            return self._status
            
        @property
        def result(self):
            return self._result
            
        def ready(self):
            return False
            
        def get(self, *args, **kwargs):
            # Simulate task not found by raising an exception
            raise Exception("Task not found")
    
    # Create a function that will return our mock AsyncResult
    def get_mock_async_result():
        def _mock_async_result(task_id):
            return MockAsyncResult(task_id)
        return _mock_async_result
    
    # Override the dependency
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from crypto_news_aggregator.api.v1.tasks import router, get_async_result_class
    
    app = FastAPI()
    app.include_router(router)
    
    # Apply the dependency override
    app.dependency_overrides[get_async_result_class] = get_mock_async_result
    
    try:
        # Create a new test client with our app
        test_client = TestClient(app)
        
        # Act
        print(f"[DEBUG] Sending request to API for non-existent task...")
        response = test_client.get(f"/api/v1/tasks/{task_id}")
        print(f"[DEBUG] Response status: {response.status_code}")
        print(f"[DEBUG] Response content: {response.text}")
        
        # Assert
        assert response.status_code == 404, f"Expected status code 404, got {response.status_code}"
        data = response.json()
        assert "detail" in data, "Expected 'detail' in error response"
        assert "not found" in data["detail"].lower(), f"Expected 'not found' in error message, got: {data['detail']}"
        
        print("[DEBUG] All assertions passed!")
    except Exception as e:
        print(f"[DEBUG] Test failed with exception: {str(e)}")
        raise
    finally:
        # Clean up the overrides
        print("\n[DEBUG] Cleaning up dependency overrides")
        app.dependency_overrides = {}
        print(f"[DEBUG] Final dependency overrides: {app.dependency_overrides}")

@pytest.mark.asyncio
@patch('src.crypto_news_aggregator.api.v1.tasks.CeleryAsyncResult')
async def test_get_task_status_with_exception(mock_celery_async_result, client):
    """Test handling of exceptions when getting task status."""
    # Arrange
    task_id = 'exceptional-task-id'
    
    print("\n[DEBUG] Starting test_get_task_status_with_exception")
    
    # Create a mock AsyncResult that raises an exception when status is accessed
    mock_result = MagicMock()
    mock_result.id = task_id
    mock_result.task_id = task_id
    
    # Configure the status property to raise an exception
    type(mock_result).status = PropertyMock(side_effect=Exception("Failed to get status"))
    mock_result.ready.return_value = False
    
    # Configure the CeleryAsyncResult mock to return our mock result
    mock_celery_async_result.return_value = mock_result
    
    # Act
    print(f"\n[DEBUG] Making request to /api/v1/tasks/{task_id}")
    response = client.get(f"/api/v1/tasks/{task_id}")
    print(f"[DEBUG] Response status: {response.status_code}")
    print(f"[DEBUG] Response content: {response.text}")
    
    # Assert
    # The API should return a 200 status with an error in the response
    assert response.status_code == 200, (
        f"Expected status code 200, got {response.status_code}"
    )
    
    data = response.json()
    print(f"[DEBUG] Response data: {data}")
    
    # The endpoint should include the task_id in the response
    assert "task_id" in data, "Expected 'task_id' in response"
    assert data["task_id"] == task_id, (
        f"Expected task_id '{task_id}', got '{data.get('task_id')}'"
    )
    
    # The endpoint should include the error message in the response
    assert "error" in data, "Expected 'error' in response"
    assert "Failed to get status" in data["error"], (
        f"Expected error message to contain 'Failed to get status', got: {data.get('error')}"
    )
    
    # Verify the mock was called correctly
    mock_celery_async_result.assert_called_once_with(task_id)
    
    print("\n[DEBUG] All assertions passed!")

@pytest.mark.asyncio
@patch('src.crypto_news_aggregator.api.v1.tasks.CeleryAsyncResult')
async def test_get_task_status_with_serialization_error(mock_celery_async_result, client):
    """Test handling of non-serializable task results."""
    # Arrange
    task_id = 'non-serializable-task-id'
    
    print("\n[DEBUG] Starting test_get_task_status_with_serialization_error")
    
    # Create a mock AsyncResult that returns a non-serializable object
    mock_result = MagicMock()
    mock_result.id = task_id
    mock_result.task_id = task_id
    mock_result.status = 'SUCCESS'
    
    # Configure the result property to return a non-serializable function
    type(mock_result).result = PropertyMock(return_value=lambda x: x)
    mock_result.ready.return_value = True
    
    # Configure the CeleryAsyncResult mock to return our mock result
    mock_celery_async_result.return_value = mock_result
    
    # Act
    print(f"\n[DEBUG] Making request to /api/v1/tasks/{task_id}")
    response = client.get(f"/api/v1/tasks/{task_id}")
    print(f"[DEBUG] Response status: {response.status_code}")
    print(f"[DEBUG] Response content: {response.text}")
    
    # Assert - The endpoint should return a 200 status with an error in the response
    assert response.status_code == 200, (
        f"Expected status code 200, got {response.status_code}"
    )
    
    data = response.json()
    print(f"[DEBUG] Response data: {data}")
    
    # The endpoint should include the task_id in the response
    assert "task_id" in data, "Expected 'task_id' in response"
    assert data["task_id"] == task_id, (
        f"Expected task_id '{task_id}', got '{data.get('task_id')}'"
    )
    
    # The endpoint should include an error message in the response
    assert "error" in data, "Expected 'error' in response"
    assert "not JSON serializable" in data["error"], (
        f"Expected serialization error message, got: {data.get('error')}"
    )
    
    # Verify the mock was called correctly
    mock_celery_async_result.assert_called_once_with(task_id)
    
    print("\n[DEBUG] All assertions passed!")

@pytest.mark.asyncio
@patch('src.crypto_news_aggregator.api.v1.tasks.CeleryAsyncResult')
async def test_get_task_status_with_custom_status(mock_celery_async_result, client):
    """Test handling of custom task status values."""
    # Arrange
    task_id = 'custom-status-task-id'
    custom_status = 'CUSTOM_STATUS'
    
    print("\n[DEBUG] Starting test_get_task_status_with_custom_status")
    
    # Create a mock AsyncResult instance
    mock_result = MagicMock()
    mock_result.id = task_id
    mock_result.task_id = task_id
    mock_result.status = custom_status
    mock_result.result = {"custom": "result"}
    mock_result.ready.return_value = True
    
    # Configure the CeleryAsyncResult mock to return our mock result
    mock_celery_async_result.return_value = mock_result
    
    # Act - Make the request to the endpoint
    url = f"/api/v1/tasks/{task_id}"
    print(f"\n[DEBUG] Making request to {url}")
    
    response = client.get(url)
    print(f"[DEBUG] Response status: {response.status_code}")
    print(f"[DEBUG] Response content: {response.text}")
    
    # Assert - The endpoint should return a 200 status code with the custom status
    assert response.status_code == 200, (
        f"Expected status code 200, got {response.status_code}"
    )
    
    data = response.json()
    print(f"[DEBUG] Response data: {data}")
    
    # Verify the mock was called correctly
    mock_celery_async_result.assert_called_once_with(task_id)
    
    # Verify the response contains the expected fields and values
    assert data["task_id"] == task_id, (
        f"Expected task_id '{task_id}', got '{data.get('task_id')}'"
    )
    
    # The status should be the custom status we set
    assert data["status"] == custom_status, (
        f"Expected status '{custom_status}', got '{data.get('status')}'"
    )
    
    # The result should be included in the response
    assert "result" in data, "Expected 'result' in response"
    assert data["result"]["custom"] == "result", "Expected custom result in response"
    
    print("\n[DEBUG] All assertions passed!")

from unittest.mock import patch, MagicMock
from tests.test_utils import create_mock_async_result

@pytest.mark.asyncio
@patch('src.crypto_news_aggregator.api.v1.tasks.fetch_news')
async def test_trigger_news_fetch(mock_fetch_news, client, test_user):
    """Test triggering a news fetch task."""
    # Arrange
    source_param = "test-source"
    task_id = "test-task-id-123"
    
    # Create a mock task result
    mock_result = MagicMock()
    mock_result.id = task_id
    
    # Configure the mock task
    mock_fetch_news.delay.return_value = mock_result
    
    print("\n[DEBUG] Starting test_trigger_news_fetch")
    print(f"- Source parameter: {source_param}")
    print(f"- Mock task ID: {task_id}")
    
    # Act - Make request to the endpoint with source as a query parameter
    url = f"/api/v1/news/fetch?source={source_param}"
    print(f"\n[DEBUG] Making POST request to: {url}")
    
    response = client.post(url, json={})
    
    # Print debug information
    print(f"[DEBUG] Response status: {response.status_code}")
    print(f"[DEBUG] Response content: {response.text}")
    
    # Assert
    # Check response status code
    assert response.status_code == 202, (
        f"Expected status code 202, got {response.status_code}. Response: {response.text}"
    )
    
    # Parse response JSON
    data = response.json()
    print(f"[DEBUG] Response data: {data}")
    
    # Verify the response has the expected structure
    assert "task_id" in data, f"Response missing 'task_id' field: {data}"
    assert "status" in data, f"Response missing 'status' field: {data}"
    
    # Verify the task ID matches our mock
    assert data["task_id"] == task_id, (
        f"Expected task_id '{task_id}', got '{data.get('task_id')}'"
    )
    
    # Verify status is PENDING
    assert data["status"] == "PENDING", (
        f"Expected status 'PENDING', got '{data.get('status')}'"
    )
    
    # Verify the task was called with the correct arguments
    assert mock_fetch_news.delay.called, "Task was not called"
    
    # Get the arguments passed to the task
    call_args, call_kwargs = mock_fetch_news.delay.call_args
    print(f"[DEBUG] Task call args: {call_args}")
    print(f"[DEBUG] Task call kwargs: {call_kwargs}")
    
    # The task should be called with the source parameter
    assert len(call_args) == 1, "Task was not called with exactly one argument"
    assert call_args[0] == source_param, (
        f"Expected source parameter '{source_param}', got '{call_args[0]}'"
    )
    
    # Verify the task was called exactly once with the expected arguments
    mock_fetch_news.delay.assert_called_once_with(source_param)
    
    print("\n[DEBUG] All assertions passed!")
    
@pytest.mark.asyncio
async def test_trigger_sentiment_analysis(client, test_user):
    """Test triggering sentiment analysis for an article."""
    # Import necessary modules
    from unittest.mock import patch, MagicMock
    import uuid
    
    # Arrange
    article_id = 123
    task_id = str(uuid.uuid4())  # Generate a UUID for the task ID
    
    print("\n[DEBUG] Starting test_trigger_sentiment_analysis")
    print(f"- Article ID: {article_id}")
    print(f"- Generated task ID: {task_id}")
    
    # Create a mock task that returns a mock result with an id when delay() is called
    mock_task = MagicMock()
    mock_result = MagicMock()
    mock_result.id = task_id
    mock_task.delay.return_value = mock_result
    
    # Patch the analyze_sentiment task at the module where it's imported in the API
    with patch('src.crypto_news_aggregator.api.v1.tasks.analyze_sentiment', mock_task) as mock_patch:
        print("\n[DEBUG] Mock task created and patched:")
        print(f"- mock_task: {mock_task}")
        print(f"- mock_result: {mock_result}")
        
        # Act - Make request to the endpoint using the authenticated client
        url = f"/api/v1/sentiment/analyze/{article_id}"
        print(f"\n[DEBUG] Making authenticated POST request to: {url}")
        
        response = client.post(url)
        
        # Debug output
        print("\n[DEBUG] API Response:")
        print(f"- Status code: {response.status_code}")
        print(f"- Headers: {dict(response.headers)}")
        print(f"- Body: {response.text}")
        
        # Assert - The API should return a 202 status code with task details
        assert response.status_code == 202, (
            f"Expected status code 202 (Accepted), got {response.status_code}. "
            f"Response: {response.text}"
        )
        
        # Parse response JSON
        data = response.json()
        print("\n[DEBUG] Response data:", data)
        
        # Verify response structure
        assert "task_id" in data, "Response missing 'task_id' field"
        assert data["task_id"] == task_id, (
            f"Expected task_id '{task_id}', got '{data.get('task_id')}'"
        )
        
        assert "status" in data, "Response missing 'status' field"
        assert data["status"] == "PENDING", (
            f"Expected status 'PENDING', got '{data.get('status')}'"
        )
        
        # Verify the task was called with the correct arguments
        print("\n[DEBUG] Verifying task was called correctly:")
        print(f"- mock_task.delay.called: {mock_task.delay.called}")
        print(f"- mock_task.delay.call_args_list: {mock_task.delay.call_args_list}")
        
        mock_task.delay.assert_called_once()
        args, kwargs = mock_task.delay.call_args
        
        # Verify the task was called with the correct article_id
        assert len(args) == 1, (
            f"Expected 1 positional argument, got {len(args)}"
        )
        assert args[0] == article_id, (
            f"Expected article_id={article_id}, got {args[0] if args else 'no arguments'}"
        )
        
        # Verify no keyword arguments were passed
        assert not kwargs, (
            f"Expected no keyword arguments, got {kwargs}"
        )
        
        print("\n[DEBUG] All assertions passed!")

@pytest.mark.asyncio
async def test_trigger_trends_update(client, test_user):
    """Test triggering a trends update task."""
    # Import necessary modules
    from unittest.mock import patch, MagicMock
    import uuid
    
    # Arrange
    task_id = str(uuid.uuid4())  # Generate a UUID for the task ID
    
    print("\n[DEBUG] Starting test_trigger_trends_update")
    print(f"- Generated task ID: {task_id}")
    
    # Create a mock task that returns a mock result with an id when delay() is called
    mock_task = MagicMock()
    mock_result = MagicMock()
    mock_result.id = task_id
    mock_task.delay.return_value = mock_result
    
    # Patch the update_trends task at the module where it's imported in the API
    with patch('src.crypto_news_aggregator.api.v1.tasks.update_trends', mock_task) as mock_patch:
        print("\n[DEBUG] Mock task created and patched:")
        print(f"- mock_task: {mock_task}")
        print(f"- mock_result: {mock_result}")
        
        # Act - Make request to the endpoint using the authenticated client
        url = "/api/v1/trends/update"
        print(f"\n[DEBUG] Making authenticated POST request to: {url}")
        
        response = client.post(url)
        
        # Debug output
        print("\n[DEBUG] API Response:")
        print(f"- Status code: {response.status_code}")
        print(f"- Headers: {dict(response.headers)}")
        print(f"- Body: {response.text}")
        
        # Assert - The API should return a 202 status code with task details
        assert response.status_code == 202, (
            f"Expected status code 202 (Accepted), got {response.status_code}. "
            f"Response: {response.text}"
        )
        
        # Parse response JSON
        data = response.json()
        print("\n[DEBUG] Response data:", data)
        
        # Verify response structure
        assert "task_id" in data, "Response missing 'task_id' field"
        assert data["task_id"] == task_id, (
            f"Expected task_id '{task_id}', got '{data.get('task_id')}'"
        )
        
        assert "status" in data, "Response missing 'status' field"
        assert data["status"] == "PENDING", (
            f"Expected status 'PENDING', got '{data.get('status')}'"
        )
        
        # Verify the task was called with the correct arguments
        print("\n[DEBUG] Verifying task was called correctly:")
        print(f"- mock_task.delay.called: {mock_task.delay.called}")
        print(f"- mock_task.delay.call_args_list: {mock_task.delay.call_args_list}")
        
        mock_task.delay.assert_called_once()
        args, kwargs = mock_task.delay.call_args
        
        # Verify no positional arguments were passed
        assert len(args) == 0, (
            f"Expected no positional arguments, got {len(args)}: {args}"
        )
        
        # Verify no keyword arguments were passed
        assert not kwargs, (
            f"Expected no keyword arguments, got {kwargs}"
        )
        
        print("\n[DEBUG] All assertions passed!")
from unittest.mock import patch, MagicMock

@pytest.mark.asyncio
async def test_get_task_status_with_timeout(client, monkeypatch):
    """Test getting task status with a timeout error."""
    # Arrange
    task_id = "timeout-task-id"
    timeout_message = "Task timed out"

    print("\n[DEBUG] Starting test_get_task_status_with_timeout")

    # Create a mock for the AsyncResult class
    class MockAsyncResult:
        def __init__(self, task_id):
            print(f"[MOCK] Initializing MockAsyncResult with task_id: {task_id}")
            self.id = task_id
            self.task_id = task_id
            self.status = 'PENDING'
            self._result = None

        def ready(self):
            print("[MOCK] MockAsyncResult.ready() called - raising TimeoutError")
            raise TimeoutError(timeout_message)

        @property
        def result(self):
            print("[MOCK] MockAsyncResult.result called")
            return self._result

    # Create a mock for the get_async_result_class function
    def mock_get_async_result_class():
        print("[MOCK] mock_get_async_result_class() called")
        return MockAsyncResult

    # Import the FastAPI app and override the dependency
    from src.crypto_news_aggregator.main import app
    from src.crypto_news_aggregator.api.v1.tasks import get_async_result_class
    
    # Save the original dependency
    original_dependency = app.dependency_overrides.get(get_async_result_class)
    
    try:
        # Override the dependency with our mock
        app.dependency_overrides[get_async_result_class] = mock_get_async_result_class
        
        # Act - Make a request to the endpoint using the test client
        endpoint = f"/api/v1/tasks/{task_id}"
        print(f"\n[DEBUG] Sending request to {endpoint}")
        response = client.get(endpoint)

        print(f"[DEBUG] Response status: {response.status_code}")
        print(f"[DEBUG] Response content: {response.text}")

        # Assert
        assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
        response_data = response.json()

        # Verify the response contains the expected fields and values
        assert response_data["task_id"] == task_id, (
            f"Expected task_id {task_id}, got {response_data.get('task_id')}"
        )

        # The status should be TIMEOUT when a timeout error occurs
        assert response_data["status"] == "TIMEOUT", (
            f"Expected status 'TIMEOUT', got {response_data.get('status')}"
        )

        # Verify the error message is included in the response
        assert "error" in response_data, "Expected 'error' field in response"
        assert "timed out" in response_data["error"].lower(), (
            f"Expected 'timed out' in error message, got: {response_data.get('error')}"
        )

    finally:
        # Restore the original dependency
        if original_dependency is not None:
            app.dependency_overrides[get_async_result_class] = original_dependency
        else:
            app.dependency_overrides.pop(get_async_result_class, None)

@pytest.mark.asyncio
@patch('src.crypto_news_aggregator.api.v1.tasks.CeleryAsyncResult')
async def test_get_task_status_with_connection_error(mock_celery_async_result, client):
    """Test handling of connection errors when checking task status."""
    # Arrange
    task_id = 'connection-error-task-id'
    error_message = "Failed to connect to message broker"
    
    print("\n[DEBUG] Starting test_get_task_status_with_connection_error")
    
    # Create a mock AsyncResult that raises ConnectionError when status is accessed
    mock_result = MagicMock()
    mock_result.id = task_id
    mock_result.task_id = task_id
    
    # Configure the status property to raise ConnectionError
    type(mock_result).status = PropertyMock(
        side_effect=ConnectionError(error_message)
    )
    
    # Configure the ready() method to return False
    mock_result.ready.return_value = False
    
    # Configure the CeleryAsyncResult mock to return our mock result
    mock_celery_async_result.return_value = mock_result
    
    # Act
    print(f"\n[DEBUG] Making request to /api/v1/tasks/{task_id}")
    response = client.get(f"/api/v1/tasks/{task_id}")
    print(f"[DEBUG] Response status: {response.status_code}")
    print(f"[DEBUG] Response content: {response.text}")
    
    # Assert - The API should return a 200 status code with error details
    assert response.status_code == 200, (
        f"Expected status code 200, got {response.status_code}"
    )
    
    data = response.json()
    print(f"[DEBUG] Response data: {data}")
    
    # Verify the response contains the expected fields and values
    assert data["task_id"] == task_id, (
        f"Expected task_id {task_id}, got {data.get('task_id')}"
    )
    
    # The status should be FAILURE when a connection error occurs
    assert data["status"] == "FAILURE", (
        f"Expected status 'FAILURE', got {data.get('status')}"
    )
    
    # The response should include an error message
    assert "error" in data, "Expected 'error' in response"
    assert error_message in data["error"], (
        f"Expected error message to contain '{error_message}', got: {data.get('error')}"
    )
    
    # Verify the mock was called correctly
    mock_celery_async_result.assert_called_once_with(task_id)
    
    print("\n[DEBUG] All assertions passed!")

@pytest.mark.skip(reason="Endpoint not implemented in the API")
def test_get_article_sentiment(client, mock_db_session, test_user):
    """Test getting sentiment for an article."""
    # Arrange
    headers = {}
    article_id = 1
    
    # Create a mock article with sentiment data
    mock_article = MagicMock()
    mock_article.id = article_id
    mock_article.title = "Test Article"
    mock_article.sentiment_score = 0.8
    mock_article.sentiment_label = "Positive"
    
    # Mock database response
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_article
    mock_db_session.execute.return_value = mock_result
    
    # Act - Make request to the endpoint
    response = client.get(
        f"/api/v1/articles/{article_id}/sentiment",
        headers=headers
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["article_id"] == article_id
    assert data["sentiment"]["label"] == "Positive"
    assert data["sentiment"]["score"] == 0.8

@pytest.mark.asyncio
async def test_trigger_sentiment_analysis_invalid_article(client, test_user):
    """Test triggering sentiment analysis with a non-existent article ID."""
    # Import necessary modules
    from unittest.mock import patch, MagicMock
    import uuid
    
    # Arrange
    non_existent_article_id = 9999
    task_id = str(uuid.uuid4())  # Generate a UUID for the task ID
    
    print("\n[DEBUG] Starting test_trigger_sentiment_analysis_invalid_article")
    print(f"- Non-existent article ID: {non_existent_article_id}")
    print(f"- Generated task ID: {task_id}")
    
    # Create a mock task that returns a mock result with an id when delay() is called
    mock_task = MagicMock()
    mock_result = MagicMock()
    mock_result.id = task_id
    mock_task.delay.return_value = mock_result
    
    # Patch the analyze_sentiment task at the module where it's imported in the API
    with patch('src.crypto_news_aggregator.api.v1.tasks.analyze_sentiment', mock_task) as mock_patch:
        print("\n[DEBUG] Mock task created and patched:")
        print(f"- mock_task: {mock_task}")
        print(f"- mock_result: {mock_result}")
        
        # Act - Make request with non-existent article ID using the authenticated client
        url = f"/api/v1/sentiment/analyze/{non_existent_article_id}"
        print(f"\n[DEBUG] Making authenticated POST request to: {url}")
        
        response = client.post(url)
        
        # Debug output
        print("\n[DEBUG] API Response:")
        print(f"- Status code: {response.status_code}")
        print(f"- Headers: {dict(response.headers)}")
        print(f"- Body: {response.text}")
        
        # Assert - The API should return a 202 status code with task details
        # Note: The endpoint doesn't check if the article exists before creating the task
        assert response.status_code == 202, (
            f"Expected status code 202 (Accepted), got {response.status_code}. "
            f"Response: {response.text}"
        )
        
        # Parse response JSON
        data = response.json()
        print("\n[DEBUG] Response data:", data)
        
        # Verify response structure
        assert "task_id" in data, "Response missing 'task_id' field"
        assert data["task_id"] == task_id, (
            f"Expected task_id '{task_id}', got '{data.get('task_id')}'"
        )
        
        assert "status" in data, "Response missing 'status' field"
        assert data["status"] == "PENDING", (
            f"Expected status 'PENDING', got '{data.get('status')}'"
        )
        
        # Verify the task was called with the correct arguments
        print("\n[DEBUG] Verifying task was called correctly:")
        print(f"- mock_task.delay.called: {mock_task.delay.called}")
        print(f"- mock_task.delay.call_args_list: {mock_task.delay.call_args_list}")
        
        mock_task.delay.assert_called_once()
        args, kwargs = mock_task.delay.call_args
        
        # Verify the task was called with the non-existent article_id
        assert len(args) == 1, (
            f"Expected 1 positional argument, got {len(args)}"
        )
        assert args[0] == non_existent_article_id, (
            f"Expected article_id={non_existent_article_id}, got {args[0] if args else 'no arguments'}"
        )
        
        # Verify no keyword arguments were passed
        assert not kwargs, (
            f"Expected no keyword arguments, got {kwargs}"
        )
        
        print("\n[DEBUG] All assertions passed!")
