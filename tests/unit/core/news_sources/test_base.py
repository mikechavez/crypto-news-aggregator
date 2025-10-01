"""Tests for the base news source class."""

import pytest
import abc
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
from typing import Optional, AsyncGenerator, Dict, Any

from crypto_news_aggregator.core.news_sources.base import NewsSource, NewsSourceError


class TestSource(NewsSource):
    """Test implementation of NewsSource."""

    def __init__(self, name: str, base_url: str, api_key: Optional[str] = None):
        super().__init__(name, base_url, api_key)
        self._is_closed = False

    async def fetch_articles(
        self, since: Optional[datetime] = None, limit: int = 50
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Mock implementation of fetch_articles."""
        if self._is_closed:
            raise RuntimeError("Source is closed")
        yield {"id": "1", "title": "Test Article", "content": "Test content"}

    def format_article(self, raw_article: Dict[str, Any]) -> Dict[str, Any]:
        """Mock implementation of format_article."""
        return raw_article

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Mark the source as closed when exiting context."""
        self._is_closed = True


class TestNewsSource:
    """Test the base NewsSource class."""

    @pytest.fixture
    def source(self):
        """Create a test news source instance."""
        return TestSource("test_source", "https://example.com")

    @pytest.mark.asyncio
    async def test_context_manager(self, source):
        """Test the async context manager."""
        async with source as s:
            assert s == source

    @pytest.mark.asyncio
    async def test_fetch_articles(self, source):
        """Test the fetch_articles method."""
        articles = []
        async for article in source.fetch_articles():
            articles.append(article)

        assert len(articles) == 1
        assert articles[0]["title"] == "Test Article"

    def test_get_default_since(self, source):
        """Test the _get_default_since method."""
        now = datetime.now(timezone.utc)
        since = source._get_default_since()

        # Should be approximately 1 hour ago
        assert (now - since) >= timedelta(minutes=59)
        assert (now - since) <= timedelta(minutes=61)

    def test_log_fetch(self, source, caplog):
        """Test the _log_fetch method."""
        start_time = source.last_fetch_time

        with caplog.at_level("INFO"):
            source._log_fetch(5)

        assert "Fetched 5 new articles from test_source" in caplog.text
        assert source.last_fetch_time > start_time

    def test_abstract_methods(self):
        """Test that abstract methods raise TypeError when not implemented."""
        # Test that we can't instantiate a class without implementing abstract methods
        with pytest.raises(TypeError) as exc_info:

            class IncompleteSource(NewsSource):
                pass

            # This line should raise TypeError because abstract methods aren't implemented
            _ = IncompleteSource("incomplete", "https://example.com")

        # Verify the error message mentions the missing abstract methods
        error_msg = str(exc_info.value)
        assert "Can't instantiate abstract class IncompleteSource" in error_msg
        assert "fetch_articles" in error_msg
        assert "format_article" in error_msg

        # Test that we can't call the abstract methods directly
        with pytest.raises(NotImplementedError):
            # Create a class that implements both abstract methods but raises NotImplementedError
            class AnotherSource(NewsSource):
                async def fetch_articles(self, since=None, limit=50):
                    raise NotImplementedError("fetch_articles not implemented")

                def format_article(self, raw_article):
                    raise NotImplementedError("format_article not implemented")

            source = AnotherSource("another", "https://example.com")
            source.format_article({})

        # Test that a proper implementation works
        class ProperSource(NewsSource):
            async def fetch_articles(self, since=None, limit=50):
                yield {"title": "Test Article", "url": "https://example.com/test"}

            def format_article(self, raw_article):
                return {"title": raw_article["title"], "url": raw_article["url"]}

        source = ProperSource("proper", "https://example.com")

        # Test that fetch_articles can be awaited and returns an async generator
        import asyncio
        import inspect

        # Get the generator from the async function
        gen = source.fetch_articles()

        # Verify it's an async generator
        assert inspect.isasyncgen(gen)

        # Try to get the first item (should work)
        try:
            first = asyncio.run(gen.__anext__())
            assert isinstance(first, dict)
            assert "title" in first
            assert "url" in first
        except StopAsyncIteration:
            assert False, "fetch_articles should yield at least one article"
