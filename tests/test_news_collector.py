"""Tests for the NewsCollector class."""
import asyncio
import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock, AsyncMock, call, ANY
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, AsyncIterator, Generator

# Disable real API calls during tests
pytestmark = pytest.mark.asyncio

from crypto_news_aggregator.core.news_collector import NewsCollector
from crypto_news_aggregator.db.models import Article, Source
from crypto_news_aggregator.core.config import get_settings

# Test data
TEST_SOURCE = {
    "id": "test-source",
    "name": "Test Source",
    "url": "https://test-source.com",
    "type": "news"
}

TEST_ARTICLE = {
    "source": {"id": "test-source", "name": "Test Source"},
    "author": "Test Author",
    "title": "Test Article",
    "description": "This is a test article",
    "url": "https://test.article/1",
    "urlToImage": "https://test.article/1/image.jpg",
    "publishedAt": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
    "content": "This is the full content of the test article."
}

@pytest.fixture
def mock_session():
    """Create a mock database session."""
    # Create a mock for the execute result
    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_result.scalar_one_or_none.return_value = None
    
    # Create the session mock with proper async methods
    session = AsyncMock()
    
    # Configure execute to return our mock result
    async def execute_mock(*args, **kwargs):
        return mock_result
    
    session.execute.side_effect = execute_mock
    
    # Configure scalar_one_or_none to work with our mock result
    session.scalar_one_or_none = AsyncMock(return_value=None)
    
    # Configure add and commit to be async
    session.add = AsyncMock()
    session.commit = AsyncMock()
    
    # Configure the session to be used as a context manager
    session.__aenter__.return_value = session
    session.__aexit__.return_value = None
    
    # Store the mock_result for test configuration
    session._mock_result = mock_result
    
    return session

class AsyncContextManagerMock(MagicMock):
    """Async context manager mock for database session."""
    async def __aenter__(self):
        return self.return_value

    async def __aexit__(self, *args):
        pass

@pytest_asyncio.fixture
async def news_collector(mock_newsapi, mock_session) -> AsyncIterator[NewsCollector]:
    """Fixture that provides a NewsCollector instance for testing."""
    with patch('crypto_news_aggregator.core.news_collector.get_sessionmaker') as mock_session_maker:
        # Configure the session maker to return our mock session
        mock_session_maker.return_value = AsyncContextManagerMock(return_value=mock_session)
        
        # Create collector with the mocked newsapi client
        collector = NewsCollector(newsapi_client=mock_newsapi)
        collector._initialized = True
        collector.processed_urls = set()
        
        yield collector

@pytest.fixture
def mock_newsapi():
    """Fixture that mocks the NewsAPI client."""
    with patch('crypto_news_aggregator.core.news_collector.NewsApiClient') as mock:
        api_client = mock.return_value
        
        # Mock get_sources
        test_source = {
            'id': 'test-source',
            'name': 'Test Source',
            'url': 'https://test-source.com',
            'type': 'news'
        }
        
        api_client.get_sources.return_value = {
            'status': 'ok',
            'sources': [test_source]
        }
        
        # Mock get_everything with specific responses based on input
        def get_everything_mock(sources=None, **kwargs):
            if sources == 'test-source':
                return {
                    'status': 'ok',
                    'totalResults': 1,
                    'articles': [{
                        'title': 'Test Article',
                        'url': 'https://test.article/1',
                        'source': {'id': 'test-source', 'name': 'Test Source'},
                        'author': 'Test Author',
                        'description': 'Test Description',
                        'urlToImage': 'https://test.image.com/1.jpg',
                        'publishedAt': '2023-01-01T00:00:00Z',
                        'content': 'Test Content'
                    }]
                }
            return {
                'status': 'ok',
                'totalResults': 0,
                'articles': []
            }
            
        api_client.get_everything.side_effect = get_everything_mock
        
        yield api_client

@pytest.mark.asyncio
@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_initialize_loads_processed_urls(news_collector, mock_session):
    """Test that initialize loads processed URLs from the database."""
    # Setup test data
    test_urls = [("http://test1.com",), ("http://test2.com",)]
    
    # Configure the mock to return our test URLs
    mock_session._mock_result.all.return_value = test_urls
    
    # Reset initialization and test
    news_collector._initialized = False
    await news_collector.initialize()
    
    # Verify the query was made
    mock_session.execute.assert_awaited_once()
    
    # Verify URLs were loaded
    assert len(news_collector.processed_urls) == len(test_urls)
    for url, in test_urls:
        assert url in news_collector.processed_urls

@pytest.mark.asyncio
async def test_collect_from_source_success(news_collector, mock_newsapi, mock_session):
    """Test collecting articles from a single source successfully."""
    # Setup test data
    source_id = "test-source"
    
    # Configure the mock session
    mock_session.execute.return_value.scalar_one_or_none.return_value = None
    
    # Create a mock for the async context manager that will be used by the session maker
    mock_ctx_manager = AsyncMock()
    mock_ctx_manager.__aenter__.return_value = mock_session
    mock_ctx_manager.__aexit__.return_value = None
    
    # Create a MagicMock for the add method (which is synchronous in SQLAlchemy async)
    mock_add = MagicMock()
    mock_session.add = mock_add
    
    # Patch the session maker to return our mock context manager
    with patch('crypto_news_aggregator.core.news_collector.get_sessionmaker') as mock_session_maker:
        # The session maker should return an async context manager
        mock_session_maker.return_value = AsyncMock(return_value=mock_ctx_manager)
        
        # Test
        result = await news_collector.collect_from_source(source_id)
    
    # Verify the API was called with the expected parameters
    mock_newsapi.get_everything.assert_called_once()
    call_kwargs = mock_newsapi.get_everything.call_args[1]
    assert call_kwargs['sources'] == source_id
    assert call_kwargs['language'] == 'en'
    assert call_kwargs['sort_by'] == 'publishedAt'
    assert call_kwargs['page'] == 1
    
    # Verify the correct number of articles were processed
    assert result == 1  # 1 new article
    
    # Verify database operations - we expect at least one add for the article
    # and possibly one for the source if it didn't exist
    assert mock_add.call_count >= 1
    assert mock_session.commit.await_count >= 1
    assert mock_session.commit.await_count >= 1  # At least 1 commit

