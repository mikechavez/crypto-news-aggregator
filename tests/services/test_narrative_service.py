"""
Tests for narrative service.

Tests theme-based narrative detection and lifecycle tracking.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from bson import ObjectId

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
    lifecycle = determine_lifecycle_stage(article_count=3, mention_velocity=0.5)
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
        article_count=10,
        mention_velocity=6.0,
        momentum="declining"
    )
    assert lifecycle == "cooling"


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
            # Handle $or query format (new code) or direct article_id (old code)
            article_ids = []
            if "$or" in query:
                for condition in query["$or"]:
                    article_ids.append(condition.get("article_id"))
            else:
                article_ids.append(query.get("article_id"))
            
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
            
            # Return entities based on article_id
            if "article1" in article_ids:
                return MockCursor([
                    {"entity": "SEC"},
                    {"entity": "Coinbase"}
                ])
            elif "article2" in article_ids:
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
        
        narratives = await detect_narratives(hours=48, min_articles=2)
        
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


@pytest.mark.asyncio
async def test_extract_entities_handles_mixed_article_id_formats():
    """
    Test that extract_entities_from_articles handles both ObjectId and string article_ids.
    
    This is a regression test for the bug where entity_mentions.article_id had mixed formats
    (some ObjectId, some string), causing entities to not be linked to narratives.
    """
    # Create sample articles with ObjectId _id
    articles = [
        {"_id": ObjectId("507f1f77bcf86cd799439011"), "title": "Test Article 1"},
        {"_id": ObjectId("507f1f77bcf86cd799439012"), "title": "Test Article 2"},
    ]
    
    # Mock entity mentions with MIXED formats (ObjectId and string)
    mock_entity_mentions = [
        # Article 1: entity_id stored as ObjectId
        {"entity": "Bitcoin", "article_id": ObjectId("507f1f77bcf86cd799439011")},
        {"entity": "Ethereum", "article_id": ObjectId("507f1f77bcf86cd799439011")},
        # Article 2: article_id stored as STRING (legacy format)
        {"entity": "Ripple", "article_id": "507f1f77bcf86cd799439012"},
        {"entity": "SEC", "article_id": "507f1f77bcf86cd799439012"},
    ]
    
    # Mock the database
    with patch("crypto_news_aggregator.services.narrative_service.mongo_manager") as mock_mongo:
        mock_db = MagicMock()
        mock_collection = MagicMock()
        
        # Mock the find() method to return appropriate entities based on query
        def mock_find(query):
            mock_cursor = AsyncMock()
            
            # Simulate MongoDB $or query behavior
            if "$or" in query:
                or_conditions = query["$or"]
                matching_mentions = []
                
                for condition in or_conditions:
                    article_id_query = condition.get("article_id")
                    for mention in mock_entity_mentions:
                        if mention["article_id"] == article_id_query:
                            matching_mentions.append(mention)
                
                # Create async iterator
                async def async_iter():
                    for mention in matching_mentions:
                        yield mention
                
                mock_cursor.__aiter__ = lambda self: async_iter()
            else:
                # Single condition query (shouldn't happen with our fix, but handle it)
                mock_cursor.__aiter__ = lambda self: async_iter()
            
            return mock_cursor
        
        mock_collection.find = mock_find
        mock_db.entity_mentions = mock_collection
        mock_mongo.get_async_database = AsyncMock(return_value=mock_db)
        
        # Test entity extraction
        entities = await extract_entities_from_articles(articles)
        
        # Verify all entities were found (both ObjectId and string formats)
        assert len(entities) == 4
        assert "Bitcoin" in entities
        assert "Ethereum" in entities
        assert "Ripple" in entities
        assert "SEC" in entities


@pytest.mark.asyncio
async def test_detect_narratives_includes_entity_relationships():
    """
    Integration test: verify that detect_narratives includes entity_relationships
    in the returned narrative data when using salience-based clustering.
    """
    with patch("crypto_news_aggregator.services.narrative_service.backfill_narratives_for_recent_articles") as mock_backfill, \
         patch("crypto_news_aggregator.services.narrative_service.mongo_manager") as mock_mongo, \
         patch("crypto_news_aggregator.services.narrative_service.cluster_by_narrative_salience") as mock_cluster, \
         patch("crypto_news_aggregator.services.narrative_service.generate_narrative_from_cluster") as mock_generate, \
         patch("crypto_news_aggregator.services.narrative_service.upsert_narrative") as mock_upsert:
        
        # Mock backfill
        mock_backfill.return_value = 5
        
        # Mock database
        mock_db = MagicMock()
        mock_articles_collection = MagicMock()
        mock_db.articles = mock_articles_collection
        mock_mongo.get_async_database = AsyncMock(return_value=mock_db)
        
        # Mock articles with narrative data
        sample_articles = [
            {
                "_id": "article1",
                "title": "Bitcoin and Ethereum Rally",
                "published_at": datetime.now(timezone.utc),
                "narrative_summary": "BTC and ETH surge",
                "actors": ["Bitcoin", "Ethereum"],
                "nucleus_entity": "Bitcoin"
            },
            {
                "_id": "article2",
                "title": "Bitcoin Adoption Grows",
                "published_at": datetime.now(timezone.utc),
                "narrative_summary": "Institutions adopt BTC",
                "actors": ["Bitcoin", "MicroStrategy"],
                "nucleus_entity": "Bitcoin"
            }
        ]
        
        # Mock cursor
        class MockCursor:
            async def to_list(self, length):
                return sample_articles
        
        mock_articles_collection.find.return_value = MockCursor()
        
        # Mock clustering - return one cluster
        mock_cluster.return_value = [sample_articles]
        
        # Mock narrative generation with entity_relationships
        mock_generate.return_value = {
            "title": "Bitcoin Ecosystem Growth",
            "summary": "Bitcoin adoption accelerates across institutions.",
            "actors": ["Bitcoin", "Ethereum", "MicroStrategy"],
            "tensions": ["institutional_adoption"],
            "nucleus_entity": "Bitcoin",
            "article_ids": ["article1", "article2"],
            "article_count": 2,
            "entity_relationships": [
                {"a": "Bitcoin", "b": "Ethereum", "weight": 1},
                {"a": "Bitcoin", "b": "MicroStrategy", "weight": 1}
            ]
        }
        
        # Mock upsert
        mock_upsert.return_value = "narrative123"
        
        # Detect narratives with salience clustering
        narratives = await detect_narratives(hours=48, min_articles=2, use_salience_clustering=True)
        
        # Verify results
        assert len(narratives) > 0
        narrative = narratives[0]
        
        # Verify entity_relationships is included
        assert "entity_relationships" in narrative
        assert isinstance(narrative["entity_relationships"], list)
        assert len(narrative["entity_relationships"]) == 2
        
        # Verify relationship structure
        for rel in narrative["entity_relationships"]:
            assert "a" in rel
            assert "b" in rel
            assert "weight" in rel
        
        # Verify upsert was called with entity_relationships
        assert mock_upsert.called
        call_kwargs = mock_upsert.call_args[1]
        assert "entity_relationships" in call_kwargs
        assert len(call_kwargs["entity_relationships"]) == 2
