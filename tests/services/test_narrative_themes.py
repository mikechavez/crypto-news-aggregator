"""
Tests for narrative theme extraction service.

Tests theme extraction from articles using Claude Sonnet.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, ANY

from crypto_news_aggregator.services.narrative_themes import (
    extract_themes_from_article,
    backfill_themes_for_recent_articles,
    get_articles_by_theme,
    generate_narrative_from_theme,
    THEME_CATEGORIES
)


@pytest.fixture
def sample_article_data():
    """Sample article data for testing."""
    return {
        "article_id": "test123",
        "title": "SEC Announces New Crypto Regulations",
        "summary": "The Securities and Exchange Commission has announced new regulatory frameworks for cryptocurrency exchanges and stablecoin issuers."
    }


@pytest.fixture
def mock_llm_response_themes():
    """Mock LLM response for theme extraction."""
    return '["regulatory", "stablecoin"]'


@pytest.fixture
def mock_llm_response_narrative():
    """Mock LLM response for narrative generation."""
    return '{"title": "SEC Regulatory Crackdown", "summary": "The SEC is intensifying enforcement actions against crypto exchanges."}'


@pytest.mark.asyncio
async def test_extract_themes_from_article_success(sample_article_data, mock_llm_response_themes):
    """Test successful theme extraction from article."""
    with patch("crypto_news_aggregator.services.narrative_themes.get_llm_provider") as mock_llm:
        # Mock LLM provider
        mock_provider = MagicMock()
        mock_provider._get_completion.return_value = mock_llm_response_themes
        mock_llm.return_value = mock_provider
        
        # Extract themes
        themes = await extract_themes_from_article(
            article_id=sample_article_data["article_id"],
            title=sample_article_data["title"],
            summary=sample_article_data["summary"]
        )
        
        # Assertions
        assert themes == ["regulatory", "stablecoin"]
        assert all(theme in THEME_CATEGORIES for theme in themes)
        mock_provider._get_completion.assert_called_once()


@pytest.mark.asyncio
async def test_extract_themes_filters_invalid_themes(sample_article_data):
    """Test that invalid themes are filtered out."""
    with patch("crypto_news_aggregator.services.narrative_themes.get_llm_provider") as mock_llm:
        # Mock LLM provider returning invalid themes
        mock_provider = MagicMock()
        mock_provider._get_completion.return_value = '["regulatory", "invalid_theme", "stablecoin"]'
        mock_llm.return_value = mock_provider
        
        themes = await extract_themes_from_article(
            article_id=sample_article_data["article_id"],
            title=sample_article_data["title"],
            summary=sample_article_data["summary"]
        )
        
        # Should filter out invalid_theme
        assert themes == ["regulatory", "stablecoin"]
        assert "invalid_theme" not in themes


@pytest.mark.asyncio
async def test_extract_themes_empty_content():
    """Test theme extraction with empty title and summary."""
    themes = await extract_themes_from_article(
        article_id="test123",
        title="",
        summary=""
    )
    
    assert themes == []


@pytest.mark.asyncio
async def test_extract_themes_llm_error(sample_article_data):
    """Test theme extraction when LLM fails."""
    with patch("crypto_news_aggregator.services.narrative_themes.get_llm_provider") as mock_llm:
        # Mock LLM provider raising exception
        mock_provider = MagicMock()
        mock_provider._get_completion.side_effect = Exception("LLM API error")
        mock_llm.return_value = mock_provider
        
        themes = await extract_themes_from_article(
            article_id=sample_article_data["article_id"],
            title=sample_article_data["title"],
            summary=sample_article_data["summary"]
        )
        
        # Should return empty list on error
        assert themes == []


@pytest.mark.asyncio
async def test_extract_themes_invalid_json(sample_article_data):
    """Test theme extraction with invalid JSON response."""
    with patch("crypto_news_aggregator.services.narrative_themes.get_llm_provider") as mock_llm:
        # Mock LLM provider returning invalid JSON
        mock_provider = MagicMock()
        mock_provider._get_completion.return_value = "not valid json"
        mock_llm.return_value = mock_provider
        
        themes = await extract_themes_from_article(
            article_id=sample_article_data["article_id"],
            title=sample_article_data["title"],
            summary=sample_article_data["summary"]
        )
        
        # Should return empty list on parse error
        assert themes == []


@pytest.mark.asyncio
async def test_get_articles_by_theme_success():
    """Test retrieving articles by theme."""
    with patch("crypto_news_aggregator.services.narrative_themes.mongo_manager") as mock_mongo:
        # Mock database
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.articles = mock_collection
        
        # Make get_async_database return a coroutine
        async def get_db():
            return mock_db
        mock_mongo.get_async_database = get_db
        
        # Mock articles
        sample_articles = [
            {"_id": "1", "title": "Article 1", "themes": ["regulatory"]},
            {"_id": "2", "title": "Article 2", "themes": ["regulatory"]},
            {"_id": "3", "title": "Article 3", "themes": ["regulatory"]},
        ]
        
        # Mock cursor
        class MockCursor:
            def __init__(self, data):
                self.data = data
                self.index = 0
            
            def __aiter__(self):
                return self
            
            async def __anext__(self):
                if self.index >= len(self.data):
                    raise StopAsyncIteration
                result = self.data[self.index]
                self.index += 1
                return result
            
            def sort(self, *args, **kwargs):
                return self
        
        mock_cursor = MockCursor(sample_articles)
        mock_collection.find.return_value = mock_cursor
        
        # Get articles
        articles = await get_articles_by_theme(theme="regulatory", hours=48, min_articles=2)
        
        # Assertions
        assert articles is not None
        assert len(articles) == 3
        mock_collection.find.assert_called_once()


@pytest.mark.asyncio
async def test_get_articles_by_theme_below_threshold():
    """Test that None is returned when below minimum article threshold."""
    with patch("crypto_news_aggregator.services.narrative_themes.mongo_manager") as mock_mongo:
        # Mock database
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.articles = mock_collection
        
        # Make get_async_database return a coroutine
        async def get_db():
            return mock_db
        mock_mongo.get_async_database = get_db
        
        # Mock only 1 article (below threshold of 2)
        sample_articles = [
            {"_id": "1", "title": "Article 1", "themes": ["regulatory"]},
        ]
        
        # Mock cursor
        class MockCursor:
            def __init__(self, data):
                self.data = data
                self.index = 0
            
            def __aiter__(self):
                return self
            
            async def __anext__(self):
                if self.index >= len(self.data):
                    raise StopAsyncIteration
                result = self.data[self.index]
                self.index += 1
                return result
            
            def sort(self, *args, **kwargs):
                return self
        
        mock_cursor = MockCursor(sample_articles)
        mock_collection.find.return_value = mock_cursor
        
        # Get articles
        articles = await get_articles_by_theme(theme="regulatory", hours=48, min_articles=2)
        
        # Should return None when below threshold
        assert articles is None


@pytest.mark.asyncio
async def test_generate_narrative_from_theme_success(mock_llm_response_narrative):
    """Test narrative generation from theme and articles."""
    with patch("crypto_news_aggregator.services.narrative_themes.get_llm_provider") as mock_llm:
        # Mock LLM provider
        mock_provider = MagicMock()
        mock_provider._get_completion.return_value = mock_llm_response_narrative
        mock_llm.return_value = mock_provider
        
        # Sample articles
        articles = [
            {"_id": "1", "title": "SEC sues Coinbase", "description": "Regulatory action"},
            {"_id": "2", "title": "Binance faces charges", "description": "Enforcement"},
        ]
        
        # Generate narrative
        narrative = await generate_narrative_from_theme(theme="regulatory", articles=articles)
        
        # Assertions
        assert narrative is not None
        assert narrative["title"] == "SEC Regulatory Crackdown"
        assert narrative["summary"] == "The SEC is intensifying enforcement actions against crypto exchanges."
        mock_provider._get_completion.assert_called_once()


@pytest.mark.asyncio
async def test_generate_narrative_from_theme_empty_articles():
    """Test narrative generation with empty articles list."""
    narrative = await generate_narrative_from_theme(theme="regulatory", articles=[])
    
    assert narrative is None


@pytest.mark.asyncio
async def test_generate_narrative_from_theme_llm_error():
    """Test narrative generation when LLM fails."""
    with patch("crypto_news_aggregator.services.narrative_themes.get_llm_provider") as mock_llm:
        # Mock LLM provider raising exception
        mock_provider = MagicMock()
        mock_provider._get_completion.side_effect = Exception("LLM API error")
        mock_llm.return_value = mock_provider
        
        articles = [
            {"_id": "1", "title": "Article 1", "description": "Content"},
        ]
        
        narrative = await generate_narrative_from_theme(theme="regulatory", articles=articles)
        
        # Should return None on error
        assert narrative is None


@pytest.mark.asyncio
async def test_generate_narrative_from_theme_fallback():
    """Test narrative generation fallback when JSON parsing fails."""
    with patch("crypto_news_aggregator.services.narrative_themes.get_llm_provider") as mock_llm:
        # Mock LLM provider returning invalid JSON
        mock_provider = MagicMock()
        mock_provider._get_completion.return_value = "invalid json"
        mock_llm.return_value = mock_provider
        
        articles = [
            {"_id": "1", "title": "Article 1", "description": "Content"},
        ]
        
        narrative = await generate_narrative_from_theme(theme="regulatory", articles=articles)
        
        # Should use fallback
        assert narrative is not None
        assert "Regulatory Narrative" in narrative["title"]
        assert "regulatory" in narrative["summary"].lower()


def test_theme_categories_defined():
    """Test that theme categories are properly defined."""
    assert len(THEME_CATEGORIES) > 0
    assert "regulatory" in THEME_CATEGORIES
    assert "defi_adoption" in THEME_CATEGORIES
    assert "institutional_investment" in THEME_CATEGORIES
    assert "stablecoin" in THEME_CATEGORIES
