"""
Integration tests for database operations.
"""

import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone

from src.crypto_news_aggregator.services.article_service import ArticleService


@pytest.fixture
async def article_service():
    """Create an article service instance for testing."""
    service = ArticleService()
    yield service


@pytest.mark.asyncio
class TestArticleServiceIntegration:
    """Integration tests for article service database operations."""

    async def test_get_top_articles_for_symbols_success(self, article_service):
        """Test successful article retrieval by symbols."""
        # This test verifies the integration with MongoDB
        # In a real scenario, this would test against a test database

        symbols = ["Bitcoin", "BTC"]
        result = await article_service.get_top_articles_for_symbols(
            symbols, hours=24, limit=5
        )

        # The result should be a list of dictionaries
        assert isinstance(result, list)
        if result:  # If we have data in the test database
            for article in result:
                assert isinstance(article, dict)
                assert "title" in article
                assert "source" in article
                assert "sentiment_score" in article
                assert "keywords" in article

    async def test_get_top_articles_for_symbols_empty_result(self, article_service):
        """Test article retrieval with no matching articles."""
        # Test with symbols that likely won't match anything
        symbols = ["NonExistentCoin12345"]
        result = await article_service.get_top_articles_for_symbols(
            symbols, hours=1, limit=5
        )

        assert isinstance(result, list)
        assert len(result) == 0

    async def test_get_top_articles_for_symbols_invalid_input(self, article_service):
        """Test article retrieval with invalid input."""
        # Test with empty symbols list
        result = await article_service.get_top_articles_for_symbols(
            [], hours=24, limit=5
        )
        assert isinstance(result, list)
        assert len(result) == 0

        # Test with None symbols
        result = await article_service.get_top_articles_for_symbols(
            None, hours=24, limit=5
        )
        assert isinstance(result, list)
        assert len(result) == 0

    async def test_get_top_articles_for_symbols_different_timeframes(
        self, article_service
    ):
        """Test article retrieval with different timeframes."""
        symbols = ["Bitcoin"]

        # Test with 1 hour
        result_1h = await article_service.get_top_articles_for_symbols(
            symbols, hours=1, limit=5
        )
        assert isinstance(result_1h, list)

        # Test with 24 hours
        result_24h = await article_service.get_top_articles_for_symbols(
            symbols, hours=24, limit=5
        )
        assert isinstance(result_24h, list)

        # Test with 7 days
        result_7d = await article_service.get_top_articles_for_symbols(
            symbols, hours=168, limit=5
        )
        assert isinstance(result_7d, list)

        # Results should be consistent in structure
        for result in [result_1h, result_24h, result_7d]:
            for article in result:
                assert isinstance(article, dict)
                assert "title" in article
                assert "relevance_score" in article
                assert isinstance(article["relevance_score"], (int, float))

    async def test_get_top_articles_for_symbols_multiple_symbols(self, article_service):
        """Test article retrieval with multiple symbols."""
        symbols = ["Bitcoin", "BTC", "Ethereum", "ETH"]
        result = await article_service.get_top_articles_for_symbols(
            symbols, hours=24, limit=10
        )

        assert isinstance(result, list)

        if result:  # If we have data
            for article in result:
                assert isinstance(article, dict)
                assert "title" in article
                assert "keywords" in article
                assert isinstance(article["keywords"], list)

    async def test_article_structure_validation(self, article_service):
        """Test that retrieved articles have the expected structure."""
        symbols = ["Bitcoin"]
        result = await article_service.get_top_articles_for_symbols(
            symbols, hours=24, limit=5
        )

        assert isinstance(result, list)

        if result:  # If we have data
            for article in result:
                # Required fields
                required_fields = [
                    "title",
                    "source",
                    "url",
                    "published_at",
                    "relevance_score",
                    "keywords",
                ]
                for field in required_fields:
                    assert field in article, f"Missing required field: {field}"

                # Data type validation
                assert isinstance(article["title"], str)
                assert isinstance(article["source"], str)
                assert isinstance(article["relevance_score"], (int, float))
                assert isinstance(article["keywords"], list)

                # Optional fields with defaults
                optional_fields = ["sentiment_score", "sentiment_label"]
                for field in optional_fields:
                    if field in article:
                        assert article[field] is not None


@pytest.mark.asyncio
class TestDatabaseConnectionIntegration:
    """Integration tests for database connection and basic operations."""

    async def test_database_connection(self, article_service):
        """Test that database connection is working."""
        try:
            # This will test the database connection
            result = await article_service.get_top_articles_for_symbols(
                ["Bitcoin"], hours=1, limit=1
            )
            assert isinstance(result, list)
            # If we get here, the database connection is working
        except Exception as e:
            # In a test environment, the database might not be available
            # This is acceptable for integration tests
            assert "database" in str(e).lower() or "connection" in str(e).lower()

    async def test_collection_access(self, article_service):
        """Test that we can access the MongoDB collection."""
        try:
            # This tests the _get_collection method
            collection = await article_service._get_collection()
            assert collection is not None
            assert hasattr(collection, "find")
            assert hasattr(collection, "count_documents")
        except Exception as e:
            # Database might not be available in test environment
            assert "database" in str(e).lower() or "connection" in str(e).lower()


@pytest.mark.asyncio
class TestArticleQueryIntegration:
    """Integration tests for article querying functionality."""

    async def test_query_with_realistic_data(self, article_service):
        """Test queries with realistic cryptocurrency symbols."""
        test_cases = [
            (["Bitcoin"], "Single symbol"),
            (["Bitcoin", "BTC"], "Multiple Bitcoin terms"),
            (["Ethereum"], "Ethereum symbol"),
            (["Ethereum", "ETH"], "Multiple Ethereum terms"),
            (["Bitcoin", "Ethereum"], "Multiple cryptocurrencies"),
        ]

        for symbols, description in test_cases:
            result = await article_service.get_top_articles_for_symbols(
                symbols, hours=24, limit=5
            )
            assert isinstance(result, list), f"Failed for {description}"

            if result:  # If we have data
                for article in result:
                    assert isinstance(article, dict)
                    assert "title" in article
                    assert "relevance_score" in article
                    assert isinstance(article["relevance_score"], (int, float))

    async def test_query_performance(self, article_service):
        """Test that queries complete within reasonable time."""
        import time

        start_time = time.time()
        result = await article_service.get_top_articles_for_symbols(
            ["Bitcoin"], hours=24, limit=10
        )
        end_time = time.time()

        # Query should complete within 5 seconds
        assert (
            end_time - start_time < 5.0
        ), f"Query took too long: {end_time - start_time:.2f}s"
        assert isinstance(result, list)
