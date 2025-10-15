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
    determine_lifecycle_state,
    extract_entities_from_articles,
    detect_narratives,
    calculate_grace_period,
    find_matching_narrative
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
        mock_narratives_collection = MagicMock()
        mock_db.articles = mock_articles_collection
        mock_db.narratives = mock_narratives_collection
        mock_mongo.get_async_database = AsyncMock(return_value=mock_db)
        
        # Mock narratives collection for find_matching_narrative
        class MockNarrativesCursor:
            async def to_list(self, length):
                return []  # No existing narratives to match
        
        mock_narratives_collection.find.return_value = MockNarrativesCursor()
        mock_narratives_collection.insert_one = AsyncMock(return_value=MagicMock(inserted_id="narrative123"))
        
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
        
        # Verify insert_one was called with entity_relationships
        assert mock_narratives_collection.insert_one.called
        call_args = mock_narratives_collection.insert_one.call_args[0][0]
        assert "entity_relationships" in call_args
        assert len(call_args["entity_relationships"]) == 2


# ============================================================================
# Adaptive Grace Period Tests
# ============================================================================

def test_calculate_grace_period_high_velocity():
    """Test grace period calculation for high-velocity narratives (>2 articles/day)."""
    # High velocity: 3.0 articles/day -> 7 days
    grace_period = calculate_grace_period(3.0)
    assert grace_period == 7
    
    # Very high velocity: 5.0 articles/day -> 7 days (minimum)
    grace_period = calculate_grace_period(5.0)
    assert grace_period == 7


def test_calculate_grace_period_medium_velocity():
    """Test grace period calculation for medium-velocity narratives (~1 article/day)."""
    # Medium velocity: 1.0 articles/day -> 14 days
    grace_period = calculate_grace_period(1.0)
    assert grace_period == 14
    
    # Slightly higher: 1.5 articles/day -> ~9 days
    grace_period = calculate_grace_period(1.5)
    assert grace_period == 9


def test_calculate_grace_period_low_velocity():
    """Test grace period calculation for low-velocity narratives (<0.5 articles/day)."""
    # Low velocity: 0.3 articles/day -> uses min threshold 0.5 -> 28 days
    grace_period = calculate_grace_period(0.3)
    assert grace_period == 28
    
    # Very low velocity: 0.1 articles/day -> uses min threshold 0.5 -> 28 days
    # Note: The formula clamps to 0.5 minimum, so 14/0.5 = 28, not 30
    grace_period = calculate_grace_period(0.1)
    assert grace_period == 28


def test_calculate_grace_period_edge_cases():
    """Test grace period calculation for edge cases."""
    # Zero velocity -> uses minimum threshold of 0.5 -> 28 days
    grace_period = calculate_grace_period(0.0)
    assert grace_period == 28
    
    # Negative velocity (shouldn't happen but handle gracefully) -> uses 0.5 -> 28 days
    grace_period = calculate_grace_period(-1.0)
    assert grace_period == 28
    
    # Exactly at threshold: 0.5 articles/day -> 28 days
    grace_period = calculate_grace_period(0.5)
    assert grace_period == 28
    
    # Just above threshold for minimum: 2.0 articles/day -> 7 days
    grace_period = calculate_grace_period(2.0)
    assert grace_period == 7


def test_calculate_grace_period_formula_correctness():
    """Test that the formula produces expected results across the range."""
    # Formula: min(30, max(7, int(14 / max(mention_velocity, 0.5))))
    
    test_cases = [
        (0.5, 28),   # 14 / 0.5 = 28
        (0.7, 20),   # 14 / 0.7 = 20
        (1.0, 14),   # 14 / 1.0 = 14
        (1.4, 10),   # 14 / 1.4 = 10
        (2.0, 7),    # 14 / 2.0 = 7 (at minimum threshold)
        (3.0, 7),    # 14 / 3.0 = 4.67 -> 7 (clamped to minimum)
        (10.0, 7),   # 14 / 10.0 = 1.4 -> 7 (clamped to minimum)
    ]
    
    for velocity, expected_days in test_cases:
        result = calculate_grace_period(velocity)
        assert result == expected_days, f"Failed for velocity {velocity}: expected {expected_days}, got {result}"


