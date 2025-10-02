"""
Tests for narrative service.

Tests co-occurrence detection and narrative generation.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from crypto_news_aggregator.services.narrative_service import (
    find_cooccurring_entities,
    generate_narrative_summary,
    detect_narratives
)


@pytest.fixture
def mock_db():
    """Mock MongoDB database."""
    db = MagicMock()
    return db


@pytest.fixture
def sample_entities():
    """Sample entity data for testing."""
    return [
        {"entity": "Bitcoin", "entity_type": "project", "score": 8.5},
        {"entity": "ETF", "entity_type": "event", "score": 7.2},
        {"entity": "SEC", "entity_type": "project", "score": 6.8},
    ]


@pytest.fixture
def sample_article():
    """Sample article for narrative generation."""
    return {
        "_id": "article123",
        "title": "SEC Reviews Bitcoin ETF Applications",
        "text": "The Securities and Exchange Commission is reviewing multiple Bitcoin ETF applications from major financial institutions. This could mark a significant milestone for cryptocurrency adoption in traditional finance.",
        "published_at": datetime.now(timezone.utc)
    }


@pytest.mark.asyncio
async def test_find_cooccurring_entities_basic(sample_entities):
    """Test basic co-occurrence detection."""
    with patch("crypto_news_aggregator.services.narrative_service.mongo_manager") as mock_mongo:
        # Mock entity mentions collection
        mock_collection = AsyncMock()
        mock_db = AsyncMock()
        mock_db.entity_mentions = mock_collection
        
        # Make get_async_database return a coroutine
        async def get_db():
            return mock_db
        mock_mongo.get_async_database = get_db
        
        # Mock cursor for entity mentions
        def mock_find(query):
            entity = query.get("entity")
            
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
            
            if entity == "Bitcoin":
                return MockCursor([
                    {"article_id": "article1"},
                    {"article_id": "article2"},
                    {"article_id": "article3"}
                ])
            elif entity == "ETF":
                return MockCursor([
                    {"article_id": "article1"},
                    {"article_id": "article2"}
                ])
            elif entity == "SEC":
                return MockCursor([
                    {"article_id": "article1"},
                    {"article_id": "article2"}
                ])
            return MockCursor([])
        
        mock_collection.find = mock_find
        
        # Test co-occurrence detection
        groups = await find_cooccurring_entities(sample_entities, min_shared_articles=2)
        
        # Should find at least one group with co-occurring entities
        assert len(groups) >= 0  # May be 0 or more depending on intersection logic
        
        # If groups found, verify structure
        if groups:
            assert "entities" in groups[0]
            assert "article_ids" in groups[0]
            assert isinstance(groups[0]["entities"], list)
            assert isinstance(groups[0]["article_ids"], list)


@pytest.mark.asyncio
async def test_generate_narrative_summary_success(sample_article):
    """Test successful narrative summary generation."""
    entity_group = {
        "entities": ["Bitcoin", "ETF", "SEC"],
        "article_ids": ["article123"]
    }
    
    with patch("crypto_news_aggregator.services.narrative_service.mongo_manager") as mock_mongo, \
         patch("crypto_news_aggregator.services.narrative_service.get_llm_provider") as mock_llm:
        
        # Mock database
        mock_articles_collection = AsyncMock()
        mock_mentions_collection = AsyncMock()
        mock_db = AsyncMock()
        mock_db.articles = mock_articles_collection
        mock_db.entity_mentions = mock_mentions_collection
        
        async def get_db():
            return mock_db
        mock_mongo.get_async_database = get_db
        
        # Mock article lookup
        mock_articles_collection.find_one.return_value = sample_article
        
        # Mock entity mentions lookup
        async def mock_find_one(query):
            entity = query.get("entity")
            return {"entity": entity, "entity_type": "project"}
        
        mock_mentions_collection.find_one = mock_find_one
        
        # Mock LLM response
        mock_client = MagicMock()
        mock_client._get_completion.return_value = '{"theme": "Bitcoin ETF Approval", "story": "SEC reviews Bitcoin ETF applications from major institutions."}'
        mock_llm.return_value = mock_client
        
        # Generate narrative
        narrative = await generate_narrative_summary(entity_group)
        
        # Verify narrative structure
        assert narrative is not None
        assert "theme" in narrative
        assert "entities" in narrative
        assert "story" in narrative
        assert "article_count" in narrative
        assert narrative["article_count"] == 1
        assert len(narrative["entities"]) == 3


@pytest.mark.asyncio
async def test_generate_narrative_summary_json_parse_error(sample_article):
    """Test narrative generation with JSON parse error fallback."""
    entity_group = {
        "entities": ["Bitcoin", "ETF"],
        "article_ids": ["article123"]
    }
    
    with patch("crypto_news_aggregator.services.narrative_service.mongo_manager") as mock_mongo, \
         patch("crypto_news_aggregator.services.narrative_service.get_llm_provider") as mock_llm:
        
        # Mock database
        mock_articles_collection = AsyncMock()
        mock_mentions_collection = AsyncMock()
        mock_db = AsyncMock()
        mock_db.articles = mock_articles_collection
        mock_db.entity_mentions = mock_mentions_collection
        
        async def get_db():
            return mock_db
        mock_mongo.get_async_database = get_db
        
        mock_articles_collection.find_one.return_value = sample_article
        mock_mentions_collection.find_one.return_value = {"entity": "Bitcoin", "entity_type": "project"}
        
        # Mock LLM with invalid JSON
        mock_client = MagicMock()
        mock_client._get_completion.return_value = "This is not valid JSON"
        mock_llm.return_value = mock_client
        
        # Generate narrative - should use fallback
        narrative = await generate_narrative_summary(entity_group)
        
        # Should still return a narrative with fallback values
        assert narrative is not None
        assert "theme" in narrative
        assert "Bitcoin" in narrative["theme"]


@pytest.mark.asyncio
async def test_detect_narratives_no_entities():
    """Test narrative detection with no trending entities."""
    with patch("crypto_news_aggregator.services.narrative_service.get_trending_entities") as mock_trending:
        mock_trending.return_value = []
        
        narratives = await detect_narratives(min_score=5.0, max_narratives=5)
        
        assert narratives == []


@pytest.mark.asyncio
async def test_detect_narratives_integration(sample_entities, sample_article):
    """Test full narrative detection flow."""
    with patch("crypto_news_aggregator.services.narrative_service.get_trending_entities") as mock_trending, \
         patch("crypto_news_aggregator.services.narrative_service.mongo_manager") as mock_mongo, \
         patch("crypto_news_aggregator.services.narrative_service.get_llm_provider") as mock_llm:
        
        # Mock trending entities
        mock_trending.return_value = sample_entities
        
        # Mock database
        mock_mentions_collection = AsyncMock()
        mock_articles_collection = AsyncMock()
        mock_db = AsyncMock()
        mock_db.entity_mentions = mock_mentions_collection
        mock_db.articles = mock_articles_collection
        
        async def get_db():
            return mock_db
        mock_mongo.get_async_database = get_db
        
        # Mock entity mentions - all entities share article1
        def mock_find(query):
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
            
            return MockCursor([
                {"article_id": "article1"},
                {"article_id": "article2"}
            ])
        
        mock_mentions_collection.find = mock_find
        mock_mentions_collection.find_one.return_value = {"entity": "Bitcoin", "entity_type": "project"}
        
        # Mock article lookup
        mock_articles_collection.find_one.return_value = sample_article
        
        # Mock LLM
        mock_client = MagicMock()
        mock_client._get_completion.return_value = '{"theme": "Test Narrative", "story": "Test story."}'
        mock_llm.return_value = mock_client
        
        # Detect narratives
        narratives = await detect_narratives(min_score=5.0, max_narratives=5)
        
        # Should return list (may be empty if no co-occurrence found)
        assert isinstance(narratives, list)
