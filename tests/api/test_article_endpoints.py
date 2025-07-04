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
os.environ["API_KEYS"] = "test-api-key,another-test-key"
os.environ["MONGODB_URI"] = "mongodb://localhost:27017/test_db"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["NEWS_API_KEY"] = "test-api-key"
os.environ["SECRET_KEY"] = "test-secret-key"

# Import the FastAPI app after setting environment variables
from src.crypto_news_aggregator.main import app
from src.crypto_news_aggregator.db.mongodb_models import ArticleResponse, ArticleInDB, ArticleSource
from src.crypto_news_aggregator.services.article_service import article_service

# Create test client
client = TestClient(app)

# Test data
now = datetime.now(timezone.utc)

# Create a test article ID
test_article_id = "507f1f77bcf86cd799439011"

# Create test article data that matches the expected API response format
test_article_data = {
    "_id": ObjectId(test_article_id),
    "title": "Test Article",
    "url": "https://example.com/test-article",
    "source": {
        "id": "test-source-1",
        "name": "Test Source",
        "url": "https://example.com",
        "type": "test"
    },
    "published_at": now,
    "content": "This is a test article",
    "created_at": now,
    "updated_at": now,
    "author": "Test Author",
    "description": "Test description",
    "url_to_image": "https://example.com/test-image.jpg",
    "sentiment_score": 0.5,
    "keywords": ["test", "crypto", "blockchain"],
    "additional_data": {},
    "raw_data": {}
}

# Create an ArticleInDB instance from the test data
test_article = ArticleInDB(**test_article_data)

# Mock for the article service
@pytest.fixture
def mock_article_service():
    with patch('src.crypto_news_aggregator.api.v1.endpoints.articles.article_service') as mock_service:
        # Configure the mock to return our test article
        mock_service.get_article = AsyncMock(return_value=test_article)
        
        # For list_articles, return a tuple of (articles, total_count)
        mock_service.list_articles = AsyncMock(return_value=([test_article], 1))
        
        # For search_articles, same format as list_articles
        mock_service.search_articles = AsyncMock(return_value=([test_article], 1))
        
        # For the collection property used in some endpoints
        mock_collection = AsyncMock()
        mock_service._get_collection = AsyncMock(return_value=mock_collection)
        
        yield mock_service



# Common headers for requests
auth_headers = {"X-API-Key": "test-api-key"}  # This matches one of the keys in API_KEYS

class TestArticleEndpoints:
    """Test cases for article endpoints."""
    
    def test_list_articles(self, mock_article_service):
        """Test listing articles with filters."""
        # Make request to list articles
        response = client.get(
            "/api/v1/articles/",
            headers={"X-API-Key": "test-api-key"}
        )
        
        # Verify response
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        article = data[0]
        assert article["id"] == test_article_id  # Should be string ID in response
        assert article["title"] == test_article_data["title"]
        # The API should return the source as an object
        assert isinstance(article["source"], dict)
        assert article["source"]["name"] == test_article_data["source"]["name"]
        
        # Verify the X-Total-Count header is set
        assert "X-Total-Count" in response.headers
        assert response.headers["X-Total-Count"] == "1"

    def test_get_article(self, mock_article_service):
        """Test getting a single article by ID."""
        # Make request to get the article
        response = client.get(
            f"/api/v1/articles/{test_article_id}",
            headers={"X-API-Key": "test-api-key"}
        )
        
        # Verify response
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == test_article_id  # Should be string ID in response
        assert data["title"] == test_article_data["title"]
        # The API should return the source as an object
        assert isinstance(data["source"], dict)
        assert data["source"]["name"] == test_article_data["source"]["name"]
        
        # Test with invalid ID format
        response = client.get(
            "/api/v1/articles/invalid-id",
            headers={"X-API-Key": "test-api-key"}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        # Test non-existent article
        mock_article_service.get_article.return_value = None
        response = client.get(
            f"/api/v1/articles/{test_article_id}",
            headers={"X-API-Key": "test-api-key"}
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_search_articles(self, mock_article_service):
        """Test searching articles."""
        response = client.get(
            "/api/v1/articles/search?q=test",
            headers={"X-API-Key": "test-api-key"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert data[0]["id"] == test_article_id
        
        # Verify the X-Total-Count header is set
        assert "X-Total-Count" in response.headers
        assert response.headers["X-Total-Count"] == "1"

    def test_unauthenticated_access(self):
        """Test that unauthenticated access is handled correctly."""
        # Test list articles without API key
        response = client.get("/api/v1/articles/")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
        
        # Test get article without API key
        response = client.get(f"/api/v1/articles/{test_article_id}")
        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
        
        # Test get article with invalid API key
        response = client.get(
            f"/api/v1/articles/{test_article_id}",
            headers={"X-API-Key": "invalid-key"}
        )
        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
        response = client.get("/api/v1/health")
        assert response.status_code == 200  # Health check should be public
