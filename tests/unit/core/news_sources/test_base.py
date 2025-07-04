"""Tests for the base news source class."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta

from crypto_news_aggregator.core.news_sources.base import NewsSource, NewsSourceError

class TestNewsSource:
    """Test the base NewsSource class."""
    
    class TestSource(NewsSource):
        """Test implementation of NewsSource."""
        
        async def fetch_articles(self, since=None, limit=50):
            """Mock implementation of fetch_articles."""
            yield {"id": "1", "title": "Test Article", "content": "Test content"}
            
        def format_article(self, raw_article):
            """Mock implementation of format_article."""
            return raw_article
    
    @pytest.fixture
    def source(self):
        """Create a test news source instance."""
        return self.TestSource("test_source", "https://example.com")
    
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
        """Test that abstract methods raise NotImplementedError."""
        class IncompleteSource(NewsSource):
            pass
            
        source = IncompleteSource("incomplete", "https://example.com")
        
        with pytest.raises(NotImplementedError):
            source.format_article({})
            
        # Test that fetch_articles is an async generator
        import inspect
        assert inspect.isasyncgenfunction(source.fetch_articles)
