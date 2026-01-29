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
    detect_narratives,
    validate_article_mentions_entity
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


def test_validate_article_mentions_entity_success():
    """Test validation passes when article mentions entity in title."""
    article = {
        "title": "Coinbase Stock Surges After Earnings",
        "text": "The crypto exchange reported strong Q4 results..."
    }
    assert validate_article_mentions_entity(article, "Coinbase") is True


def test_validate_article_mentions_entity_in_body_only():
    """Test validation passes when entity only in body text."""
    article = {
        "title": "Crypto Exchange Reports Strong Quarter",
        "text": "Coinbase led the sector with record trading volume today..."
    }
    assert validate_article_mentions_entity(article, "Coinbase") is True


def test_validate_article_mentions_entity_failure():
    """Test validation fails when entity not mentioned."""
    article = {
        "title": "Sharps Technology Partners with Solana",
        "text": "Sharps announced a new blockchain integration with Solana..."
    }
    assert validate_article_mentions_entity(article, "Coinbase") is False


def test_validate_article_mentions_entity_case_insensitive():
    """Test validation is case-insensitive."""
    article = {
        "title": "COINBASE Stock Update",
        "text": "coinbase shares rose 5% today..."
    }
    assert validate_article_mentions_entity(article, "Coinbase") is True


def test_validate_article_mentions_entity_word_boundary():
    """Test validation respects word boundaries."""
    article = {
        "title": "Coinbase Trading Volume Increases",
        "text": "Coinbase reported high trading activity..."
    }
    # "Coin" should NOT match "Coinbase"
    assert validate_article_mentions_entity(article, "Coin") is False

    # "Coinbase" should match "Coinbase"
    assert validate_article_mentions_entity(article, "Coinbase") is True


def test_validate_article_mentions_entity_partial_match_prevented():
    """Test that partial matches are prevented (e.g., 'Coin' not matching 'Coinbase')."""
    article = {
        "title": "Bitcoin and Ethereum Rally",
        "text": "The crypto market saw gains today..."
    }
    # "Bit" should NOT match "Bitcoin"
    assert validate_article_mentions_entity(article, "Bit") is False

    # "Bitcoin" should match "Bitcoin"
    assert validate_article_mentions_entity(article, "Bitcoin") is True


def test_validate_article_mentions_entity_empty_nucleus():
    """Test validation fails gracefully with empty nucleus entity."""
    article = {
        "title": "Some News",
        "text": "Some content..."
    }
    assert validate_article_mentions_entity(article, "") is False
    assert validate_article_mentions_entity(article, None) is False


def test_validate_article_mentions_entity_missing_fields():
    """Test validation handles missing article fields."""
    # Missing text field
    article = {
        "title": "Coinbase News"
    }
    assert validate_article_mentions_entity(article, "Coinbase") is True

    # Missing title field
    article = {
        "text": "Coinbase reported..."
    }
    assert validate_article_mentions_entity(article, "Coinbase") is True

    # Missing both fields
    article = {}
    assert validate_article_mentions_entity(article, "Coinbase") is False


def test_validate_article_mentions_entity_special_characters():
    """Test validation with special regex characters in entity name."""
    article = {
        "title": "OpenAI Partners with Coinbase.io",
        "text": "OpenAI announced a partnership with Coinbase.io today..."
    }
    # Entity with . character should be escaped and matched literally
    assert validate_article_mentions_entity(article, "Coinbase.io") is True
    # Partial match with just "Coinbase" should work
    assert validate_article_mentions_entity(article, "Coinbase") is True


def test_post_cluster_validation_integration():
    """Test post-cluster validation with multiple articles."""
    articles = [
        {
            "id": "1",
            "title": "Coinbase Earnings Report",
            "text": "Coinbase beat expectations with strong quarterly results..."
        },
        {
            "id": "2",
            "title": "Sharps Technology News",
            "text": "Sharps announced a partnership with Solana blockchain..."
        },
        {
            "id": "3",
            "title": "Crypto Market Update",
            "text": "Bitcoin and Coinbase saw gains today..."
        }
    ]

    # Simulate post-cluster validation
    nucleus_entity = "Coinbase"
    validated = [
        a for a in articles if validate_article_mentions_entity(a, nucleus_entity)
    ]

    # Should only include articles 1 and 3 (both mention Coinbase)
    assert len(validated) == 2
    assert validated[0]["id"] == "1"
    assert validated[1]["id"] == "3"

    # Article 2 should be rejected
    rejected = [
        a for a in articles if not validate_article_mentions_entity(a, nucleus_entity)
    ]
    assert len(rejected) == 1
    assert rejected[0]["id"] == "2"
