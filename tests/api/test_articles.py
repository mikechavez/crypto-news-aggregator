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
    published_at=datetime.utcnow()
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
    with patch('crypto_news_aggregator.api.v1.tasks.AsyncResult', return_value=mock_result):
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

def test_get_task_status_success(client, monkeypatch, capsys, mock_celery_app):
    """Test getting the status of a successfully completed task."""
    # Import the tasks module to access its attributes
    from crypto_news_aggregator.api.v1 import tasks
    from fastapi.testclient import TestClient
    from crypto_news_aggregator.main import app
    
    # Arrange
    task_id = 'test-task-id'
    expected_result = {"status": "success", "message": "Task completed"}
    
    # Create a mock AsyncResult class
    class MockAsyncResult:
        def __init__(self, task_id, **kwargs):
            print(f"[DEBUG] Creating MockAsyncResult with task_id={task_id}, kwargs={kwargs}")
            self.id = task_id
            self.task_id = task_id
            self.status = 'SUCCESS'
            self._result = expected_result
            self._ready = True
            
        def ready(self):
            print(f"[DEBUG] MockAsyncResult.ready() called, returning {self._ready}")
            return self._ready
            
        @property
        def result(self):
            print(f"[DEBUG] MockAsyncResult.result called, returning {self._result}")
            return self._result
    
    # Create a function to return our mock class
    def get_mock_async_result_class():
        print("[DEBUG] Returning MockAsyncResult class")
        return MockAsyncResult
    
    # Override the dependency in the existing app
    app.dependency_overrides[tasks.get_async_result_class] = get_mock_async_result_class
    
    # Create a test client with the existing app
    test_client = TestClient(app)
    
    try:
        # Act
        print("\n[DEBUG] Sending request to API...")
        response = test_client.get(f"/api/v1/tasks/{task_id}")
        print(f"[DEBUG] Response status: {response.status_code}")
        print(f"[DEBUG] Response data: {response.json()}")
        
        # Assert
        assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
        data = response.json()
        
        assert data["task_id"] == task_id, f"Expected task_id '{task_id}', got '{data['task_id']}'"
        assert data["status"] == "SUCCESS", f"Expected status 'SUCCESS', got '{data['status']}'"
        assert data.get("result") == expected_result, f"Expected result {expected_result}, got {data.get('result')}"
    finally:
        # Clean up the overrides
        app.dependency_overrides = {}

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

def test_get_task_status_failed(client, monkeypatch, capsys):
    """Test getting the status of a failed task."""
    # Import the tasks module to access its attributes
    from crypto_news_aggregator.api.v1 import tasks
    from fastapi.testclient import TestClient
    from crypto_news_aggregator.main import app
    
    print("\n[DEBUG] Starting test_get_task_status_failed")
    
    # Arrange
    task_id = 'failed-task-id'
    error_message = "Task failed with an error"
    
    # Create a mock AsyncResult class for a failed task
    class MockAsyncResult:
        def __init__(self, task_id, **kwargs):
            print(f"[DEBUG] Creating Failed MockAsyncResult with task_id={task_id}, kwargs={kwargs}")
            self.id = task_id
            self.task_id = task_id
            self.status = 'FAILURE'
            self._result = Exception(error_message)
            self._ready = True
            self._failed = True
            
        def ready(self):
            print(f"[DEBUG] Failed MockAsyncResult.ready() called, returning {self._ready}")
            return self._ready
            
        @property
        def result(self):
            print(f"[DEBUG] Failed MockAsyncResult.result called, raising exception")
            raise self._result
    
    # Create a function to return our mock class
    def get_mock_async_result_class():
        print("[DEBUG] In get_mock_async_result_class, returning MockAsyncResult")
        return MockAsyncResult
    
    # Create a new test client with our overrides
    with TestClient(app) as test_client:
        # Override the dependency in the existing app
        print("[DEBUG] Setting up dependency override...")
        app.dependency_overrides[tasks.get_async_result_class] = get_mock_async_result_class
        print(f"[DEBUG] Updated dependency overrides: {app.dependency_overrides}")
        
        try:
            # Act
            print("\n[DEBUG] Sending request to API for failed task...")
            print(f"[DEBUG] Request URL: /api/v1/tasks/{task_id}")
            
            # Call the endpoint
            response = test_client.get(f"/api/v1/tasks/{task_id}")
            print(f"[DEBUG] Response status: {response.status_code}")
            
            # Print response headers and body for debugging
            print(f"[DEBUG] Response headers: {dict(response.headers)}")
            response_data = response.json()
            print(f"[DEBUG] Response data: {response_data}")
            
            # Assert
            assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
            data = response_data
            
            print(f"[DEBUG] Verifying response data...")
            assert data["task_id"] == task_id, f"Expected task_id '{task_id}', got '{data['task_id']}'"
            assert data["status"] == "FAILURE", f"Expected status 'FAILURE', got '{data['status']}'"
            assert "error" in data, f"Expected error in response, but got {data}"
            assert error_message in data["error"], f"Expected error message to contain '{error_message}', but got '{data.get('error')}'"
            
            print("[DEBUG] All assertions passed!")
        except Exception as e:
            print(f"[DEBUG] Test failed with exception: {str(e)}")
            print("[DEBUG] Current app.dependency_overrides:", app.dependency_overrides)
            raise
        finally:
            # Clean up the overrides
            print("\n[DEBUG] Cleaning up dependency overrides")
            app.dependency_overrides = {}
            print(f"[DEBUG] Final dependency overrides: {app.dependency_overrides}")

