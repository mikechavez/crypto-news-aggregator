"""Integration tests for the CoinTelegraph news source."""
import asyncio
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any

import httpx
import pytest
import pytest_asyncio
from pytest_httpx import HTTPXMock

from crypto_news_aggregator.core.news_sources.cointelegraph import CoinTelegraphSource

# Sample test data directory
TEST_DATA_DIR = Path(__file__).parent.parent / "test_data" / "cointelegraph"

# Sample article data
SAMPLE_ARTICLE = {
    "id": 12345,
    "title": "Test Article",
    "lead": "This is a test article description.",
    "url": "/test-article",
    "cover_image": "https://example.com/image.jpg",
    "published_at": 1672531200,  # 2023-01-01T00:00:00Z
    "author": {
        "name": "Test Author"
    },
    "category": {
        "name": "Bitcoin"
    },
    "tags": [
        {"name": "bitcoin"},
        {"name": "crypto"}
    ],
    "is_opinion": False,
    "language": "en"
}

@pytest_asyncio.fixture
async def cointelegraph_source():
    """Fixture that provides a CoinTelegraph source instance with a fresh client."""
    source = CoinTelegraphSource()
    # Create a new client for testing
    source.client = httpx.AsyncClient(timeout=30.0)
    try:
        yield source
    finally:
        await source.client.aclose()

@pytest.fixture
def sample_article():
    """Fixture that provides a sample article."""
    return SAMPLE_ARTICLE.copy()

@pytest.fixture
def mock_article_response(sample_article):
    """Fixture that provides a mock API response with articles."""
    return {
        "data": [sample_article],
        "pagination": {
            "current_page": 1,
            "per_page": 1,
            "total_pages": 1,
            "total_items": 1,
            "next_url": None
        }
    }

@pytest.mark.asyncio
async def test_fetch_articles_success(
    cointelegraph_source: CoinTelegraphSource,
    httpx_mock: HTTPXMock,
    mock_article_response: dict,
    sample_article: dict
):
    """Test successful article fetching from CoinTelegraph."""
    # Configure the mock to return our test data
    httpx_mock.add_response(
        method="GET",
        url=(
            "https://api.cointelegraph.com/v1/news"
            "?limit=1&sort=published_at&order=desc"
        ),
        json=mock_article_response
    )
    
    # Fetch articles with a limit of 1
    articles = []
    async for article in cointelegraph_source.fetch_articles(limit=1):
        articles.append(article)
    
    # Verify results
    assert len(articles) == 1
    article = articles[0]
    assert article["title"] == sample_article["title"]
    # Check that HTML tags have been stripped
    assert "<p>" not in article["description"]
    assert "<b>" not in article["description"]
    assert "</b>" not in article["description"]
    assert "</p>" not in article["description"]
    assert article["url"] == "https://cointelegraph.com/test-article"
    assert article["image_url"] == sample_article["cover_image"]
    assert article["author"] == sample_article["author"]["name"]
    assert "bitcoin" in article["cryptocurrencies"]  # From categories
    assert "crypto" in [t.lower() for t in article["tags"]]  # From tags

@pytest.mark.asyncio
async def test_fetch_articles_rate_limit(
    cointelegraph_source: CoinTelegraphSource,
    httpx_mock: HTTPXMock
):
    """Test rate limit handling."""
    # First request: rate limited
    httpx_mock.add_response(
        status_code=429,
        headers={"Retry-After": "1"},
        json={"error": "Rate limit exceeded"}
    )
    
    # Second request: success
    httpx_mock.add_response(
        json={"data": [], "pagination": {"total_items": 0}}
    )
    
    # This should not raise an exception
    articles = []
    async for article in cointelegraph_source.fetch_articles(limit=1):
        articles.append(article)
    
    assert len(articles) == 0

@pytest.mark.asyncio
async def test_fetch_articles_retry_on_error(
    cointelegraph_source: CoinTelegraphSource,
    httpx_mock: HTTPXMock
):
    """Test retry behavior on server errors."""
    # First request: server error
    httpx_mock.add_response(status_code=500)
    
    # Second request: success
    httpx_mock.add_response(
        json={"data": [], "pagination": {"total_items": 0}}
    )
    
    # This should retry on error
    articles = []
    async for article in cointelegraph_source.fetch_articles(limit=1, max_retries=1):
        articles.append(article)
    
    assert len(articles) == 0

@pytest.mark.asyncio
async def test_format_article(cointelegraph_source: CoinTelegraphSource, sample_article: dict):
    """Test article formatting."""
    formatted = cointelegraph_source.format_article(sample_article)
    
    assert formatted["title"] == sample_article["title"]
    assert formatted["description"] == sample_article["lead"]
    assert formatted["url"] == f"https://cointelegraph.com{sample_article['url']}"
    assert formatted["image_url"] == sample_article["cover_image"]
    assert formatted["author"] == sample_article["author"]["name"]
    assert formatted["categories"] == [sample_article["category"]["name"]]
    assert set(t.lower() for t in formatted["tags"]) == {"bitcoin", "crypto"}
    assert "bitcoin" in formatted["cryptocurrencies"]
    assert formatted["published_at"] is not None

@pytest.mark.asyncio
async def test_with_statement():
    """Test context manager behavior."""
    async with CoinTelegraphSource() as source:
        assert source.client is not None
        assert not source.client.is_closed
    
    # Client should be closed after context manager exits
    assert source.client.is_closed

@pytest.mark.asyncio
async def test_empty_response(
    cointelegraph_source: CoinTelegraphSource,
    httpx_mock: HTTPXMock
):
    """Test handling of empty API responses."""
    httpx_mock.add_response(
        json={"data": [], "pagination": {"total_items": 0}}
    )
    
    articles = []
    async for article in cointelegraph_source.fetch_articles(limit=1):
        articles.append(article)
    
    assert len(articles) == 0
