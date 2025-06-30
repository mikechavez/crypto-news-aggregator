import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, ANY
from datetime import datetime, timezone

from crypto_news_aggregator.main import app
from crypto_news_aggregator.db.models import Article, Source
from sqlalchemy.ext.asyncio import AsyncSession

# Create test client
client = TestClient(app)

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

@pytest.mark.asyncio
async def test_get_task_status(client, mock_celery_app):
    """Test getting the status of a background task."""
    # Create a mock task result with SUCCESS status
    task_id = 'test-task-id'
    expected_result = "Task completed"
    
    # Create a mock AsyncResult instance
    mock_result = MockAsyncResult(task_id)
    mock_result.set_result(expected_result, status='SUCCESS')
    
    # Patch the AsyncResult class to return our mock
    with patch('crypto_news_aggregator.api.v1.tasks.AsyncResult', return_value=mock_result):
        # Make the API request
        response = client.get(f"/api/v1/tasks/{task_id}")
        
        # Verify the response
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == task_id
        assert data["status"] == "SUCCESS"
        assert data["result"] == expected_result
        def __str__(self):
            return f"<MockAsyncResult: {self.task_id} status={self.status} result={self.result}>"
    
    # Replace the AsyncResult class with our mock
    monkeypatch.setattr('crypto_news_aggregator.api.v1.tasks.AsyncResult', MockAsyncResult)
    
    # Now get a new reference to the patched AsyncResult
    from crypto_news_aggregator.api.v1.tasks import AsyncResult as PatchedAsyncResult
    
    # Create an instance of our mock
    mock_result = PatchedAsyncResult(task_id)
    print(f"[DEBUG] Created mock_result: {mock_result}")
    print(f"[DEBUG] mock_result.ready() returns: {mock_result.ready()}")
    
    # Make request - this will use our patched AsyncResult
    with caplog.at_level('DEBUG'):
        response = client.get(f"/api/v1/tasks/{task_id}")
        print(f"[DEBUG] Response status: {response.status_code}")
        print(f"[DEBUG] Response data: {response.json()}")
    
    # Verify response
    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
    data = response.json()
    
    print(f"[DEBUG] Response task_id: {data.get('task_id')} (expected: {task_id})")
    print(f"[DEBUG] Response status: {data.get('status')} (expected: SUCCESS)")
    print(f"[DEBUG] Response result: {data.get('result')} (expected: {expected_result})")
    
    assert data["task_id"] == task_id, f"Expected task_id {task_id}, got {data['task_id']}"
    assert data["status"] == "SUCCESS", f"Expected status 'SUCCESS', got {data['status']}"
    assert data["result"] == expected_result, f"Expected result {expected_result}, got {data['result']}"

@pytest.mark.asyncio
async def test_trigger_news_fetch(mock_celery_tasks):
    """Test triggering a news fetch task."""
    # Make request to the correct endpoint
    response = client.post("/api/v1/news/fetch")
    
    # Verify response
    assert response.status_code == 202  # Accepted
    data = response.json()
    assert data["task_id"] == "test-task-id"
    assert data["status"] == "PENDING"
    
    # Verify the task was called with correct arguments
    mock_celery_tasks['fetch_news'].delay.assert_called_once_with(None)  # No source specified

@pytest.mark.asyncio
async def test_trigger_sentiment_analysis(mock_celery_tasks):
    """Test triggering sentiment analysis for an article."""
    # Make request to the correct endpoint
    response = client.post("/api/v1/sentiment/analyze/1")
    
    # Verify response
    assert response.status_code == 202  # Accepted
    data = response.json()
    assert data["task_id"] == "test-task-id"
    assert data["status"] == "PENDING"
    
    # Verify the task was called with correct arguments
    mock_celery_tasks['analyze_sentiment'].delay.assert_called_once_with(1)

@pytest.mark.asyncio
async def test_trigger_trends_update(mock_celery_tasks):
    """Test triggering a trends update task."""
    # Make request to the correct endpoint
    response = client.post("/api/v1/trends/update")
    
    # Verify response
    assert response.status_code == 202  # Accepted
    data = response.json()
    assert data["task_id"] == "test-task-id"
    assert data["status"] == "PENDING"
    
    # Verify the task was called
    mock_celery_tasks['update_trends'].delay.assert_called_once()



@pytest.mark.asyncio
async def test_get_task_status_not_found():
    """Test getting the status of a non-existent task."""
    # Mock the AsyncResult to return a pending task
    mock_result = MockAsyncResult('non-existent-task')
    
    with patch('crypto_news_aggregator.api.AsyncResult', return_value=mock_result):
        # Make request
        response = client.get("/api/v1/tasks/non-existent-task")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "non-existent-task"
        assert data["status"] == "PENDING"

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
async def test_trigger_sentiment_analysis_invalid_article(mock_async_result):
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