def test_get_task_status_revoked(client, monkeypatch):
    """Test getting the status of a revoked task."""
    # Import the tasks module to access its attributes
    from crypto_news_aggregator.api.v1 import tasks
    from fastapi.testclient import TestClient
    from crypto_news_aggregator.main import app
    
    print("\n[DEBUG] Starting test_get_task_status_revoked")
    
    # Arrange
    task_id = 'revoked-task-id'
    
    # Create a mock AsyncResult class for a revoked task
    class MockAsyncResult:
        def __init__(self, task_id, **kwargs):
            print(f"[DEBUG] Creating Revoked MockAsyncResult with task_id={task_id}, kwargs={kwargs}")
            self.id = task_id
            self.task_id = task_id
            self.status = 'REVOKED'
            self._result = None
            self._ready = True
            
        def ready(self):
            print(f"[DEBUG] Revoked MockAsyncResult.ready() called, returning {self._ready}")
            return self._ready
            
        @property
        def result(self):
            print(f"[DEBUG] Revoked MockAsyncResult.result called, returning None")
            return None
    
    # Create a function to return our mock class
    def get_mock_async_result_class():
        print("[DEBUG] In get_mock_async_result_class, returning MockAsyncResult")
        return MockAsyncResult
    
    # Create a new test client with our overrides
    with TestClient(app) as test_client:
        # Override the dependency in the existing app
        print("[DEBUG] Setting up dependency override...")
        app.dependency_overrides[tasks.get_async_result_class] = get_mock_async_result_class
        print(f"[DEBUG] Updated dependency overrides: {app.dependency_overrides}")
        
        try:
            # Act
            print("\n[DEBUG] Sending request to API for revoked task...")
            print(f"[DEBUG] Request URL: /api/v1/tasks/{task_id}")
            
            # Call the endpoint
            response = test_client.get(f"/api/v1/tasks/{task_id}")
            print(f"[DEBUG] Response status: {response.status_code}")
            
            # Print response headers and body for debugging
            print(f"[DEBUG] Response headers: {dict(response.headers)}")
            response_data = response.json()
            print(f"[DEBUG] Response data: {response_data}")
            
            # Assert
            assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
            data = response_data
            
            print(f"[DEBUG] Verifying response data...")
            assert data["task_id"] == task_id, f"Expected task_id '{task_id}', got '{data['task_id']}'"
            assert data["status"] == "REVOKED", f"Expected status 'REVOKED', got '{data['status']}'"
            # The API includes result: None for all task statuses
            assert data.get("result") is None, f"Expected result to be None for revoked task, but got {data.get('result')}"
            
            print("[DEBUG] All assertions passed!")
        except Exception as e:
            print(f"[DEBUG] Test failed with exception: {str(e)}")
            print("[DEBUG] Current app.dependency_overrides:", app.dependency_overrides)
            raise
        finally:
            # Clean up the overrides
            print("\n[DEBUG] Cleaning up dependency overrides")
            app.dependency_overrides = {}
            print(f"[DEBUG] Final dependency overrides: {app.dependency_overrides}")

