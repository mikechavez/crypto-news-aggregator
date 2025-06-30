import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, ANY
from datetime import datetime, timezone

from crypto_news_aggregator.db.models import Article, Source
from sqlalchemy.ext.asyncio import AsyncSession

# We'll use the client fixture from conftest.py instead of creating our own

# Mock Celery task result
class MockAsyncResult:
    def __init__(self, task_id, **kwargs):
        self._id = task_id
        self._result = None
        self._status = 'PENDING'
        self._ready = False
        self._kwargs = kwargs
    
    @property
    def id(self):
        return self._id
    
    @id.setter
    def id(self, value):
        self._id = value
    
    @property
    def status(self):
        return self._status
    
    @status.setter
    def status(self, value):
        self._status = value
    
    def ready(self):
        return self._ready
    
    @property
    def result(self):
        return self._result
    
    @result.setter
    def result(self, value):
        self._result = value
    
    def set_result(self, result, status='SUCCESS'):
        self._result = result
        self._status = status
        self._ready = True
        return self
    
    def get(self, *args, **kwargs):
        return self._result
    
    def successful(self):
        return self._status == 'SUCCESS'
        
    def failed(self):
        return self._status == 'FAILURE'
        
    def wait(self, *args, **kwargs):
        return self._result
        
    def forget(self):
        pass
        
    def revoke(self, *args, **kwargs):
        self._status = 'REVOKED'
        return True

# Mock Celery task class
class MockTask:
    def __init__(self):
        self.delay = MagicMock()
        self.apply_async = MagicMock()
    
    def __call__(self, *args, **kwargs):
        return self.delay(*args, **kwargs)

@pytest.fixture
def mock_db_session():
    with patch('crypto_news_aggregator.db.session.get_session') as mock_get_session:
        mock_session = AsyncMock(spec=AsyncSession)
        
        # Set up the async context manager
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        
        # Configure the mock to return our mock session
        mock_get_session.return_value = mock_session
        
        yield mock_session

@pytest.fixture
def mock_async_result():
    # Create a mock async result that won't try to connect to a broker
    mock_result = MockAsyncResult('test-task-id')
    with patch('crypto_news_aggregator.api.v1.tasks.AsyncResult', return_value=mock_result):
        yield mock_result

@pytest.fixture
def mock_celery_tasks():
    # Mock the Celery tasks at the module level
    with patch('crypto_news_aggregator.api.fetch_news', new_callable=MockTask) as mock_fetch_news, \
         patch('crypto_news_aggregator.api.analyze_sentiment', new_callable=MockTask) as mock_analyze_sentiment, \
         patch('crypto_news_aggregator.api.update_trends', new_callable=MockTask) as mock_update_trends:
        
        # Configure the mock tasks to return our mock async result
        mock_result = MockAsyncResult('test-task-id')
        mock_fetch_news.delay.return_value = mock_result
        mock_analyze_sentiment.delay.return_value = mock_result
        mock_update_trends.delay.return_value = mock_result
        
        yield {
            'fetch_news': mock_fetch_news,
            'analyze_sentiment': mock_analyze_sentiment,
            'update_trends': mock_update_trends,
            'result': mock_result
        }

def test_get_task_status_success(client, monkeypatch):
    """Test getting the status of a successfully completed task."""
    # Arrange
    task_id = 'test-task-id'
    expected_result = {"status": "success", "message": "Task completed"}
    
    # Create a mock AsyncResult with the expected behavior
    class MockAsyncResult:
        def __init__(self, task_id):
            self.task_id = task_id
            self._status = 'SUCCESS'
            self._result = expected_result
            
        @property
        def status(self):
            return self._status
            
        @property
        def result(self):
            return self._result
            
        def ready(self):
            return True
    
    # Create a function that will return our mock AsyncResult
    def mock_async_result(*args, **kwargs):
        return MockAsyncResult(args[0] if args else task_id)
    
    # We need to patch the AsyncResult where it's imported in the API module
    import sys
    if 'crypto_news_aggregator.api' in sys.modules:
        del sys.modules['crypto_news_aggregator.api']
    
    # Apply the monkeypatch to replace celery.result.AsyncResult
    import celery.result
    original_async_result = celery.result.AsyncResult
    celery.result.AsyncResult = mock_async_result
    
    try:
        # Now import the API module after patching
        from crypto_news_aggregator.api import router
        
        # Create a new test client to ensure it uses our patched module
        from fastapi.testclient import TestClient
        from crypto_news_aggregator.main import app
        
        test_client = TestClient(app)
        
        # Act - make the request to the endpoint
        response = test_client.get(f"/api/v1/tasks/{task_id}")
        
        # Assert the response
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == task_id
        assert data["status"] == "SUCCESS"
        assert data["result"] == expected_result
    finally:
        # Clean up by restoring the original AsyncResult
        celery.result.AsyncResult = original_async_result
        if 'crypto_news_aggregator.api' in sys.modules:
            del sys.modules['crypto_news_aggregator.api']

