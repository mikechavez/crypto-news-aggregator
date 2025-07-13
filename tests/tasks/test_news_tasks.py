"""Integration tests for news collection Celery tasks."""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta, timezone

from crypto_news_aggregator.tasks.news import fetch_news, analyze_sentiment, process_article
from crypto_news_aggregator.core.news_collector import NewsCollector

# Enable async test support
pytestmark = pytest.mark.asyncio

class TestNewsTasks:
    """Test suite for news-related Celery tasks."""
    
    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        """Setup common mocks for task tests."""
        self.mock_collector = MagicMock(spec=NewsCollector)
        self.mock_collector.collect_from_source = AsyncMock(return_value=1)
        self.mock_collector.collect_all_sources = AsyncMock(return_value=5)
        self.mock_collector.get_metrics.return_value = {
            'articles_processed': 5,
            'articles_skipped': 0,
            'api_errors': 0,
            'start_time': datetime.now(timezone.utc).isoformat()
        }
        
        # Patch the NewsCollector to return our mock
        self.news_collector_patch = patch('crypto_news_aggregator.tasks.news.NewsCollector', 
                                        return_value=self.mock_collector)
        self.news_collector_patch.start()
        
        yield
        
        # Cleanup
        self.news_collector_patch.stop()
    
    def test_fetch_news_single_source(self):
        """Test fetching news from a single source."""
        # Create a mock task request
        task = MagicMock()
        task.request.id = 'test-task-123'
        task.request.retries = 0
        task.max_retries = 3
        
        # Call the task
        result = fetch_news(task, source_name='test-source', days=1)
        
        # Verify the result
        assert result['status'] == 'success'
        assert result['source'] == 'test-source'
        assert result['articles_collected'] == 1
        assert 'duration_seconds' in result
        assert 'metrics' in result
        
        # Verify the collector was called correctly
        self.mock_collector.collect_from_source.assert_awaited_once_with('test-source', days=1)
    
    def test_fetch_news_all_sources(self):
        """Test fetching news from all sources."""
        # Create a mock task request
        task = MagicMock()
        task.request.id = 'test-task-456'
        task.request.retries = 0
        task.max_retries = 3
        
        # Call the task
        result = fetch_news(task, source_name=None, days=2)
        
        # Verify the result
        assert result['status'] == 'success'
        assert result['source'] == 'all'
        assert result['articles_collected'] == 5
        assert 'duration_seconds' in result
        assert 'metrics' in result
        
        # Verify the collector was called correctly
        self.mock_collector.collect_all_sources.assert_awaited_once()
    
    def test_fetch_news_retry_on_error(self):
        """Test that the task retries on errors."""
        # Setup mock to raise an exception
        self.mock_collector.collect_all_sources.side_effect = Exception("API Error")
        
        # Create a mock task request
        task = MagicMock()
        task.request.id = 'test-task-789'
        task.request.retries = 0
        task.max_retries = 3
        
        # Call the task - should raise retry
        with pytest.raises(Exception):
            fetch_news(task, source_name=None, days=1)
        
        # Verify retry was called
        task.retry.assert_called_once()
    
    def test_analyze_sentiment_task(self):
        """Test the analyze_sentiment task."""
        # Create a mock task request
        task = MagicMock()
        task.request.id = 'sentiment-task-123'
        task.request.retries = 0
        task.max_retries = 3
        
        # Call the task
        result = analyze_sentiment(task, article_id='test-article-123')
        
        # Verify the result
        assert result['status'] == 'success'
        assert result['article_id'] == 'test-article-123'
        assert 'sentiment_score' in result
        assert 'sentiment_label' in result
        assert 'confidence' in result
    
    def test_process_article_task(self):
        """Test the process_article task."""
        # Create test article data
        article_data = {
            'id': 'test-article-123',
            'title': 'Test Article',
            'content': 'This is a test article.',
            'url': 'https://example.com/test-article'
        }
        
        # Create a mock task request
        task = MagicMock()
        task.request.id = 'process-task-123'
        task.request.retries = 0
        task.max_retries = 2
        
        # Call the task
        result = process_article(task, article_data)
        
        # Verify the result
        assert result['status'] == 'success'
        assert result['article_id'] == 'test-article-123'
        assert result['title'] == 'Test Article'
