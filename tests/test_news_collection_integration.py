"""
Integration tests for the news collection functionality.
"""
import os
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, Mock, create_autospec, ANY
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple

from newsapi import NewsApiClient

from crypto_news_aggregator.core.news_collector import NewsCollector
from crypto_news_aggregator.db.models import Article, Source
from crypto_news_aggregator.core.config import get_settings


# Create a mock ArticleService class
class MockArticleService:
    async def create_or_update_article(self, article_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        return True, None
    
    async def get_article_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        return None
        
    async def create_article(self, article_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        return True, "test-article-id"

@pytest.fixture
def mock_newsapi():
    """Create a mock NewsAPI client."""
    with patch('crypto_news_aggregator.core.news_collector.NewsApiClient') as mock_newsapi_class:
        mock_newsapi = MagicMock(spec=NewsApiClient)
        mock_newsapi_class.return_value = mock_newsapi
        
        # Mock the get_sources method
        mock_newsapi.get_sources.return_value = {
            'status': 'ok',
            'sources': [
                {'id': 'test-source', 'name': 'Test Source', 'url': 'https://test-source.com'}
            ]
        }
        
        # Mock the get_everything method
        mock_newsapi.get_everything.return_value = {
            'status': 'ok',
            'totalResults': 1,
            'articles': [{
                'title': 'Test Article',
                'description': 'Test Description',
                'url': 'https://example.com/test-article',
                'publishedAt': '2023-01-01T12:00:00Z',
                'source': {'id': 'test-source', 'name': 'Test Source'},
                'content': 'Test content',
                'author': 'Test Author',
                'urlToImage': 'https://example.com/test-image.jpg'
            }]
        }
        
        yield mock_newsapi

# Test data
TEST_ARTICLE = {
    'title': 'Test Article',
    'description': 'Test Description',
    'url': 'https://example.com/test-article',
    'publishedAt': '2023-01-01T12:00:00Z',
    'source': {'id': 'test-source', 'name': 'Test Source'},
    'content': 'Test content',
    'author': 'Test Author',
    'urlToImage': 'https://example.com/test-image.jpg'
}

@pytest.fixture
def mock_newsapi():
    """Create a mock NewsAPI client."""
    with patch('crypto_news_aggregator.core.news_collector.NewsApiClient') as mock_newsapi_class:
        mock_newsapi = MagicMock()
        mock_newsapi_class.return_value = mock_newsapi
        
        # Mock the get_sources method
        mock_newsapi.get_sources.return_value = {
            'status': 'ok',
            'sources': [
                {'id': 'test-source', 'name': 'Test Source', 'url': 'https://test-source.com'}
            ]
        }
        
        # Mock the get_everything method
        mock_newsapi.get_everything.return_value = {
            'status': 'ok',
            'totalResults': 1,
            'articles': [TEST_ARTICLE]
        }
        
        yield mock_newsapi

@pytest.fixture
def mock_article_service():
    """Create a mock ArticleService."""
    # Create a mock ArticleService instance with the required methods
    mock_service = MockArticleService()
    
    # Patch the article service instance in the article_service module
    with patch('crypto_news_aggregator.services.article_service.article_service', mock_service):
        yield mock_service

@pytest.mark.asyncio
async def test_news_collector_initialization(mock_newsapi, mock_article_service):
    """Test that the NewsCollector initializes correctly."""
    # Initialize collector with mocked dependencies
    mock_article_service = MockArticleService()
    collector = NewsCollector(
        newsapi_client=mock_newsapi,
        article_service=mock_article_service
    )
    
    # Verify the collector was initialized with the provided clients
    assert collector.newsapi is mock_newsapi
    assert collector.article_service is mock_article_service

@pytest.mark.asyncio
async def test_collect_from_source(mock_newsapi, mock_article_service):
    """Test collecting articles from a source."""
    # Initialize collector with mocked dependencies
    collector = NewsCollector(
        newsapi_client=mock_newsapi,
        article_service=mock_article_service
    )
    
    # Create a mock for the create_article method
    with patch.object(mock_article_service, 'create_article', 
                     return_value=(True, "test-article-id")) as mock_create_article:
        
        # Test collecting from a source
        source_id = 'test-source'
        new_articles = await collector.collect_from_source(source_id)
        
        # Verify the API was called the correct number of times (5 pages)
        assert mock_newsapi.get_everything.call_count == 5
        
        # Get all calls to get_everything
        calls = mock_newsapi.get_everything.call_args_list
        
        # Verify each call has the expected arguments
        for i, call in enumerate(calls, 1):
            call_args = call[1]  # Get the keyword arguments
            assert call_args['sources'] == source_id
            assert call_args['language'] == 'en'
            assert call_args['sort_by'] == 'publishedAt'
            assert call_args['page_size'] == 50
            assert call_args['page'] == i
            assert 'crypto OR cryptocurrency OR bitcoin OR ethereum OR blockchain' in call_args['q']
        
        # Verify the article service was called to save the article
        assert mock_create_article.called
        
        # Get the article data that was passed to create_article
        article_data = mock_create_article.call_args[0][0]
        
        # Debug output to see the actual structure of article_data
        print("\nArticle data structure:", article_data)
        
        # Verify the article data is as expected
        assert article_data['title'] == 'Test Article'
        assert article_data['url'] == 'https://example.com/test-article'
        assert article_data['description'] == 'Test Description'
        # The source is stored in the 'source_id' field
        assert article_data['source_id'] == 'test-source'
        
        # Verify the correct number of new articles were processed
        assert new_articles == 5  # We expect 5 pages with 1 article each from our mock