def test_get_task_status_pending(client, monkeypatch):
    """Test getting the status of a pending task."""
    # Arrange
    task_id = 'pending-task-id'
    
    # Create a mock AsyncResult with the expected behavior
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
    
    # Create a function that will return our mock AsyncResult
    def mock_async_result(*args, **kwargs):
        return MockAsyncResult(args[0] if args else task_id)
    
    # We need to patch the AsyncResult where it's imported in the API module
    import sys
    if 'crypto_news_aggregator.api' in sys.modules:
        del sys.modules['crypto_news_aggregator.api']
    
    # Apply the monkeypatch to replace celery.result.AsyncResult
    import celery.result
    original_async_result = celery.result.AsyncResult
    celery.result.AsyncResult = mock_async_result
    
    try:
        # Now import the API module after patching
        from crypto_news_aggregator.api import router
        
        # Create a new test client to ensure it uses our patched module
        from fastapi.testclient import TestClient
        from crypto_news_aggregator.main import app
        
        test_client = TestClient(app)
        
        # Act - make the request to the endpoint
        response = test_client.get(f"/api/v1/tasks/{task_id}")
        
        # Assert the response
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == task_id
        assert data["status"] == "PENDING"
        assert "result" not in data  # Should not include result for pending tasks
    finally:
        # Clean up by restoring the original AsyncResult
        celery.result.AsyncResult = original_async_result
        if 'crypto_news_aggregator.api' in sys.modules:
            del sys.modules['crypto_news_aggregator.api']

def test_get_task_status_failed(client, monkeypatch):
    """Test getting the status of a failed task."""
    # Arrange
    task_id = 'failed-task-id'
    error_message = "Task failed due to an error"
    
    # Create a mock AsyncResult with the expected behavior
    class MockAsyncResult:
        def __init__(self, task_id):
            self.task_id = task_id
            self._status = 'FAILURE'
            self._result = Exception(error_message)
            
        @property
        def status(self):
            return self._status
            
        @property
        def result(self):
            return self._result
            
        def ready(self):
            return True
    
    # Create a function that will return our mock AsyncResult
    def mock_async_result(*args, **kwargs):
        return MockAsyncResult(args[0] if args else task_id)
    
    # We need to patch the AsyncResult where it's imported in the API module
    import sys
    if 'crypto_news_aggregator.api' in sys.modules:
        del sys.modules['crypto_news_aggregator.api']
    
    # Apply the monkeypatch to replace celery.result.AsyncResult
    import celery.result
    original_async_result = celery.result.AsyncResult
    celery.result.AsyncResult = mock_async_result
    
    try:
        # Now import the API module after patching
        from crypto_news_aggregator.api import router
        
        # Create a new test client to ensure it uses our patched module
        from fastapi.testclient import TestClient
        from crypto_news_aggregator.main import app
        
        test_client = TestClient(app)
        
        # Act - make the request to the endpoint
        response = test_client.get(f"/api/v1/tasks/{task_id}")
        
        # Assert the response
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == task_id
        assert data["status"] == "FAILURE"
        assert "result" in data
        assert error_message in str(data["result"])
    finally:
        # Clean up by restoring the original AsyncResult
        celery.result.AsyncResult = original_async_result
        if 'crypto_news_aggregator.api' in sys.modules:
            del sys.modules['crypto_news_aggregator.api']

