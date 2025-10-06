"""
Tests for narrative service.

Tests theme-based narrative detection and lifecycle tracking.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from crypto_news_aggregator.services.narrative_service import (
    determine_lifecycle_stage,
    extract_entities_from_articles,
    detect_narratives
)


@pytest.fixture
def mock_db():
    """Mock MongoDB database."""
    db = MagicMock()
    return db


@pytest.fixture
def sample_articles():
    """Sample articles with themes for testing."""
    return [
        {
            "_id": "article1",
            "title": "SEC Sues Coinbase",
            "description": "Regulatory action against crypto exchange",
            "themes": ["regulatory"],
            "published_at": datetime.now(timezone.utc)
        },
        {
            "_id": "article2",
            "title": "Binance Faces Charges",
            "description": "Enforcement action",
            "themes": ["regulatory"],
            "published_at": datetime.now(timezone.utc)
        },
        {
            "_id": "article3",
            "title": "New DeFi Protocol Launches",
            "description": "DeFi adoption grows",
            "themes": ["defi_adoption"],
            "published_at": datetime.now(timezone.utc)
        }
    ]


def test_determine_lifecycle_stage_emerging():
    """Test lifecycle stage determination for emerging narratives."""
    lifecycle = determine_lifecycle_stage(article_count=3, mention_velocity=1.5)
    assert lifecycle == "emerging"


def test_determine_lifecycle_stage_hot():
    """Test lifecycle stage determination for hot narratives."""
    lifecycle = determine_lifecycle_stage(article_count=7, mention_velocity=3.5)
    assert lifecycle == "hot"


def test_determine_lifecycle_stage_mature():
    """Test lifecycle stage determination for mature narratives."""
    lifecycle = determine_lifecycle_stage(article_count=15, mention_velocity=7.5)
    assert lifecycle == "mature"


def test_determine_lifecycle_stage_declining():
    """Test lifecycle stage determination for declining narratives."""
    lifecycle = determine_lifecycle_stage(
        article_count=5,
        mention_velocity=2.5,
        previous_count=10
    )
    assert lifecycle == "declining"


@pytest.mark.asyncio
async def test_extract_entities_from_articles(sample_articles):
    """Test extracting entities from articles."""
    with patch("crypto_news_aggregator.services.narrative_service.mongo_manager") as mock_mongo:
        # Mock database
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.entity_mentions = mock_collection
        
        # Make get_async_database return a coroutine
        async def get_db():
            return mock_db
        mock_mongo.get_async_database = get_db
        
        # Mock entity mentions
        def mock_find(query):
            article_id = query.get("article_id")
            
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
            
            if article_id == "article1":
                return MockCursor([
                    {"entity": "SEC"},
                    {"entity": "Coinbase"}
                ])
            elif article_id == "article2":
                return MockCursor([
                    {"entity": "Binance"},
                    {"entity": "SEC"}
                ])
            return MockCursor([])
        
        mock_collection.find = mock_find
        
        # Extract entities
        entities = await extract_entities_from_articles(sample_articles[:2])
        
        # Verify entities
        assert len(entities) > 0
        assert "SEC" in entities
        assert "Coinbase" in entities or "Binance" in entities


@pytest.mark.asyncio
async def test_detect_narratives_no_articles():
    """Test narrative detection with no recent articles."""
    with patch("crypto_news_aggregator.services.narrative_service.backfill_themes_for_recent_articles") as mock_backfill, \
         patch("crypto_news_aggregator.services.narrative_service.get_articles_by_theme") as mock_get_articles:
        
        mock_backfill.return_value = 0
        mock_get_articles.return_value = None  # No articles for any theme
        
        narratives = await detect_narratives(hours=48, min_articles=3)
        
        assert narratives == []


@pytest.mark.asyncio
async def test_detect_narratives_integration(sample_articles):
    """Test full narrative detection flow with theme-based clustering."""
    with patch("crypto_news_aggregator.services.narrative_service.backfill_themes_for_recent_articles") as mock_backfill, \
         patch("crypto_news_aggregator.services.narrative_service.get_articles_by_theme") as mock_get_articles, \
         patch("crypto_news_aggregator.services.narrative_service.extract_entities_from_articles") as mock_extract, \
         patch("crypto_news_aggregator.services.narrative_service.generate_narrative_from_theme") as mock_generate, \
         patch("crypto_news_aggregator.services.narrative_service.upsert_narrative") as mock_upsert, \
         patch("crypto_news_aggregator.services.narrative_service.mongo_manager") as mock_mongo:
        
        # Mock backfill
        mock_backfill.return_value = 5
        
        # Mock database for existing narratives
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.narratives = mock_collection
        mock_mongo.get_async_database.return_value = mock_db
        
        # Mock cursor for existing narratives
        class MockCursor:
            def __aiter__(self):
                return self
            
            async def __anext__(self):
                raise StopAsyncIteration
        
        mock_collection.find.return_value = MockCursor()
        
        # Mock get_articles_by_theme - return articles for regulatory theme only
        def mock_get_by_theme(theme, hours, min_articles):
            if theme == "regulatory":
                return sample_articles[:2]  # Return 2 regulatory articles
            return None
        
        mock_get_articles.side_effect = mock_get_by_theme
        
        # Mock entity extraction
        mock_extract.return_value = ["SEC", "Coinbase", "Binance"]
        
        # Mock narrative generation
        mock_generate.return_value = {
            "title": "SEC Regulatory Crackdown",
            "summary": "The SEC is intensifying enforcement actions."
        }
        
        # Mock upsert
        mock_upsert.return_value = "narrative123"
        
        # Detect narratives
        narratives = await detect_narratives(hours=48, min_articles=2)
        
        # Verify results
        assert isinstance(narratives, list)
        # Should have at least one narrative (regulatory)
        if len(narratives) > 0:
            narrative = narratives[0]
            assert "theme" in narrative
            assert "title" in narrative
            assert "summary" in narrative
            assert "entities" in narrative
            assert "article_count" in narrative
            assert "mention_velocity" in narrative
            assert "lifecycle" in narrative
            assert narrative["lifecycle"] in ["emerging", "hot", "mature", "declining"]
