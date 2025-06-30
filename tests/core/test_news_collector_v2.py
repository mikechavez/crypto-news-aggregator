"""Tests for the NewsCollector class with MongoDB integration."""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

from newsapi import NewsApiClient

from crypto_news_aggregator.core.news_collector import NewsCollector
from crypto_news_aggregator.core.config import get_settings

# Enable async test support
pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_article_data() -> Dict[str, Any]:
    """Mock article data for testing."""
    return {
        "source": {"id": "test-source", "name": "Test Source"},
        "author": "Test Author",
        "title": "Test Article",
        "description": "Test description",
        "url": "https://example.com/test-article",
        "urlToImage": "https://example.com/image.jpg",
        "publishedAt": "2025-01-01T12:00:00Z",
        "content": "Test content"
    }

@pytest.fixture
def mock_newsapi_response(mock_article_data: Dict[str, Any]) -> Dict[str, Any]:
    """Mock response from NewsAPI."""
    return {
        "status": "ok",
        "totalResults": 1,
        "articles": [mock_article_data]
    }

@pytest.fixture
def mock_article_service():
    """Mock ArticleService."""
    mock_service = AsyncMock()
    mock_service.create_article.return_value = True
    return mock_service

@pytest.fixture
def mock_newsapi(mock_newsapi_response: Dict[str, Any], mock_article_service):
    """Mock NewsAPI client and dependencies."""
    with patch('crypto_news_aggregator.core.news_collector.NewsApiClient') as mock_newsapi_cls:
        # Mock NewsApiClient
        mock_client = MagicMock()
        mock_client.get_everything.return_value = mock_newsapi_response
        mock_client.get_sources.return_value = {
            "status": "ok",
            "sources": [{"id": "test-source", "name": "Test Source"}]
        }
        mock_newsapi_cls.return_value = mock_client
        
        # Create NewsCollector with mocked dependencies
        collector = NewsCollector(
            newsapi_client=mock_client,
            article_service=mock_article_service
        )
        
        yield collector, mock_client, mock_article_service

class TestNewsCollector:
    """Test suite for the NewsCollector class."""
    
    async def test_initialization(self, mock_article_service):
        """Test that the NewsCollector initializes correctly."""
        # Create a mock NewsAPI client
        mock_client = MagicMock()
        
        # Initialize NewsCollector with mocked dependencies
        collector = NewsCollector(
            newsapi_client=mock_client,
            article_service=mock_article_service
        )
        
        assert collector is not None
        metrics = collector.get_metrics()
        assert 'articles_processed' in metrics
        assert 'articles_skipped' in metrics
        assert 'api_errors' in metrics
        assert 'start_time' in metrics
    
    async def test_collect_from_source(self, mock_newsapi, mock_article_data):
        """Test collecting articles from a single source."""
        collector, mock_client, mock_service = mock_newsapi
        
        # Configure the mock to return our test data
        mock_client.get_everything.return_value = {
            "status": "ok",
            "totalResults": 1,
            "articles": [mock_article_data]
        }
        
        # Configure the article service mock
        mock_service.create_article.return_value = True
        
        # Test the collection
        count = await collector.collect_from_source("test-source", days=1)
        
        # Verify the article was processed
        assert count == 1
        assert collector.get_metrics()['articles_processed'] == 1
        
        # Verify the article service was called with the expected data
        mock_service.create_article.assert_awaited_once()
        called_with = mock_service.create_article.await_args[0][0]
        assert called_with['title'] == mock_article_data['title']
        assert called_with['url'] == mock_article_data['url']
    
    async def test_duplicate_article_handling(self, mock_newsapi, mock_article_data):
        """Test that duplicate articles are handled correctly."""
        collector, mock_client, mock_service = mock_newsapi
        
        # Configure the mock to return our test data
        mock_client.get_everything.return_value = {
            "status": "ok",
            "totalResults": 1,
            "articles": [mock_article_data]
        }
        
        # First call returns True (new article), second returns False (duplicate)
        mock_service.create_article.side_effect = [True, False]
        
        # First collection - should process the article
        count1 = await collector.collect_from_source("test-source", days=1)
        assert count1 == 1
        assert collector.get_metrics()['articles_processed'] == 1
        
        # Second collection with same data - should skip as duplicate
        count2 = await collector.collect_from_source("test-source", days=1)
        assert count2 == 0
        assert collector.get_metrics()['articles_skipped'] == 1
    
    async def test_error_handling(self, mock_newsapi, caplog):
        """Test error handling during news collection."""
        collector, mock_client, _ = mock_newsapi
        
        # Configure the mock to raise an exception
        mock_client.get_everything.side_effect = Exception("API Error")
        
        # Test error handling
        count = await collector.collect_from_source("test-source", days=1)
        
        # Should return 0 articles on error
        assert count == 0
        assert collector.get_metrics()['api_errors'] > 0
        
        # Verify error was logged
        assert "Error collecting from source test-source" in caplog.text
    
    async def test_collect_all_sources(self, mock_newsapi):
        """Test collecting articles from all sources."""
        collector, mock_client, mock_service = mock_newsapi
        
        # Configure the article service mock
        mock_service.create_article.return_value = True
        
        # Test collecting from all sources (limited to 1 for testing)
        count = await collector.collect_all_sources(max_sources=1)
        
        # Should process one article from one source
        assert count == 1
        assert collector.get_metrics()['articles_processed'] == 1
    
async def test_rate_limiting(self, mock_newsapi):
        """Test that rate limiting is respected."""
        collector, _, _ = mock_newsapi
        
        with patch('time.time', return_value=0), \
             patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            
            # First call - no delay needed
            await collector._respect_rate_limit()
            mock_sleep.assert_not_called()
            
            # Second call immediately after - should trigger rate limiting
            await collector._respect_rate_limit()
            mock_sleep.assert_called_once()
            assert mock_sleep.call_args[0][0] > 0  # Should sleep for some duration