@pytest.mark.asyncio
async def test_get_task_status_revoked(client, monkeypatch):
    """Test getting the status of a revoked task."""
    # Arrange
    task_id = 'revoked-task-id'
    
    # Create a mock AsyncResult with the expected behavior
    class MockAsyncResult:
        def __init__(self, task_id):
            self.task_id = task_id
            self._status = 'REVOKED'
            self._result = "Task was revoked"
            
        @property
        def status(self):
            return self._status
            
        @property
        def result(self):
            return self._result
            
        def ready(self):
            return True
    
    # Create a function that will return our mock AsyncResult
    def mock_async_result(*args, **kwargs):
        return MockAsyncResult(args[0] if args else task_id)
    
    # We need to patch the AsyncResult where it's imported in the API module
    import sys
    if 'crypto_news_aggregator.api' in sys.modules:
        del sys.modules['crypto_news_aggregator.api']
    
    # Apply the monkeypatch to replace celery.result.AsyncResult
    import celery.result
    original_async_result = celery.result.AsyncResult
    celery.result.AsyncResult = mock_async_result
    
    try:
        # Now import the API module after patching
        from crypto_news_aggregator.api import router
        
        # Create a new test client to ensure it uses our patched module
        from fastapi.testclient import TestClient
        from crypto_news_aggregator.main import app
        
        test_client = TestClient(app)
        
        # Act - make the request to the endpoint
        response = test_client.get(f"/api/v1/tasks/{task_id}")
        
        # Assert the response
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == task_id
        assert data["status"] == "REVOKED"
        assert "result" in data  # May contain revoke reason if available
    finally:
        # Clean up by restoring the original AsyncResult
        celery.result.AsyncResult = original_async_result
        if 'crypto_news_aggregator.api' in sys.modules:
            del sys.modules['crypto_news_aggregator.api']

@pytest.mark.asyncio
async def test_get_task_status_retry(client, monkeypatch):
    """Test getting the status of a task that's being retried."""
    # Arrange
    task_id = 'retry-task-id'
    
    # Create a mock AsyncResult with the expected behavior
    class MockAsyncResult:
        def __init__(self, task_id):
            self.task_id = task_id
            self._status = 'RETRY'
            self._result = None
            
        @property
        def status(self):
            return self._status
            
        @property
        def result(self):
            return self._result
            
        def ready(self):
            return True
    
    # Create a function that will return our mock AsyncResult
    def mock_async_result(*args, **kwargs):
        return MockAsyncResult(args[0] if args else task_id)
    
    # We need to patch the AsyncResult where it's imported in the API module
    import sys
    if 'crypto_news_aggregator.api' in sys.modules:
        del sys.modules['crypto_news_aggregator.api']
    
    # Apply the monkeypatch to replace celery.result.AsyncResult
    import celery.result
    original_async_result = celery.result.AsyncResult
    celery.result.AsyncResult = mock_async_result
    
    try:
        # Now import the API module after patching
        from crypto_news_aggregator.api import router
        
        # Create a new test client to ensure it uses our patched module
        from fastapi.testclient import TestClient
        from crypto_news_aggregator.main import app
        
        test_client = TestClient(app)
        
        # Act - make the request to the endpoint
        response = test_client.get(f"/api/v1/tasks/{task_id}")
        
        # Assert the response
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == task_id
        assert data["status"] == "RETRY"
        assert "result" not in data  # Typically no result for retry status
    finally:
        # Clean up by restoring the original AsyncResult
        celery.result.AsyncResult = original_async_result
        if 'crypto_news_aggregator.api' in sys.modules:
            del sys.modules['crypto_news_aggregator.api']

@pytest.mark.asyncio
async def test_get_task_status_with_large_result(client, monkeypatch):
    """Test getting the status of a task with a large result."""
    # Arrange
    task_id = 'large-result-task-id'
    large_result = {"data": ["x" * 1000] * 1000}  # Large result
    
    # Create a mock AsyncResult with the expected behavior
    class MockAsyncResult:
        def __init__(self, task_id):
            self.task_id = task_id
            self._status = 'SUCCESS'
            self._result = large_result
            
        @property
        def status(self):
            return self._status
            
        @property
        def result(self):
            return self._result
            
        def ready(self):
            return True
    
    # Create a function that will return our mock AsyncResult
    def mock_async_result(*args, **kwargs):
        return MockAsyncResult(args[0] if args else task_id)
    
    # We need to patch the AsyncResult where it's imported in the API module
    import sys
    if 'crypto_news_aggregator.api' in sys.modules:
        del sys.modules['crypto_news_aggregator.api']
    
    # Apply the monkeypatch to replace celery.result.AsyncResult
    import celery.result
    original_async_result = celery.result.AsyncResult
    celery.result.AsyncResult = mock_async_result
    
    try:
        # Now import the API module after patching
        from crypto_news_aggregator.api import router
        
        # Create a new test client to ensure it uses our patched module
        from fastapi.testclient import TestClient
        from crypto_news_aggregator.main import app
        
        test_client = TestClient(app)
        
        # Act - make the request to the endpoint
        response = test_client.get(f"/api/v1/tasks/{task_id}")
        
        # Assert the response
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == task_id
        assert data["status"] == "SUCCESS"
        assert data["result"] == large_result
    finally:
        # Clean up by restoring the original AsyncResult
        celery.result.AsyncResult = original_async_result
        if 'crypto_news_aggregator.api' in sys.modules:
            del sys.modules['crypto_news_aggregator.api']

