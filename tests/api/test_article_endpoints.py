"""
Integration tests for article API endpoints.
"""
import logging
import os
import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from fastapi.testclient import TestClient
from fastapi import status
from unittest.mock import patch, MagicMock, AsyncMock
from bson import ObjectId
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Set test environment variables before importing the app
os.environ["API_KEYS"] = "testapikey123"  # Must match the test API key in conftest.py
os.environ["MONGODB_URI"] = "mongodb://localhost:27017/test_db"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["NEWS_API_KEY"] = "test-api-key"
os.environ["SECRET_KEY"] = "test-secret-key"

# Import the FastAPI app after setting environment variables
from src.crypto_news_aggregator.main import app
from src.crypto_news_aggregator.models.article import ArticleInDB
from src.crypto_news_aggregator.services.article_service import article_service
from src.crypto_news_aggregator.db.mongodb import PyObjectId

# Client fixture will be provided by conftest.py

# Test data
now = datetime.now(timezone.utc)

# Create a test article ID
test_article_id = "507f1f77bcf86cd799439011"

# Create test article data that matches the ArticleInDB model
test_article_data = {
    "id": PyObjectId(test_article_id),
    "title": "Test Article",
    "source_id": "test-source-123",
    "source": "rss",
    "text": "This is the full content of the test article.",
    "author": ArticleAuthor(
        id="author-123",
        name="Test Author",
        username="testauthor"
    ),
    "url": "https://example.com/test-article",
    "lang": "en",
    "metrics": ArticleMetrics(
        views=100,
        likes=10,
        replies=5,
        retweets=2,
        quotes=1
    ),
    "keywords": ["test", "article"],
    "relevance_score": 0.8,
    "sentiment_score": 0.5,
    "sentiment_label": "neutral",
    "raw_data": {"original_source": "test"},
    "published_at": now,
    "created_at": now,
    "updated_at": now,
    "description": "A test article description",
    "image_url": "https://example.com/image.jpg",
    "tags": ["test"],
    "entities": [],
}

# Create an ArticleInDB instance from the test data
test_article = ArticleInDB(**test_article_data)

# Mock for the article service
@pytest.fixture
def mock_article_service():
    with patch('src.crypto_news_aggregator.services.article_service.article_service') as mock_service:
        # Configure the mock to return our test article
        mock_service.get_article = AsyncMock(return_value=test_article)
        
        # For list_articles, return a tuple of (articles, total_count)
        mock_service.list_articles = AsyncMock(return_value=([test_article], 1))
        
        # For search_articles, same format as list_articles
        mock_service.search_articles = AsyncMock(return_value=([test_article], 1))
        
        # For the collection property used in some endpoints
        mock_collection = AsyncMock()
        mock_service._get_collection = AsyncMock(return_value=mock_collection)
        
        # Mock the current user dependency
        from fastapi import Depends
        from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
        from src.crypto_news_aggregator.core.security import get_current_user
        
        # Create a mock user with required fields
        from src.crypto_news_aggregator.models.user import UserInDB
        from bson import ObjectId
        
        mock_user = UserInDB(
            id=str(ObjectId()),
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
            is_active=True,
            is_superuser=False
        )
        
        # Override the get_current_user dependency
        def mock_get_current_user():
            return mock_user
            
        app.dependency_overrides[get_current_user] = mock_get_current_user
        
        try:
            yield mock_service
        finally:
            # Clean up the override
            app.dependency_overrides.pop(get_current_user, None)



# Common headers for requests
auth_headers = {"X-API-Key": "test-api-key"}  # This matches one of the keys in API_KEYS

class TestArticleEndpoints:
    """Test cases for article endpoints."""
    
    def test_list_articles(self, mock_article_service, client):
        """Test listing articles with filters."""
        # Make request to list articles
        response = client.get("/api/v1/articles/")
        
        # Verify response
        assert response.status_code == status.HTTP_200_OK, f"Unexpected status code: {response.status_code}. Response: {response.text}"
        
        # Parse response data
        data = response.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        
        # The mock returns one article, so we should have at least one
        assert len(data) > 0, "No articles returned in the response"
        
        # Verify article data
        article = data[0]
        assert article["id"] == test_article_id, f"Unexpected article ID: {article.get('id')}"
        assert article["title"] == test_article.title
        assert article["source_name"] == test_article.source_name
        
        # Verify the X-Total-Count header is set
        assert "X-Total-Count" in response.headers
        assert response.headers["X-Total-Count"] == "1"

    def test_get_article(self, mock_article_service, client):
        """Test getting a single article by ID."""
        # Make request to get the article
        response = client.get(f"/api/v1/articles/{test_article_id}")

        # Verify response
        assert response.status_code == status.HTTP_200_OK, f"Unexpected status code: {response.status_code}. Response: {response.text}"
        data = response.json()
        assert str(data["id"]) == test_article_id  # Should be string ID in response
        assert data["title"] == test_article.title
        assert data["source_name"] == test_article.source_name
        
        # Test with invalid ID format
        response = client.get("/api/v1/articles/invalid-id")
        assert response.status_code == status.HTTP_400_BAD_REQUEST, "Expected 400 for invalid ID format"
        
        # Test non-existent article
        mock_article_service.get_article.return_value = None
        response = client.get(f"/api/v1/articles/{test_article_id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND, "Expected 404 for non-existent article"

    def test_search_articles(self, mock_article_service, client):
        """Test searching articles."""
        response = client.get("/api/v1/articles/search/?q=test")

        assert response.status_code == status.HTTP_200_OK, f"Unexpected status code: {response.status_code}. Response: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0, "No articles returned in search results"
        assert str(data[0]["id"]) == test_article_id
        
        # Verify the X-Total-Count header is set
        assert "X-Total-Count" in response.headers
        assert response.headers["X-Total-Count"] == "1"

    def test_unauthenticated_access(self, client):
        """Test that unauthenticated access is handled correctly."""
        # Save original headers
        original_headers = client.headers.copy()
        
        try:
            # Remove API key for unauthenticated test
            if "X-API-Key" in client.headers:
                del client.headers["X-API-Key"]
            
            # Test list articles without API key
            response = client.get("/api/v1/articles/")
            assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
            
            # Test get article without API key
            response = client.get(f"/api/v1/articles/{test_article_id}")
            assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
            
            # Test get article with invalid API key
            client.headers.update({"X-API-Key": "invalid-key"})
            response = client.get(f"/api/v1/articles/{test_article_id}")
            assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
            
        finally:
            # Restore original headers
            client.headers = original_headers
        response = client.get("/api/v1/health")
        assert response.status_code == 200  # Health check should be public