@pytest.mark.asyncio
async def test_find_matching_narrative_with_adaptive_grace_period():
    """Test that find_matching_narrative uses adaptive grace period when cluster_velocity is provided."""
    with patch("crypto_news_aggregator.services.narrative_service.mongo_manager") as mock_mongo, \
         patch("crypto_news_aggregator.services.narrative_service.calculate_fingerprint_similarity") as mock_similarity:
        
        # Mock database
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.narratives = mock_collection
        mock_mongo.get_async_database = AsyncMock(return_value=mock_db)
        
        # Create a candidate narrative that's 10 days old
        ten_days_ago = datetime.now(timezone.utc) - timedelta(days=10)
        candidate_narrative = {
            "_id": "narrative123",
            "title": "Test Narrative",
            "last_updated": ten_days_ago,
            "status": "hot",
            "fingerprint": {
                "nucleus_entity": "Bitcoin",
                "top_actors": ["Bitcoin", "Ethereum"],
                "key_actions": ["surged", "rallied"]
            }
        }
        
        # Mock cursor that simulates MongoDB filtering
        def make_mock_cursor(query):
            class MockCursor:
                async def to_list(self, length):
                    # Simulate MongoDB's filtering based on last_updated
                    cutoff = query.get("last_updated", {}).get("$gte")
                    if cutoff and candidate_narrative["last_updated"] >= cutoff:
                        return [candidate_narrative]
                    return []
            return MockCursor()
        
        mock_collection.find.side_effect = make_mock_cursor
        
        # Mock high similarity
        mock_similarity.return_value = 0.8
        
        # Test fingerprint
        test_fingerprint = {
            "nucleus_entity": "Bitcoin",
            "top_actors": ["Bitcoin", "Ethereum"],
            "key_actions": ["surged"]
        }
        
        # Test 1: High velocity (3.0 articles/day) -> 7 day grace period
        # The 10-day-old narrative should NOT be found (outside 7-day window)
        result = await find_matching_narrative(test_fingerprint, cluster_velocity=3.0)
        assert result is None, "High velocity should use 7-day window, excluding 10-day-old narrative"
        
        # Verify the query used the correct cutoff time (7 days)
        call_args = mock_collection.find.call_args[0][0]
        cutoff_time = call_args["last_updated"]["$gte"]
        expected_cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        # Allow 1 second tolerance for test execution time
        assert abs((cutoff_time - expected_cutoff).total_seconds()) < 1
        
        # Test 2: Low velocity (0.3 articles/day) -> 28 day grace period
        # The 10-day-old narrative SHOULD be found (within 28-day window)
        result = await find_matching_narrative(test_fingerprint, cluster_velocity=0.3)
        assert result is not None, "Low velocity should use 28-day window, including 10-day-old narrative"
        assert result["_id"] == "narrative123"
        
        # Verify the query used the correct cutoff time (28 days for 0.3 velocity)
        call_args = mock_collection.find.call_args[0][0]
        cutoff_time = call_args["last_updated"]["$gte"]
        expected_cutoff = datetime.now(timezone.utc) - timedelta(days=28)
        assert abs((cutoff_time - expected_cutoff).total_seconds()) < 1


@pytest.mark.asyncio
async def test_find_matching_narrative_default_grace_period():
    """Test that find_matching_narrative uses default 14-day grace period when cluster_velocity is not provided."""
    with patch("crypto_news_aggregator.services.narrative_service.mongo_manager") as mock_mongo, \
         patch("crypto_news_aggregator.services.narrative_service.calculate_fingerprint_similarity") as mock_similarity:
        
        # Mock database
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.narratives = mock_collection
        mock_mongo.get_async_database = AsyncMock(return_value=mock_db)
        
        # Mock cursor with no results
        class MockCursor:
            async def to_list(self, length):
                return []
        
        mock_collection.find.return_value = MockCursor()
        
        # Test fingerprint
        test_fingerprint = {
            "nucleus_entity": "Bitcoin",
            "top_actors": ["Bitcoin"],
            "key_actions": []
        }
        
        # Call without cluster_velocity (should use default 14 days)
        result = await find_matching_narrative(test_fingerprint)
        
        # Verify the query used the default 14-day cutoff
        call_args = mock_collection.find.call_args[0][0]
        cutoff_time = call_args["last_updated"]["$gte"]
        expected_cutoff = datetime.now(timezone.utc) - timedelta(days=14)
        assert abs((cutoff_time - expected_cutoff).total_seconds()) < 1