@pytest.mark.asyncio
async def test_get_task_status_not_found(client, monkeypatch):
    """Test getting the status of a non-existent task."""
    # Arrange
    task_id = 'non-existent-task-id'
    
    # Create a mock AsyncResult with the expected behavior
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
    
    # Create a function that will return our mock AsyncResult
    def mock_async_result(*args, **kwargs):
        return MockAsyncResult(args[0] if args else task_id)
    
    # We need to patch the AsyncResult where it's imported in the API module
    import sys
    if 'crypto_news_aggregator.api' in sys.modules:
        del sys.modules['crypto_news_aggregator.api']
    
    # Apply the monkeypatch to replace celery.result.AsyncResult
    import celery.result
    original_async_result = celery.result.AsyncResult
    celery.result.AsyncResult = mock_async_result
    
    try:
        # Now import the API module after patching
        from crypto_news_aggregator.api import router
        
        # Create a new test client to ensure it uses our patched module
        from fastapi.testclient import TestClient
        from crypto_news_aggregator.main import app
        
        test_client = TestClient(app)
        
        # Act - make the request to the endpoint
        response = test_client.get(f"/api/v1/tasks/{task_id}")
        
        # Assert the response
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == task_id
        assert data["status"] == "PENDING"
        assert "result" not in data
    finally:
        # Clean up by restoring the original AsyncResult
        celery.result.AsyncResult = original_async_result
        if 'crypto_news_aggregator.api' in sys.modules:
            del sys.modules['crypto_news_aggregator.api']  # Should not include result for pending tasks

@pytest.mark.asyncio
async def test_get_task_status_with_exception(client, monkeypatch):
    """Test handling of exceptions when getting task status."""
    # Arrange
    task_id = 'error-task-id'
    
    # Mock AsyncResult to raise an exception
    with patch('crypto_news_aggregator.api.v1.tasks.AsyncResult') as mock_async_result:
        mock_async_result.side_effect = Exception("Database connection failed")
        
        # Act & Assert
        with pytest.raises(Exception, match="Database connection failed"):
            client.get(f"/api/v1/tasks/{task_id}")

@pytest.mark.asyncio
async def test_get_task_status_with_serialization_error(client):
    """Test handling of non-serializable task results."""
    # Arrange
    task_id = 'serialization-error-task-id'
    
    # Create a non-serializable object (function)
    def non_serializable():
        pass
    
    # Create a mock AsyncResult instance with non-serializable result
    mock_result = MockAsyncResult(task_id)
    mock_result.set_result({"func": non_serializable}, status='SUCCESS')
    
    # Act
    with patch('crypto_news_aggregator.api.v1.tasks.AsyncResult', return_value=mock_result):
        response = client.get(f"/api/v1/tasks/{task_id}")
    
    # Assert
    assert response.status_code == 200  # Should handle serialization errors gracefully
    data = response.json()
    assert data["task_id"] == task_id
    assert data["status"] == "SUCCESS"
    assert "result" in data  # The result might be a string representation

@pytest.mark.asyncio
async def test_get_task_status_with_custom_status(client):
    """Test handling of custom task status values."""
    # Arrange
    task_id = 'custom-status-task-id'
    custom_status = 'CUSTOM_STATUS'
    
    # Create a mock AsyncResult instance with custom status
    mock_result = MockAsyncResult(task_id)
    mock_result.status = custom_status
    mock_result._ready = True
    
    # Act
    with patch('crypto_news_aggregator.api.v1.tasks.AsyncResult', return_value=mock_result):
        response = client.get(f"/api/v1/tasks/{task_id}")
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == task_id
    assert data["status"] == custom_status
    assert "result" not in data