def test_get_task_status_retry(client, monkeypatch):
    """Test getting the status of a task that's being retried."""
    # Import the tasks module to access its attributes
    from crypto_news_aggregator.api.v1 import tasks
    from fastapi.testclient import TestClient
    from crypto_news_aggregator.main import app
    
    print("\n[DEBUG] Starting test_get_task_status_retry")
    
    # Arrange
    task_id = 'retry-task-id'
    retry_message = "Task is being retried"
    
    # Create a mock AsyncResult class for a retry task
    class MockAsyncResult:
        def __init__(self, task_id, **kwargs):
            print(f"[DEBUG] Creating Retry MockAsyncResult with task_id={task_id}, kwargs={kwargs}")
            self.id = task_id
            self.task_id = task_id
            self.status = 'RETRY'
            self._result = retry_message
            self._ready = True
            
        def ready(self):
            print(f"[DEBUG] Retry MockAsyncResult.ready() called, returning {self._ready}")
            return self._ready
            
        @property
        def result(self):
            print(f"[DEBUG] Retry MockAsyncResult.result called, returning: {self._result}")
            return self._result
    
    # Create a function to return our mock class
    def get_mock_async_result_class():
        print("[DEBUG] In get_mock_async_result_class, returning MockAsyncResult")
        return MockAsyncResult
    
    # Create a new test client with our overrides
    with TestClient(app) as test_client:
        # Override the dependency in the existing app
        print("[DEBUG] Setting up dependency override...")
        app.dependency_overrides[tasks.get_async_result_class] = get_mock_async_result_class
        print(f"[DEBUG] Updated dependency overrides: {app.dependency_overrides}")
        
        try:
            # Act
            print("\n[DEBUG] Sending request to API for retry task...")
            print(f"[DEBUG] Request URL: /api/v1/tasks/{task_id}")
            
            # Call the endpoint
            response = test_client.get(f"/api/v1/tasks/{task_id}")
            print(f"[DEBUG] Response status: {response.status_code}")
            
            # Print response headers and body for debugging
            print(f"[DEBUG] Response headers: {dict(response.headers)}")
            response_data = response.json()
            print(f"[DEBUG] Response data: {response_data}")
            
            # Assert
            assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
            data = response_data
            
            print(f"[DEBUG] Verifying response data...")
            assert data["task_id"] == task_id, f"Expected task_id '{task_id}', got '{data['task_id']}'"
            assert data["status"] == "RETRY", f"Expected status 'RETRY', got '{data['status']}'"
            assert data.get("result") == retry_message, f"Expected result '{retry_message}', got '{data.get('result')}'"
            
            print("[DEBUG] All assertions passed!")
        except Exception as e:
            print(f"[DEBUG] Test failed with exception: {str(e)}")
            print("[DEBUG] Current app.dependency_overrides:", app.dependency_overrides)
            raise
        finally:
            # Clean up the overrides
            print("\n[DEBUG] Cleaning up dependency overrides")
            app.dependency_overrides = {}
            print(f"[DEBUG] Final dependency overrides: {app.dependency_overrides}")

