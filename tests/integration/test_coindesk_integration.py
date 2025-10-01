"""Integration tests for the CoinDesk news source."""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import AsyncGenerator
from unittest.mock import patch, MagicMock, AsyncMock

import httpx
import pytest
import pytest_asyncio
from pytest_httpx import HTTPXMock

from crypto_news_aggregator.core.news_sources.coindesk import CoinDeskSource

# Sample test data directory
TEST_DATA_DIR = Path(__file__).parent.parent / "test_data" / "coindesk"

# Sample article data
SAMPLE_ARTICLE = {
    "id": "12345",
    "title": "Test Article",
    "description": "This is a test article description.",
    "content": "<p>This is the article content with <b>HTML</b> tags.</p>",
    "url": "/test-article",
    "image": {"original_url": "https://example.com/image.jpg"},
    "published_at": "2023-01-01T12:00:00Z",
    "author": {"name": "Test Author"},
    "categories": [{"name": "Bitcoin"}],
    "tags": [{"slug": "bitcoin"}, {"slug": "crypto"}],
    "created_at": "2023-01-01T11:00:00Z",
    "updated_at": "2023-01-01T11:30:00Z",
}


@pytest_asyncio.fixture
async def coindesk_source():
    """Fixture that provides a CoinDesk source instance with a fresh client."""
    source = CoinDeskSource()
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
    return {"data": [sample_article], "meta": {"page": 1, "per_page": 1, "total": 1}}


@pytest.mark.asyncio
async def test_fetch_articles_success(
    coindesk_source: CoinDeskSource,
    httpx_mock: HTTPXMock,
    mock_article_response: dict,
    sample_article: dict,
):
    """Test successful article fetching from CoinDesk."""
    # Configure the mock to return our test data
    httpx_mock.add_response(
        method="GET",
        url=(
            "https://www.coindesk.com/v2/news"
            "?page=1&per_page=1&sort=-published_at&include_aggregations=false"
        ),
        json=mock_article_response,
    )

    # Fetch articles with a limit of 1
    articles = []
    async for article in coindesk_source.fetch_articles(limit=1):
        articles.append(article)

    # Verify results
    assert len(articles) == 1
    article = articles[0]
    assert article["title"] == sample_article["title"]
    # Check that HTML tags have been stripped
    assert "<p>" not in article["content"]
    assert "<b>" not in article["content"]
    assert "</b>" not in article["content"]
    assert "</p>" not in article["content"]
    assert article["url"] == "https://www.coindesk.com/test-article"
    assert article["image_url"] == sample_article["image"]["original_url"]
    assert article["author"] == sample_article["author"]["name"]
    assert "bitcoin" in article["cryptocurrencies"]  # From categories
    assert "crypto" in [t.lower() for t in article["tags"]]  # From tags


@pytest.mark.asyncio
async def test_fetch_articles_rate_limit(
    coindesk_source: CoinDeskSource, httpx_mock: HTTPXMock
):
    """Test rate limit handling."""
    # Mock rate limit response
    httpx_mock.add_response(status_code=429, headers={"Retry-After": "5"})

    # Add a successful response after rate limit
    httpx_mock.add_response(
        json={"data": [], "meta": {"page": 1, "per_page": 50, "total": 0}}
    )

    # This should not raise an exception
    articles = []
    async for article in coindesk_source.fetch_articles(limit=1, max_retries=1):
        articles.append(article)

    # Should have backed off and retried
    assert len(httpx_mock.get_requests()) == 2


@pytest.mark.asyncio
async def test_fetch_articles_retry_on_error(
    coindesk_source: CoinDeskSource, httpx_mock: HTTPXMock
):
    """Test retry behavior on server errors."""
    # First request fails with 500
    httpx_mock.add_response(
        method="GET",
        url=(
            "https://www.coindesk.com/v2/news"
            "?page=1&per_page=1&sort=-published_at&include_aggregations=false"
        ),
        status_code=500,
    )

    # Second request succeeds
    httpx_mock.add_response(
        method="GET",
        url=(
            "https://www.coindesk.com/v2/news"
            "?page=1&per_page=1&sort=-published_at&include_aggregations=false"
        ),
        json={
            "data": [
                {
                    "id": "123",
                    "title": "Test Article",
                    "description": "Test",
                    "content": "Test content with Bitcoin",
                    "url": "/test",
                    "image": {"original_url": "https://example.com/image.jpg"},
                    "published_at": "2023-01-01T12:00:00Z",
                    "author": {"name": "Test"},
                    "categories": [{"name": "Bitcoin"}],
                    "tags": [{"slug": "crypto"}],
                }
            ],
            "meta": {"page": 1, "per_page": 1, "total": 1},
        },
    )

    # This should retry once and then succeed
    articles = []
    async for article in coindesk_source.fetch_articles(limit=1, max_retries=1):
        articles.append(article)

    # Should have made 2 requests (1 failed, 1 success)
    assert len(articles) == 1
    assert len(httpx_mock.get_requests()) == 2


@pytest.mark.asyncio
async def test_format_article(coindesk_source: CoinDeskSource, sample_article: dict):
    """Test article formatting."""
    # Process the sample article
    formatted = coindesk_source.format_article(sample_article)

    # Basic fields
    assert formatted["title"] == sample_article["title"]
    assert formatted["description"] == sample_article["description"]
    assert (
        formatted["content"] == "This is the article content with HTML tags."
    )  # HTML stripped
    assert formatted["url"] == "https://www.coindesk.com/test-article"  # URL normalized
    assert formatted["image_url"] == sample_article["image"]["original_url"]
    assert formatted["author"] == sample_article["author"]["name"]

    # Check HTML stripping
    assert "<p>" not in formatted["content"]
    assert "<b>" not in formatted["content"]

    # Check metadata
    assert formatted["metadata"]["language"] == "en"  # Default language
    assert isinstance(formatted["metadata"]["is_opinion"], bool)

    # Check cryptocurrency extraction (should find from categories and tags)
    assert "bitcoin" in formatted["cryptocurrencies"]  # From category name
    assert formatted["categories"] == ["Bitcoin"]
    assert set(tag.lower() for tag in formatted["tags"]) == {"bitcoin", "crypto"}


@pytest.mark.asyncio
async def test_with_statement():
    """Test context manager behavior."""
    async with CoinDeskSource() as source:
        assert isinstance(source, CoinDeskSource)
        assert source.client is not None
        assert source.client.is_closed is False

    # Client should be closed after context manager exits
    assert source.client.is_closed is True


@pytest.mark.asyncio
async def test_empty_response(coindesk_source: CoinDeskSource, httpx_mock: HTTPXMock):
    """Test handling of empty API responses."""
    httpx_mock.add_response(
        json={"data": [], "meta": {"page": 1, "per_page": 50, "total": 0}}
    )

    articles = []
    async for article in coindesk_source.fetch_articles():
        articles.append(article)

    assert len(articles) == 0