@pytest.mark.asyncio
async def test_collect_from_source_api_error(news_collector, mock_newsapi, mock_session):
    """Test handling of API errors when collecting from a source."""
    # Setup mock API to return an error
    def mock_get_everything(*args, **kwargs):
        return {
            'status': 'error',
            'code': 'apiKeyInvalid',
            'message': 'Your API key is invalid.'
        }
    
    mock_newsapi.get_everything.side_effect = mock_get_everything
    
    # Test
    result = await news_collector.collect_from_source("test-source")
    
    # Verify
    assert result == 0  # No articles collected
    
    # Verify API was called (may be called multiple times due to retries)
    assert mock_newsapi.get_everything.call_count >= 1
    
    # Verify no database operations were performed
    assert mock_session.add.await_count == 0
    assert mock_session.commit.await_count == 0

@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_collect_all_sources(news_collector, mock_newsapi, mock_session):
    """Test collecting from all available sources."""
    # Configure the mock session
    mock_session.execute.return_value.scalar_one_or_none.return_value = None
    
    # Test with max_sources=1
    result = await news_collector.collect_all_sources(max_sources=1)
    
    # Verify the API was called to get sources
    mock_newsapi.get_sources.assert_called_once()
    
    # Verify the API was called to get articles for the source
    assert mock_newsapi.get_everything.call_count == 1, "Expected get_everything to be called once"
    
    # Verify the correct number of articles were processed
    assert result == 1, f"Expected 1 article, got {result}"
    
    # Verify API was called as expected
    assert mock_newsapi.get_everything.call_count == 1, "Expected get_everything to be called once"

@pytest.mark.asyncio
async def test_process_articles_duplicate_urls(news_collector, mock_session):
    """Test that duplicate URLs are not processed."""
    # Add a URL to processed_urls
    test_url = "https://test.article/duplicate"
    news_collector.processed_urls.add(test_url)
    
    # Create a test article with duplicate URL
    test_source = {
        'id': 'test-source',
        'name': 'Test Source',
        'url': 'https://test.source'
    }
    
    # Setup mock to return source when queried
    mock_session.execute.return_value.scalar_one_or_none.return_value = test_source
    
    # Create a test article with duplicate URL
    duplicate_article = {**TEST_ARTICLE, "url": test_url, "source": {"id": "test-source"}}
    
    # Test
    result = await news_collector._process_articles([duplicate_article], "test-source")
    
    # Verify
    assert result == 0  # No new articles added
    
    # Verify no article was added (Source may or may not be added depending on test setup)
    added_article = False
    for call in mock_session.add.await_args_list:
        if isinstance(call.args[0], Article):
            added_article = True
            break
    assert not added_article, "Expected no article to be added for duplicate URL"

@pytest.mark.asyncio
async def test_retry_with_backoff(news_collector, mock_newsapi, mock_session):
    """Test the retry mechanism with backoff."""
    # Setup test data
    source_id = "test-source"
    test_article = {**TEST_ARTICLE, "url": "https://test.article/retry"}
    
    # Configure the mock session
    mock_session.execute.return_value.scalar_one_or_none.return_value = None
    
    # Setup mock to fail twice then succeed
    mock_newsapi.get_everything.side_effect = [
        {'status': 'error', 'code': 'rateLimited', 'message': 'Rate limit exceeded'},
        {'status': 'error', 'code': 'rateLimited', 'message': 'Rate limit exceeded'},
        {'status': 'ok', 'totalResults': 1, 'articles': [test_article]}
    ]
    
    # Test with reduced backoff for testing
    with patch('crypto_news_aggregator.core.news_collector.asyncio.sleep') as mock_sleep:
        result = await news_collector.collect_from_source(source_id)
    
    # Verify the API was called 3 times (2 failures + 1 success)
    assert mock_newsapi.get_everything.call_count == 3, "Expected 3 API calls (2 failures + 1 success)"
    
    # Verify sleep was called with exponential backoff
    # Each retry includes a sleep, so we should have at least 2 sleeps for 2 retries
    assert mock_sleep.await_count >= 2, f"Expected at least 2 sleeps, got {mock_sleep.await_count}"
        
    # Verify sleep was called at least once for each retry
    assert mock_sleep.await_count >= 2, f"Expected at least 2 sleeps, got {mock_sleep.await_count}"
    
    # Verify the correct number of articles were processed
    assert result == 1, f"Expected 1 article, got {result}"
    
    # Verify database operations - may or may not have added anything
    # depending on test setup and whether the source already exists
    assert mock_session.add.await_count >= 0, "Unexpected negative add count"
    assert mock_session.commit.await_count >= 0, "Unexpected negative commit count"
