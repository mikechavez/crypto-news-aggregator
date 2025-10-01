"""Tests for the CoinDesk news source."""

import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone, timedelta

from crypto_news_aggregator.core.news_sources.coindesk import CoinDeskSource


@pytest.fixture
def coindesk_source():
    """Create a CoinDesk source instance for testing."""
    return CoinDeskSource(api_key="test-api-key")


@pytest.fixture
def mock_article():
    """Create a mock CoinDesk article."""
    return {
        "id": "test-article-123",
        "title": "Test Article",
        "content": "This is a test article about cryptocurrency.",
        "url": "/article/test-article-123",
        "published_at": "2023-01-01T12:00:00Z",
        "author": {"name": "Test Author"},
        "categories": [{"name": "Bitcoin"}],
        "tags": [{"slug": "bitcoin"}],
        "image": {"original_url": "https://example.com/image.jpg"},
    }


@pytest.mark.asyncio
async def test_fetch_articles_success(httpx_mock, coindesk_source, mock_article):
    """Test successful article fetching from CoinDesk."""
    # Mock the API response
    mock_response = {
        "data": [mock_article],
        "meta": {"count": 1, "page": 1, "pages": 1},
    }

    # Mock the HTTP request
    httpx_mock.add_response(
        url=f"{coindesk_source.api_url}?page=1&per_page=20&sort=-published_at&include_aggregations=false&api_key=test-api-key",
        json=mock_response,
    )

    # Test the fetch_articles method
    articles = []
    async with coindesk_source as source:
        async for article in source.fetch_articles(limit=20):
            articles.append(article)

    # Verify the results
    assert len(articles) == 1
    article = articles[0]
    assert article["title"] == "Test Article"
    assert article["source"] == "coindesk"
    assert article["url"].startswith("https://www.coindesk.com/")
    assert article["published_at"] == datetime(2023, 1, 1, 12, 0, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_fetch_articles_rate_limit(httpx_mock, coindesk_source):
    """Test rate limit handling."""
    # Mock a rate limit response
    httpx_mock.add_response(status_code=429, headers={"Retry-After": "60"})

    # Test that the rate limit error is raised
    with pytest.raises(Exception) as exc_info:
        async with coindesk_source as source:
            async for _ in source.fetch_articles():
                pass

    assert "Rate limit exceeded" in str(exc_info.value)


@pytest.mark.asyncio
async def test_fetch_articles_empty_response(httpx_mock, coindesk_source):
    """Test handling of empty API response."""
    # Mock an empty response
    httpx_mock.add_response(
        status_code=200, json={"data": [], "meta": {"count": 0, "page": 1, "pages": 0}}
    )

    # Test the fetch_articles method
    articles = []
    async with coindesk_source as source:
        async for article in source.fetch_articles():
            articles.append(article)

    # Verify no articles were returned
    assert len(articles) == 0


def test_format_article(coindesk_source, mock_article):
    """Test article formatting."""
    formatted = coindesk_source.format_article(mock_article)

    # Check required fields
    assert formatted["source"] == "coindesk"
    assert formatted["title"] == "Test Article"
    assert formatted["content"] == "This is a test article about cryptocurrency."
    assert formatted["url"].startswith("https://www.coindesk.com/")
    assert formatted["published_at"] == datetime(2023, 1, 1, 12, 0, tzinfo=timezone.utc)
    assert formatted["author"] == "Test Author"
    assert formatted["categories"] == ["Bitcoin"]
    assert formatted["tags"] == ["bitcoin"]
    assert formatted["image_url"] == "https://example.com/image.jpg"


@pytest.mark.asyncio
async def test_fetch_articles_with_since(httpx_mock, coindesk_source, mock_article):
    """Test fetching articles with a since parameter."""
    since = datetime(2023, 1, 1, tzinfo=timezone.utc)

    # Mock the API response
    mock_response = {
        "data": [mock_article],
        "meta": {"count": 1, "page": 1, "pages": 1},
    }

    # Mock the HTTP request
    def match_request(request):
        # Check that the since parameter is in the URL
        return f"published_at%5Bgte%5D={since.strftime('%Y-%m-%dT%H:%M:%S%z')}" in str(
            request.url
        )

    httpx_mock.add_callback(
        lambda r: httpx.Response(200, json=mock_response),
        url=f"{coindesk_source.api_url}?*",
        match_querystring=False,
    )

    # Test the fetch_articles method with since parameter
    articles = []
    async with coindesk_source as source:
        async for article in source.fetch_articles(since=since):
            articles.append(article)

    # Verify the results
    assert len(articles) == 1