def test_get_task_status_with_large_result(client, monkeypatch):
    """Test getting the status of a task with a large result."""
    # Import the tasks module to access its attributes
    from crypto_news_aggregator.api.v1 import tasks
    from fastapi.testclient import TestClient
    from crypto_news_aggregator.main import app
    
    print("\n[DEBUG] Starting test_get_task_status_with_large_result")
    
    # Arrange
    task_id = 'large-result-task-id'
    large_result = {"data": ["x" * 1000] * 1000}  # Large result
    
    # Create a mock AsyncResult class for a task with a large result
    class MockAsyncResult:
        def __init__(self, task_id, **kwargs):
            print(f"[DEBUG] Creating LargeResult MockAsyncResult with task_id={task_id}, kwargs={kwargs}")
            self.id = task_id
            self.task_id = task_id
            self.status = 'SUCCESS'
            self._result = large_result
            self._ready = True
            
        def ready(self):
            print(f"[DEBUG] LargeResult MockAsyncResult.ready() called, returning {self._ready}")
            return self._ready
            
        @property
        def result(self):
            print("[DEBUG] LargeResult MockAsyncResult.result called, returning large result")
            return self._result
    
    # Create a function to return our mock class
    def get_mock_async_result_class():
        print("[DEBUG] In get_mock_async_result_class, returning MockAsyncResult")
        return MockAsyncResult
    
    # Create a new test client with our overrides
    with TestClient(app) as test_client:
        # Override the dependency in the existing app
        print("[DEBUG] Setting up dependency override...")
        app.dependency_overrides[tasks.get_async_result_class] = get_mock_async_result_class
        print(f"[DEBUG] Updated dependency overrides: {app.dependency_overrides}")
        
        try:
            # Act
            print("\n[DEBUG] Sending request to API for task with large result...")
            print(f"[DEBUG] Request URL: /api/v1/tasks/{task_id}")
            
            # Call the endpoint
            response = test_client.get(f"/api/v1/tasks/{task_id}")
            print(f"[DEBUG] Response status: {response.status_code}")
            
            # Print response headers and body for debugging (truncate the actual data for readability)
            print(f"[DEBUG] Response headers: {dict(response.headers)}")
            response_data = response.json()
            
            # Print the raw response data for debugging
            print(f"[DEBUG] Raw response data: {response_data}")
            
            # Print the type and structure of the response data
            print(f"[DEBUG] Response data type: {type(response_data)}")
            if isinstance(response_data, dict):
                print("[DEBUG] Response data keys:", response_data.keys())
                if "result" in response_data:
                    print("[DEBUG] Result type:", type(response_data["result"]))
                    print("[DEBUG] Full result content:", response_data["result"])
                    if isinstance(response_data["result"], dict):
                        print("[DEBUG] Result keys:", response_data["result"].keys())
                        if "data" in response_data["result"]:
                            data = response_data["result"]["data"]
                            print("[DEBUG] Data type:", type(data))
                            if isinstance(data, list):
                                print("[DEBUG] Data length:", len(data))
                                if len(data) > 0:
                                    print("[DEBUG] First item type:", type(data[0]))
                                    print("[DEBUG] First item content (first 100 chars):", str(data[0])[:100])
                            elif isinstance(data, str):
                                print("[DEBUG] Data content (first 100 chars):", data[:100])
                            else:
                                print("[DEBUG] Data content:", data)
                    else:
                        print("[DEBUG] Result content (first 100 chars):", str(response_data["result"])[:100])
            
            # Print the full response content for debugging
            print("[DEBUG] Full response content:", response.content.decode()[:500] + "..." if len(response.content) > 500 else response.content.decode())
            
            # Assert
            assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
            data = response_data
            
            print(f"[DEBUG] Verifying response data...")
            assert data["task_id"] == task_id, f"Expected task_id '{task_id}', got '{data['task_id']}'"
            assert data["status"] == "SUCCESS", f"Expected status 'SUCCESS', got '{data['status']}'"
            assert "result" in data, "Expected 'result' in response"
            # The API returns the result directly in the response
            assert isinstance(data["result"], dict), f"Expected result to be a dict, got {type(data['result'])}"
            assert "data" in data["result"], "Expected 'data' key in result"
            assert len(data["result"]["data"]) == 1000, f"Expected 1000 items in result data, got {len(data['result']['data'])}"
            
            print("[DEBUG] All assertions passed!")
        except Exception as e:
            print(f"[DEBUG] Test failed with exception: {str(e)}")
            print("[DEBUG] Current app.dependency_overrides:", app.dependency_overrides)
            raise
        finally:
            # Clean up the overrides
            print("\n[DEBUG] Cleaning up dependency overrides")
            app.dependency_overrides = {}
            print(f"[DEBUG] Final dependency overrides: {app.dependency_overrides}")

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
async def test_get_task_status_with_exception():
    """Test handling of exceptions when getting task status."""
    # Arrange
    task_id = 'exceptional-task-id'
    
    # Create a mock AsyncResult that raises an exception
    class ExceptionalMockAsyncResult:
        def __init__(self, task_id):
            self._id = task_id
            
        @property
        def id(self):
            return self._id
            
        @property
        def status(self):
            print("[DEBUG] Accessing status property")
            raise Exception("Failed to get status")
            
        @property
        def result(self):
            print("[DEBUG] Accessing result property")
            return None
            
        def ready(self):
            print("[DEBUG] Calling ready() method")
            return False
    
    # Create a function that will return our mock AsyncResult
    def get_mock_async_result():
        def _mock_async_result(task_id):
            print(f"[DEBUG] Creating new ExceptionalMockAsyncResult for task_id: {task_id}")
            return ExceptionalMockAsyncResult(task_id)
        return _mock_async_result
    
    # Override the dependency
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from crypto_news_aggregator.api.v1.tasks import router, get_async_result_class
    
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    
    # Apply the dependency override
    app.dependency_overrides[get_async_result_class] = get_mock_async_result
    
    # Create a new test client with our app
    test_client = TestClient(app)
    
    # Act
    print(f"[DEBUG] Sending request to API for task that raises an exception...")
    response = test_client.get(f"/api/v1/tasks/{task_id}")
    print(f"[DEBUG] Response status: {response.status_code}")
    print(f"[DEBUG] Response content: {response.text}")
    
    # Assert
    # The API should return a 200 status with an error in the response
    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
    
    data = response.json()
    print(f"[DEBUG] Response data: {data}")
    
    # The endpoint should include the task_id and status in the response
    assert "task_id" in data, "Expected 'task_id' in response"
    assert data["task_id"] == task_id, f"Expected task_id '{task_id}', got '{data.get('task_id')}'"
    
    # The endpoint should include the error message in the response
    assert "error" in data, "Expected 'error' in response"
    assert "Failed to get status" in data["error"], \
        f"Expected error message to contain 'Failed to get status', got: {data.get('error')}"
    
    print("[DEBUG] All assertions passed!")
    
    # Clean up the overrides
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_get_task_status_with_serialization_error():
    """Test handling of non-serializable task results."""
    # Arrange
    task_id = 'serialization-error-task-id'
    
    # Create a non-serializable object (function)
    def non_serializable():
        pass
    
    # Create a mock AsyncResult that returns a non-serializable result
    class NonSerializableMockAsyncResult:
        def __init__(self, task_id):
            self._id = task_id
            self._status = "SUCCESS"
            self._result = {"func": non_serializable}
            
        @property
        def id(self):
            return self._id
            
        @property
        def status(self):
            return self._status
            
        @property
        def result(self):
            # Return a non-serializable object (function)
            return self._result
            
        def ready(self):
            return True
            
        def get(self, *args, **kwargs):
            return self._result
    
    # Create a function that will return our mock AsyncResult
    def get_mock_async_result():
        def _mock_async_result(task_id):
            print(f"[DEBUG] Creating NonSerializableMockAsyncResult for task_id: {task_id}")
            return NonSerializableMockAsyncResult(task_id)
        return _mock_async_result
    
    # Override the dependency
    from fastapi import FastAPI, HTTPException
    from fastapi.testclient import TestClient
    from fastapi.responses import JSONResponse
    from crypto_news_aggregator.api.v1.tasks import router, get_async_result_class, get_task_status
    
    # Create a custom app with a modified endpoint to test the serialization error
    app = FastAPI()
    
    # Add a custom exception handler for serialization errors
    @app.exception_handler(Exception)
    async def handle_serialization_error(request, exc):
        if isinstance(exc, (TypeError, ValueError)) and "not JSON serializable" in str(exc):
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Failed to serialize task result",
                    "error": str(exc)
                }
            )
        raise exc
    
    # Include the original router
    app.include_router(router, prefix="/api/v1")
    
    # Apply the dependency override
    app.dependency_overrides[get_async_result_class] = get_mock_async_result
    
    # Create a new test client with our app
    test_client = TestClient(app)
    
    try:
        # Act
        print(f"[DEBUG] Sending request to API for task with non-serializable result...")
        response = test_client.get(f"/api/v1/tasks/{task_id}")
        print(f"[DEBUG] Response status: {response.status_code}")
        print(f"[DEBUG] Response content: {response.text}")
        
        # Assert - The endpoint should return a 200 status with an error in the response
        assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
        
        data = response.json()
        print(f"[DEBUG] Response data: {data}")
        
        # The endpoint should include the task_id and status in the response
        assert "task_id" in data, "Expected 'task_id' in response"
        assert data["task_id"] == task_id, f"Expected task_id '{task_id}', got '{data.get('task_id')}'"
        
        # The endpoint should include an error message in the response
        assert "error" in data, "Expected 'error' in response"
        assert "not JSON serializable" in data["error"], \
            f"Expected serialization error message, got: {data['error']}"
        
        print("[DEBUG] All assertions passed!")
    except Exception as e:
        print(f"[DEBUG] Test failed with exception: {str(e)}")
        raise
    finally:
        # Clean up the overrides
        app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_get_task_status_with_custom_status():
    """Test handling of custom task status values."""
    # Arrange
    task_id = 'custom-status-task-id'
    custom_status = 'CUSTOM_STATUS'
    
    # Create a mock AsyncResult with custom status using the test utility
    from tests.test_utils import MockAsyncResult
    
    # Create a function that will return our mock AsyncResult
    def get_mock_async_result():
        def _mock_async_result(task_id):
            return MockAsyncResult(
                task_id=task_id,
                status=custom_status,
                result={"custom": "result"},
                ready=True
            )
        return _mock_async_result
    
    # Override the dependency
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from crypto_news_aggregator.api.v1.tasks import router, get_async_result_class
    
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    
    # Apply the dependency override
    app.dependency_overrides[get_async_result_class] = get_mock_async_result
    
    # Create a new test client with our app
    test_client = TestClient(app)
    
    try:
        # Act
        response = test_client.get(f"/api/v1/tasks/{task_id}")
        
        # Assert
        assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
        data = response.json()
        
        assert data["task_id"] == task_id, f"Expected task_id {task_id}, got {data.get('task_id')}"
        assert data["status"] == custom_status, f"Expected status '{custom_status}', got {data.get('status')}"
        assert "result" in data, "Expected 'result' in response"
        assert data["result"]["custom"] == "result", "Expected custom result in response"
        
    finally:
        # Clean up the overrides
        app.dependency_overrides = {}

