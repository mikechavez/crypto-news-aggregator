import pytest
import asyncio
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
from sqlalchemy import select

from crypto_news_aggregator.core.news_collector import NewsCollector
from crypto_news_aggregator.db.models import Article, Source
from sqlalchemy.ext.asyncio import AsyncSession

# Add this to handle the select function in async tests
pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_newsapi_response():
    """Mock response from NewsAPI."""
    return {
        "status": "ok",
        "totalResults": 1,
        "articles": [
            {
                "source": {"id": "test-source", "name": "Test Source"},
                "author": "Test Author",
                "title": "Test Article",
                "description": "Test description",
                "url": "https://example.com/test-article",
                "urlToImage": "https://example.com/image.jpg",
                "publishedAt": "2025-01-01T12:00:00Z",
                "content": "Test content",
                "raw_data": {},
            }
        ],
    }


@pytest.mark.asyncio
async def test_collect_from_source(
    mock_newsapi_response, db_session: AsyncSession, article_service: "ArticleService"
):
    """Test collecting articles from a news source."""
    try:
        # Create a source in the database
        source = Source(id="test-source", name="Test Source")
        db_session.add(source)
        await db_session.commit()

        with patch(
            "crypto_news_aggregator.core.news_collector.NewsApiClient"
        ) as mock_newsapi:
            # Setup mock
            mock_client = MagicMock()
            mock_client.get_everything.return_value = mock_newsapi_response
            mock_newsapi.return_value = mock_client

            # Initialize collector with test session
            collector = NewsCollector(
                newsapi_client=mock_newsapi.return_value,
                article_service=article_service,
            )
            await collector.initialize()

            # Test collection
            result = await collector.collect_from_source("test-source")

            # Verify results
            assert result == 1  # One article collected
            mock_client.get_everything.assert_called_once_with(
                q="crypto OR cryptocurrency OR bitcoin OR ethereum",
                sources="test-source",
                language="en",
                sort_by="publishedAt",
                page_size=100,
            )

            # Verify article was saved to database
            await db_session.commit()  # Ensure all changes are committed
            articles = (await db_session.execute(select(Article))).scalars().all()
            assert len(articles) == 1
            assert articles[0].title == "Test Article"
    finally:
        # Clean up
        await db_session.rollback()


@pytest.mark.asyncio
async def test_process_article(
    db_session: AsyncSession, article_service: "ArticleService"
):
    """Test processing and storing an article."""
    try:
        # Create a source in the database
        source = Source(id="test-source", name="Test Source")
        db_session.add(source)
        await db_session.commit()

        article_data = {
            "source": {"id": "test-source", "name": "Test Source"},
            "author": "Test Author",
            "title": "Test Article",
            "description": "Test description",
            "url": "https://example.com/test-article",
            "urlToImage": "https://example.com/image.jpg",
            "publishedAt": "2025-01-01T12:00:00Z",
            "content": "Test content",
            "raw_data": {},
        }

        # Initialize collector
        collector = NewsCollector(article_service=article_service)
        await collector.initialize()

        # Test processing
        result = await collector._process_article(article_data, db_session)

        # Verify results
        assert result is not None
        assert result.title == "Test Article"
        assert result.source_id == "test-source"

        # Verify article was saved to database
        await db_session.commit()  # Ensure all changes are committed
        article = (
            await db_session.execute(
                select(Article).where(Article.url == "https://example.com/test-article")
            )
        ).scalar_one_or_none()

        assert article is not None
        assert article.title == "Test Article"
        assert article.source_id == "test-source"
    finally:
        # Clean up
        await db_session.rollback()


@pytest.mark.asyncio
async def test_duplicate_article_handling(
    db_session: AsyncSession, article_service: "ArticleService"
):
    """Test that duplicate articles are handled correctly."""
    try:
        # Create a source in the database
        source = Source(id="test-source", name="Test Source")
        db_session.add(source)
        await db_session.commit()

        # Create an existing article
        existing_article = Article(
            title="Existing Article",
            url="https://example.com/test-article",
            source_id="test-source",
            content="Existing content",
        )
        db_session.add(existing_article)
        await db_session.commit()

        article_data = {
            "source": {"id": "test-source", "name": "Test Source"},
            "author": "Test Author",
            "title": "Test Article",  # Different title but same URL
            "description": "Test description",
            "url": "https://example.com/test-article",  # Same URL as existing
            "urlToImage": "https://example.com/image.jpg",
            "publishedAt": "2025-01-01T12:00:00Z",
            "content": "Test content",
            "raw_data": {},
        }

        # Initialize collector
        collector = NewsCollector(article_service=article_service)
        await collector.initialize()

        # Test processing
        result = await collector._process_article(article_data, db_session)

        # Verify article was not added again
        assert result is None

        # Verify only one article exists in the database
        article_count = (await db_session.execute(select(Article))).scalars().count()
        assert article_count == 1

        # Verify the original article was not updated
        article = (await db_session.execute(select(Article))).scalar_one()
        assert article.title == "Existing Article"
    finally:
        # Clean up
        await db_session.rollback()


@pytest.mark.asyncio
async def test_error_handling(
    caplog, db_session: AsyncSession, article_service: "ArticleService"
):
    """Test error handling during news collection."""
    try:
        # Create a source in the database
        source = Source(id="test-source", name="Test Source")
        db_session.add(source)
        await db_session.commit()

        with patch(
            "crypto_news_aggregator.core.news_collector.NewsApiClient"
        ) as mock_newsapi:
            # Setup mock to raise an exception
            mock_client = MagicMock()
            mock_client.get_everything.side_effect = Exception("API Error")
            mock_newsapi.return_value = mock_client

            collector = NewsCollector(
                newsapi_client=mock_newsapi.return_value,
                article_service=article_service,
            )
            await collector.initialize()

            # Test error handling
            with caplog.at_level(logging.ERROR):
                result = await collector.collect_from_source("test-source")

                # Verify error was logged
                assert "Error collecting from test-source" in caplog.text
                assert "API Error" in caplog.text
                assert result == 0  # No articles collected due to error
    finally:
        # Clean up
        await db_session.rollback()