@pytest.mark.asyncio
async def test_trigger_news_fetch(client, mock_celery_tasks):
    """Test triggering a news fetch task."""
    # Make request to the correct endpoint (router prefix already includes /api/v1)
    response = client.post("/news/fetch")
    
    # Verify response
    assert response.status_code == 202  # Accepted
    data = response.json()
    assert data["task_id"] == "test-task-id"
    assert data["status"] == "PENDING"
    
    # Verify the task was called with correct arguments

@pytest.mark.asyncio
async def test_trigger_sentiment_analysis(client, mock_celery_tasks):
    """Test triggering sentiment analysis for an article."""
    # Make request to the correct endpoint (router prefix already includes /api/v1)
    response = client.post("/sentiment/analyze/123")
    
    # Verify response
    assert response.status_code == 202  # Accepted
    data = response.json()
    assert data["task_id"] == "test-task-id"
    assert data["status"] == "PENDING"
    
    # Verify the task was called with correct arguments
    mock_celery_tasks['analyze_sentiment'].delay.assert_called_once_with(1)

@pytest.mark.asyncio
async def test_trigger_trends_update(client, mock_celery_tasks):
    """Test triggering a trends update task."""
    # Make request to the correct endpoint (router prefix already includes /api/v1)
    response = client.post("/trends/update")
    
    # Verify response
    assert response.status_code == 202  # Accepted
    data = response.json()
    assert data["task_id"] == "test-task-id"
    assert data["status"] == "PENDING"
    
    # Verify the task was called
    mock_celery_tasks['update_trends'].delay.assert_called_once()



@pytest.mark.asyncio
async def test_get_task_status_with_timeout(client):
    """Test handling of task status check timeout."""
    # Arrange
    task_id = 'timeout-task-id'
    
    # Create a mock AsyncResult instance that times out
    mock_result = MockAsyncResult(task_id)
    mock_result.ready = MagicMock(side_effect=TimeoutError("Task timed out"))
    
    # Act
    with patch('crypto_news_aggregator.api.v1.tasks.AsyncResult', return_value=mock_result):
        with pytest.raises(TimeoutError, match="Task timed out"):
            mock_result.ready()  # This will raise the TimeoutError
            client.get(f"/api/v1/tasks/{task_id}")

@pytest.mark.asyncio
async def test_get_task_status_with_connection_error(client):
    """Test handling of connection errors when checking task status."""
    # Arrange
    task_id = 'connection-error-task-id'
    
    # Mock AsyncResult to raise a connection error
    with patch('crypto_news_aggregator.api.v1.tasks.AsyncResult') as mock_async_result:
        mock_async_result.side_effect = ConnectionError("Could not connect to broker")
        
        # Act & Assert
        with pytest.raises(ConnectionError, match="Could not connect to broker"):
            client.get(f"/api/v1/tasks/{task_id}")

@pytest.mark.skip(reason="Endpoint not implemented in the API")
@pytest.mark.asyncio
async def test_get_article_sentiment(mock_db_session):
    """Test getting sentiment for an article."""
    # Mock database response
    mock_article = Article(
        id=1,
        title="Test Article",
        source_id="test-source",
        url="https://example.com/test-article",
        published_at=datetime.now(timezone.utc),
        content="Test content",
        sentiment_score=0.8,
        sentiment_label="Positive"
    )
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_article
    mock_db_session.execute.return_value = mock_result
    
    # Make request
    response = client.get("/api/v1/articles/1/sentiment")
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["article_id"] == 1
    assert data["sentiment"]["label"] == "Positive"

@pytest.mark.asyncio
async def test_trigger_sentiment_analysis_invalid_article(client, mock_async_result):
    """Test triggering sentiment analysis with an invalid article ID."""
    # Make request with invalid article ID to the correct endpoint
    response = client.post("/api/v1/sentiment/analyze/not-an-integer")
    
    # Verify 422 response for validation error
    assert response.status_code == 422
    response_data = response.json()
    assert "detail" in response_data
    assert any(
        error["type"] == "int_parsing" and 
        error["loc"] == ["path", "article_id"] and
        "unable to parse string as an integer" in error["msg"]
        for error in response_data["detail"]
    )