from unittest.mock import patch, MagicMock
from tests.test_utils import create_mock_async_result

@pytest.mark.asyncio
async def test_trigger_news_fetch(client, test_user, user_access_token):
    """Test triggering a news fetch task."""
    # Arrange
    headers = {"Authorization": f"Bearer {user_access_token}"}
    
    # Create a mock task and result
    mock_task = MagicMock()
    mock_result = MagicMock()
    
    # Generate a UUID for the task ID that matches the format returned by the API
    import uuid
    task_id = str(uuid.uuid4())
    mock_result.id = task_id
    mock_task.delay.return_value = mock_result
    
    print("\n[DEBUG] Before patching:")
    print(f"- mock_task: {mock_task}")
    print(f"- mock_result: {mock_result}")
    print(f"- mock_result.id: {getattr(mock_result, 'id', 'NOT SET')}")
    
    # Patch the fetch_news task at the module where it's imported in the API
    with patch('src.crypto_news_aggregator.api.v1.tasks.fetch_news', mock_task) as mock_patch:
        print("\n[DEBUG] After patching:")
        print(f"- mock_patch: {mock_patch}")
        print(f"- mock_task.delay.call_args_list: {mock_task.delay.call_args_list}")
        
        # Act - Make request to the endpoint with source as a query parameter
        print("\n[DEBUG] Making API request...")
        response = client.post(
            "/api/v1/news/fetch?source=test-source",
            headers=headers,
            json={}  # Empty JSON body since we're using query parameters
        )
        
        print("\n[DEBUG] After API call:")
        print(f"- Response status: {response.status_code}")
        print(f"- Response body: {response.text}")
        print(f"- mock_task.delay.call_args_list: {mock_task.delay.call_args_list}")
        print(f"- mock_task.delay.called: {mock_task.delay.called}")
        
        # Assert
        assert response.status_code == 202, f"Expected status code 202 (Accepted), got {response.status_code}. Response: {response.text}"
        data = response.json()
        
        # Verify the response has the expected structure
        assert "task_id" in data, f"Response missing 'task_id' field: {data}"
        assert "status" in data, f"Response missing 'status' field: {data}"
        
        # Verify the task ID is a valid UUID
        try:
            uuid.UUID(data["task_id"])
        except ValueError:
            assert False, f"task_id '{data['task_id']}' is not a valid UUID"
            
        assert data["status"] == "PENDING", f"Expected status 'PENDING', got '{data.get('status')}'"
        
        # Verify the task was called with the correct arguments
        print("\n[DEBUG] Verifying mock was called...")
        print(f"- mock_task.delay.call_args_list: {mock_task.delay.call_args_list}")
        
        # The task is called with source as a positional argument, not a keyword argument
        # So we need to check the first positional argument
        mock_task.delay.assert_called_once()
        args, kwargs = mock_task.delay.call_args
        assert len(args) == 1, f"Expected 1 positional argument, got {len(args)}"
        assert args[0] == "test-source", f"Expected source='test-source', got {args[0]}"
        assert not kwargs, f"Expected no keyword arguments, got {kwargs}"
    
