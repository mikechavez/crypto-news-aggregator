import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone

from crypto_news_aggregator.main import app
from crypto_news_aggregator.db.models import Article, Source

client = TestClient(app)

@pytest.fixture
def mock_db_session():
    with patch('crypto_news_aggregator.api.get_db') as mock_db:
        mock_session = AsyncMock()
        mock_db.return_value = mock_session
        yield mock_session

@pytest.mark.asyncio
async def test_get_articles(mock_db_session):
    """Test getting a list of articles."""
    # Mock database response
    mock_article = Article(
        id=1,
        title="Test Article",
        source_id="test-source",
        url="https://example.com/test-article",
        published_at=datetime.now(timezone.utc),
        content="Test content"
    )
    mock_source = Source(id="test-source", name="Test Source")
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_article]
    mock_db_session.execute.return_value = mock_result
    
    # Make request
    response = client.get("/api/articles/")
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Test Article"
    assert data[0]["source"]["name"] == "Test Source"

@pytest.mark.asyncio
async def test_get_article_not_found(mock_db_session):
    """Test getting a non-existent article."""
    # Mock database to return None
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result
    
    # Make request
    response = client.get("/api/articles/999")
    
    # Verify 404 response
    assert response.status_code == 404
    assert response.json()["detail"] == "Article not found"

@pytest.mark.asyncio
async def test_create_article(mock_db_session):
    """Test creating a new article."""
    # Setup test data
    article_data = {
        "title": "New Article",
        "source_id": "test-source",
        "url": "https://example.com/new-article",
        "content": "Test content"
    }
    
    # Mock database response
    mock_source = Source(id="test-source", name="Test Source")
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_source
    mock_db_session.execute.return_value = mock_result
    
    # Make request
    response = client.post("/api/articles/", json=article_data)
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "New Article"
    assert data["source"]["id"] == "test-source"
    
    # Verify database was called
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()

@pytest.mark.asyncio
async def test_create_article_invalid_source(mock_db_session):
    """Test creating an article with an invalid source."""
    # Setup test data with invalid source
    article_data = {
        "title": "New Article",
        "source_id": "invalid-source",
        "url": "https://example.com/new-article",
        "content": "Test content"
    }
    
    # Mock database to return None for source
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result
    
    # Make request
    response = client.post("/api/articles/", json=article_data)
    
    # Verify 400 response
    assert response.status_code == 400
    assert "Source not found" in response.json()["detail"]

@pytest.mark.asyncio
async def test_get_article_sentiment(mock_db_session):
    """Test getting sentiment for an article."""
    # Create test article with sentiment
    mock_article = Article(
        id=1,
        title="Test Article",
        source_id="test-source",
        url="https://example.com/test-article",
        published_at=datetime.now(timezone.utc),
        content="This is a positive test article.",
        sentiment_score=0.8,
        sentiment_subjectivity=0.6
    )
    
    # Mock database response
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_article
    mock_db_session.execute.return_value = mock_result
    
    # Make request
    response = client.get("/api/articles/1/sentiment")
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["article_id"] == 1
    assert data["sentiment"]["score"] == 0.8
    assert data["sentiment"]["label"] == "Positive"