@pytest.mark.asyncio
async def test_find_matching_narrative_explicit_within_days_overrides_velocity():
    """Test that explicit within_days parameter is used when cluster_velocity is not provided."""
    with patch("crypto_news_aggregator.services.narrative_service.mongo_manager") as mock_mongo:
        
        # Mock database
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.narratives = mock_collection
        mock_mongo.get_async_database = AsyncMock(return_value=mock_db)
        
        # Mock cursor
        class MockCursor:
            async def to_list(self, length):
                return []
        
        mock_collection.find.return_value = MockCursor()
        
        # Test fingerprint
        test_fingerprint = {
            "nucleus_entity": "Bitcoin",
            "top_actors": ["Bitcoin"],
            "key_actions": []
        }
        
        # Call with explicit within_days=21 and no cluster_velocity
        result = await find_matching_narrative(test_fingerprint, within_days=21)
        
        # Verify the query used 21 days
        call_args = mock_collection.find.call_args[0][0]
        cutoff_time = call_args["last_updated"]["$gte"]
        expected_cutoff = datetime.now(timezone.utc) - timedelta(days=21)
        assert abs((cutoff_time - expected_cutoff).total_seconds()) < 1


@pytest.mark.asyncio
async def test_detect_narratives_uses_adaptive_grace_period():
    """Integration test: verify that detect_narratives passes cluster velocity to find_matching_narrative."""
    with patch("crypto_news_aggregator.services.narrative_service.backfill_narratives_for_recent_articles") as mock_backfill, \
         patch("crypto_news_aggregator.services.narrative_service.mongo_manager") as mock_mongo, \
         patch("crypto_news_aggregator.services.narrative_service.cluster_by_narrative_salience") as mock_cluster, \
         patch("crypto_news_aggregator.services.narrative_service.find_matching_narrative") as mock_find_match, \
         patch("crypto_news_aggregator.services.narrative_service.generate_narrative_from_cluster") as mock_generate:
        
        # Mock backfill
        mock_backfill.return_value = 5
        
        # Mock database
        mock_db = MagicMock()
        mock_articles_collection = MagicMock()
        mock_narratives_collection = MagicMock()
        mock_db.articles = mock_articles_collection
        mock_db.narratives = mock_narratives_collection
        mock_mongo.get_async_database = AsyncMock(return_value=mock_db)
        
        # Mock articles with narrative data
        sample_articles = [
            {
                "_id": "article1",
                "title": "Bitcoin Surges",
                "published_at": datetime.now(timezone.utc),
                "narrative_summary": {"actions": ["surged"]},
                "actors": ["Bitcoin"],
                "actor_salience": {"Bitcoin": 5},
                "nucleus_entity": "Bitcoin"
            },
            {
                "_id": "article2",
                "title": "Bitcoin Adoption",
                "published_at": datetime.now(timezone.utc),
                "narrative_summary": {"actions": ["adopted"]},
                "actors": ["Bitcoin"],
                "actor_salience": {"Bitcoin": 5},
                "nucleus_entity": "Bitcoin"
            },
            {
                "_id": "article3",
                "title": "Bitcoin Rally",
                "published_at": datetime.now(timezone.utc),
                "narrative_summary": {"actions": ["rallied"]},
                "actors": ["Bitcoin"],
                "actor_salience": {"Bitcoin": 5},
                "nucleus_entity": "Bitcoin"
            }
        ]
        
        # Mock cursor
        class MockCursor:
            async def to_list(self, length):
                return sample_articles
        
        mock_articles_collection.find.return_value = MockCursor()
        
        # Mock clustering - return one cluster with 3 articles
        mock_cluster.return_value = [sample_articles]
        
        # Mock find_matching_narrative - return None (no match, will create new)
        mock_find_match.return_value = None
        
        # Mock narrative generation
        mock_generate.return_value = {
            "title": "Bitcoin Rally",
            "summary": "Bitcoin surges to new highs",
            "actors": ["Bitcoin"],
            "nucleus_entity": "Bitcoin",
            "article_ids": ["article1", "article2", "article3"],
            "article_count": 3,
            "entity_relationships": []
        }
        
        # Mock insert_one
        mock_narratives_collection.insert_one = AsyncMock(return_value=MagicMock(inserted_id="narrative123"))
        
        # Detect narratives with 48-hour window
        narratives = await detect_narratives(hours=48, min_articles=2, use_salience_clustering=True)
        
        # Verify find_matching_narrative was called with cluster_velocity
        assert mock_find_match.called
        call_kwargs = mock_find_match.call_args[1]
        
        # Verify cluster_velocity was passed
        assert "cluster_velocity" in call_kwargs
        cluster_velocity = call_kwargs["cluster_velocity"]
        
        # Calculate expected velocity: 3 articles / 2 days = 1.5 articles/day
        expected_velocity = 3 / 2.0
        assert abs(cluster_velocity - expected_velocity) < 0.01, \
            f"Expected velocity ~{expected_velocity}, got {cluster_velocity}"