@pytest.mark.asyncio
async def test_trigger_sentiment_analysis(client, test_user, user_access_token):
    """Test triggering sentiment analysis for an article."""
    # Arrange
    headers = {"Authorization": f"Bearer {user_access_token}"}
    article_id = 123
    task_id = 'test-sentiment-task-id'
    
    # Create a mock task that returns a mock result with an id when delay() is called
    mock_task = MagicMock()
    mock_result = MagicMock()
    mock_result.id = task_id
    mock_task.delay.return_value = mock_result
    
    # Patch the analyze_sentiment task at the module where it's imported in the API
    with patch('src.crypto_news_aggregator.api.v1.tasks.analyze_sentiment', mock_task) as mock_patch:
        print("\n[DEBUG] Making sentiment analysis API request...")
        # Act - Make request to the endpoint
        response = client.post(
            f"/api/v1/sentiment/analyze/{article_id}",
            headers=headers
        )
        
        print(f"[DEBUG] Response status: {response.status_code}")
        print(f"[DEBUG] Response body: {response.text}")
        
        # Assert
        assert response.status_code == 202, f"Expected status code 202 (Accepted), got {response.status_code}. Response: {response.text}"
        data = response.json()
        assert data["task_id"] == task_id, f"Expected task_id '{task_id}', got '{data.get('task_id')}'"
        assert data["status"] == "PENDING", f"Expected status 'PENDING', got '{data.get('status')}'"
        
        # Verify the task was called with the correct arguments
        # The task is called with article_id as a positional argument, not a keyword argument
        print(f"[DEBUG] Mock call args: {mock_task.delay.call_args}")
        mock_task.delay.assert_called_once()
        args, kwargs = mock_task.delay.call_args
        assert len(args) == 1, f"Expected 1 positional argument, got {len(args)}"
        assert args[0] == article_id, f"Expected article_id={article_id}, got {args[0]}"
        assert not kwargs, f"Expected no keyword arguments, got {kwargs}"

@pytest.mark.asyncio
async def test_trigger_trends_update(client, test_user, user_access_token):
    """Test triggering a trends update task."""
    # Arrange
    headers = {"Authorization": f"Bearer {user_access_token}"}
    task_id = 'test-trends-update-task-id'
    
    # Create a mock task that returns a mock result with an id when delay() is called
    mock_task = MagicMock()
    mock_result = MagicMock()
    mock_result.id = task_id
    mock_task.delay.return_value = mock_result
    
    print("\n[DEBUG] Before patching trends update task...")
    
    # Patch the update_trends task at the module where it's imported in the API
    with patch('src.crypto_news_aggregator.api.v1.tasks.update_trends', mock_task) as mock_patch:
        print("[DEBUG] Making trends update API request...")
        # Act - Make request to the endpoint
        response = client.post(
            "/api/v1/trends/update",
            headers=headers
        )
        
        print(f"[DEBUG] Response status: {response.status_code}")
        print(f"[DEBUG] Response body: {response.text}")
        
        # Assert
        assert response.status_code == 202, f"Expected status code 202 (Accepted), got {response.status_code}. Response: {response.text}"
        data = response.json()
        assert data["task_id"] == task_id, f"Expected task_id '{task_id}', got '{data.get('task_id')}'"
        assert data["status"] == "PENDING", f"Expected status 'PENDING', got '{data.get('status')}'"
        
        # Verify the task was called with no arguments
        print(f"[DEBUG] Mock call args: {mock_task.delay.call_args}")
        mock_task.delay.assert_called_once()
        args, kwargs = mock_task.delay.call_args
        assert len(args) == 0, f"Expected no positional arguments, got {len(args)}"
        assert not kwargs, f"Expected no keyword arguments, got {kwargs}"



@pytest.mark.asyncio
async def test_get_task_status_with_timeout():
    """Test handling of task status check timeout."""
    # Arrange
    task_id = 'timeout-task-id'
    
    # Create a mock AsyncResult that raises TimeoutError when ready() is called
    from tests.test_utils import MockAsyncResult
    
    # Create a function that will return our mock AsyncResult
    def get_mock_async_result():
        def _mock_async_result(task_id):
            # Create a mock result that will raise TimeoutError when ready() is called
            mock_result = MockAsyncResult(
                task_id=task_id,
                status='PENDING',
                ready=MagicMock(side_effect=TimeoutError("Task timed out"))
            )
            return mock_result
        return _mock_async_result
    
    # Override the dependency
    from fastapi import FastAPI, status
    from fastapi.testclient import TestClient
    from crypto_news_aggregator.api.v1.tasks import router, get_async_result_class
    
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    
    # Apply the dependency override
    app.dependency_overrides[get_async_result_class] = get_mock_async_result
    
    # Create a new test client with our app
    test_client = TestClient(app)
    
    try:
        # Act
        response = test_client.get(f"/api/v1/tasks/{task_id}")
        print(f"[DEBUG] Response status: {response.status_code}")
        print(f"[DEBUG] Response content: {response.text}")
        
        # Assert - The endpoint should return a 200 status with an error in the response
        assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
        
        data = response.json()
        print(f"[DEBUG] Response data: {data}")
        
        # The endpoint should include the task_id and status in the response
        assert "task_id" in data, "Expected 'task_id' in response"
        assert data["task_id"] == task_id, f"Expected task_id '{task_id}', got '{data.get('task_id')}'"
        
        # The endpoint should include an error message in the response
        assert "error" in data, "Expected 'error' in response"
        assert "Task timed out" in data["error"], \
            f"Expected error message to contain 'Task timed out', got: {data.get('error')}"
            
    finally:
        # Clean up the overrides
        app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_get_task_status_with_connection_error():
    """Test handling of connection errors when checking task status."""
    # Arrange
    task_id = 'connection-error-task-id'
    error_message = "Failed to connect to message broker"
    
    # Create a mock AsyncResult that raises ConnectionError when status is accessed
    from tests.test_utils import MockAsyncResult
    from unittest.mock import PropertyMock
    
    # Create a function that will return our mock AsyncResult
    def get_mock_async_result():
        def _mock_async_result(task_id):
            # Create a mock result that raises ConnectionError when status is accessed
            mock_result = MockAsyncResult(
                task_id=task_id,
                status='FAILURE',  # Set a default status
                error=ConnectionError(error_message),  # Store the error
                ready=False  # Set ready to False to simulate a pending task
            )
            
            # Override the status property to raise ConnectionError
            type(mock_result).status = PropertyMock(
                side_effect=ConnectionError(error_message)
            )
            
            # Ensure ready() returns False to simulate a pending task
            mock_result.ready.return_value = False
            
            return mock_result
            
        return _mock_async_result
    
    # Override the dependency
    from fastapi import FastAPI, status
    from fastapi.testclient import TestClient
    from crypto_news_aggregator.api.v1.tasks import router, get_async_result_class
    
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    
    # Apply the dependency override
    app.dependency_overrides[get_async_result_class] = get_mock_async_result
    
    # Create a new test client with our app
    test_client = TestClient(app)
    
    try:
        # Act
        response = test_client.get(f"/api/v1/tasks/{task_id}")
        
        # Assert
        # The API should return a 200 status code with error details in the response
        assert response.status_code == status.HTTP_200_OK, \
            f"Expected status code 200, got {response.status_code}"
        
        data = response.json()
        
        assert data["task_id"] == task_id, \
            f"Expected task_id {task_id}, got {data.get('task_id')}"
        assert data["status"] == "FAILURE", \
            f"Expected status 'FAILURE', got {data.get('status')}"
        assert "error" in data, "Expected 'error' in response"
        assert error_message in data["error"], \
            f"Expected error message to contain '{error_message}', got: {data.get('error')}"
    finally:
        # Clean up the overrides
        app.dependency_overrides = {}

@pytest.mark.skip(reason="Endpoint not implemented in the API")
def test_get_article_sentiment(client, mock_db_session, test_user, user_access_token):
    """Test getting sentiment for an article."""
    # Arrange
    headers = {"Authorization": f"Bearer {user_access_token}"}
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

def test_trigger_sentiment_analysis_invalid_article(client, test_user, user_access_token):
    """Test triggering sentiment analysis with a non-existent article ID."""
    # Arrange
    headers = {"Authorization": f"Bearer {user_access_token}"}
    non_existent_article_id = 9999
    task_id = 'test-sentiment-task-id'
    
    # Create a mock task that returns a mock result with an id when delay() is called
    mock_task = MagicMock()
    mock_result = MagicMock()
    mock_result.id = task_id
    mock_task.delay.return_value = mock_result
    
    # Patch the analyze_sentiment task at the module where it's imported in the API
    with patch('src.crypto_news_aggregator.api.v1.tasks.analyze_sentiment', mock_task) as mock_patch:
        print("\n[DEBUG] Making sentiment analysis API request for invalid article...")
        # Act - Make request with non-existent article ID
        response = client.post(
            f"/api/v1/sentiment/analyze/{non_existent_article_id}",
            headers=headers
        )
        
        print(f"[DEBUG] Response status: {response.status_code}")
        print(f"[DEBUG] Response body: {response.text}")
        
        # Assert - Verify the task was still created (the endpoint doesn't check article existence)
        assert response.status_code == 202, f"Expected status code 202 (Accepted), got {response.status_code}. Response: {response.text}"
        data = response.json()
        assert data["task_id"] == task_id, f"Expected task_id '{task_id}', got '{data.get('task_id')}'"
        assert data["status"] == "PENDING", f"Expected status 'PENDING', got '{data.get('status')}'"
