"""
Tests for narrative lifecycle state tracking.

Tests the determine_lifecycle_state function and its integration
into the narrative detection workflow.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from crypto_news_aggregator.services.narrative_service import (
    determine_lifecycle_state,
    detect_narratives
)


class TestDetermineLifecycleState:
    """Unit tests for determine_lifecycle_state function."""
    
    def test_emerging_state_low_article_count(self):
        """Test emerging state for narratives with < 4 articles."""
        now = datetime.now(timezone.utc)
        first_seen = now - timedelta(hours=12)
        last_updated = now - timedelta(hours=1)
        
        state = determine_lifecycle_state(
            article_count=3,
            mention_velocity=0.5,
            first_seen=first_seen,
            last_updated=last_updated
        )
        
        assert state == 'emerging'
    
    def test_emerging_state_edge_case(self):
        """Test emerging state for 4-6 articles with low velocity."""
        now = datetime.now(timezone.utc)
        first_seen = now - timedelta(days=2)
        last_updated = now - timedelta(hours=1)
        
        state = determine_lifecycle_state(
            article_count=5,
            mention_velocity=1.0,  # Below 1.5 threshold
            first_seen=first_seen,
            last_updated=last_updated
        )
        
        assert state == 'emerging'
    
    def test_rising_state_moderate_velocity(self):
        """Test rising state for velocity >= 1.5 and article_count < 7."""
        now = datetime.now(timezone.utc)
        first_seen = now - timedelta(days=2)
        last_updated = now - timedelta(hours=1)
        
        state = determine_lifecycle_state(
            article_count=5,
            mention_velocity=2.0,  # >= 1.5
            first_seen=first_seen,
            last_updated=last_updated
        )
        
        assert state == 'rising'
    
    def test_rising_state_boundary(self):
        """Test rising state at exact velocity threshold."""
        now = datetime.now(timezone.utc)
        first_seen = now - timedelta(days=1)
        last_updated = now - timedelta(hours=1)
        
        state = determine_lifecycle_state(
            article_count=6,
            mention_velocity=1.5,  # Exactly at threshold
            first_seen=first_seen,
            last_updated=last_updated
        )
        
        assert state == 'rising'
    
    def test_hot_state_high_article_count(self):
        """Test hot state for article_count >= 7."""
        now = datetime.now(timezone.utc)
        first_seen = now - timedelta(days=3)
        last_updated = now - timedelta(hours=1)
        
        state = determine_lifecycle_state(
            article_count=7,
            mention_velocity=1.0,
            first_seen=first_seen,
            last_updated=last_updated
        )
        
        assert state == 'hot'
    
    def test_hot_state_high_velocity(self):
        """Test hot state for mention_velocity >= 3.0."""
        now = datetime.now(timezone.utc)
        first_seen = now - timedelta(days=1)
        last_updated = now - timedelta(hours=1)
        
        state = determine_lifecycle_state(
            article_count=5,
            mention_velocity=3.5,  # >= 3.0
            first_seen=first_seen,
            last_updated=last_updated
        )
        
        assert state == 'hot'
    
    def test_hot_state_both_conditions(self):
        """Test hot state when both article count and velocity are high."""
        now = datetime.now(timezone.utc)
        first_seen = now - timedelta(days=2)
        last_updated = now - timedelta(hours=1)
        
        state = determine_lifecycle_state(
            article_count=10,
            mention_velocity=4.0,
            first_seen=first_seen,
            last_updated=last_updated
        )
        
        assert state == 'hot'
    
    def test_cooling_state_three_days_no_update(self):
        """Test cooling state for no new articles in last 3 days."""
        now = datetime.now(timezone.utc)
        first_seen = now - timedelta(days=10)
        last_updated = now - timedelta(days=3, hours=1)  # Just over 3 days
        
        state = determine_lifecycle_state(
            article_count=10,
            mention_velocity=2.0,
            first_seen=first_seen,
            last_updated=last_updated
        )
        
        assert state == 'cooling'
    
    def test_cooling_state_boundary(self):
        """Test cooling state at exactly 3 days since update."""
        now = datetime.now(timezone.utc)
        first_seen = now - timedelta(days=7)
        last_updated = now - timedelta(days=3)  # Exactly 3 days
        
        state = determine_lifecycle_state(
            article_count=8,
            mention_velocity=1.5,
            first_seen=first_seen,
            last_updated=last_updated
        )
        
        assert state == 'cooling'
    
    def test_dormant_state_seven_days_no_update(self):
        """Test dormant state for no new articles in last 7 days."""
        now = datetime.now(timezone.utc)
        first_seen = now - timedelta(days=30)
        last_updated = now - timedelta(days=8)  # Over 7 days
        
        state = determine_lifecycle_state(
            article_count=15,
            mention_velocity=0.5,
            first_seen=first_seen,
            last_updated=last_updated
        )
        
        assert state == 'dormant'
    
    def test_dormant_state_boundary(self):
        """Test dormant state at exactly 7 days since update."""
        now = datetime.now(timezone.utc)
        first_seen = now - timedelta(days=14)
        last_updated = now - timedelta(days=7)  # Exactly 7 days
        
        state = determine_lifecycle_state(
            article_count=20,
            mention_velocity=0.1,
            first_seen=first_seen,
            last_updated=last_updated
        )
        
        assert state == 'dormant'
    
    def test_recency_overrides_activity(self):
        """Test that recency (cooling/dormant) takes priority over activity level."""
        now = datetime.now(timezone.utc)
        first_seen = now - timedelta(days=20)
        last_updated = now - timedelta(days=10)  # Dormant
        
        # Even with high article count and velocity, should be dormant
        state = determine_lifecycle_state(
            article_count=50,
            mention_velocity=10.0,
            first_seen=first_seen,
            last_updated=last_updated
        )
        
        assert state == 'dormant'
    
    def test_recent_update_with_low_activity(self):
        """Test that recent updates prevent cooling/dormant states."""
        now = datetime.now(timezone.utc)
        first_seen = now - timedelta(days=10)
        last_updated = now - timedelta(hours=2)  # Very recent
        
        # Low activity but recent update = emerging
        state = determine_lifecycle_state(
            article_count=2,
            mention_velocity=0.2,
            first_seen=first_seen,
            last_updated=last_updated
        )
        
        assert state == 'emerging'


class TestLifecycleStateIntegration:
    """Integration tests for lifecycle_state in detect_narratives."""
    
    @pytest.mark.asyncio
    async def test_new_narrative_includes_lifecycle_state(self):
        """Test that newly created narratives include lifecycle_state field."""
        with patch("crypto_news_aggregator.services.narrative_service.backfill_narratives_for_recent_articles") as mock_backfill, \
             patch("crypto_news_aggregator.services.narrative_service.mongo_manager") as mock_mongo, \
             patch("crypto_news_aggregator.services.narrative_service.cluster_by_narrative_salience") as mock_cluster, \
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
            
            # Mock narratives collection for find_matching_narrative
            class MockNarrativesCursor:
                async def to_list(self, length):
                    return []  # No existing narratives
            
            mock_narratives_collection.find.return_value = MockNarrativesCursor()
            
            # Track insert_one calls
            inserted_docs = []
            async def mock_insert_one(doc):
                inserted_docs.append(doc)
                return MagicMock(inserted_id="narrative123")
            
            mock_narratives_collection.insert_one = mock_insert_one
            
            # Mock articles with narrative data
            now = datetime.now(timezone.utc)
            sample_articles = [
                {
                    "_id": f"article{i}",
                    "title": f"Article {i}",
                    "published_at": now - timedelta(hours=i),
                    "narrative_summary": {"actions": ["test"]},
                    "actors": ["Bitcoin", "Ethereum"],
                    "actor_salience": {"Bitcoin": 5, "Ethereum": 4},
                    "nucleus_entity": "Bitcoin"
                }
                for i in range(5)
            ]
            
            # Mock cursor
            class MockCursor:
                async def to_list(self, length):
                    return sample_articles
            
            mock_articles_collection.find.return_value = MockCursor()
            
            # Mock clustering - return one cluster
            cluster = sample_articles.copy()
            cluster.append({"article_ids": [f"article{i}" for i in range(5)]})
            mock_cluster.return_value = [cluster]
            
            # Mock narrative generation
            mock_generate.return_value = {
                "title": "Bitcoin Ecosystem Growth",
                "summary": "Bitcoin adoption accelerates.",
                "actors": ["Bitcoin", "Ethereum"],
                "nucleus_entity": "Bitcoin",
                "article_ids": [f"article{i}" for i in range(5)],
                "article_count": 5,
                "entity_relationships": []
            }
            
            # Detect narratives
            narratives = await detect_narratives(hours=48, min_articles=3, use_salience_clustering=True)
            
            # Verify lifecycle_state was included
            assert len(narratives) > 0
            narrative = narratives[0]
            assert "lifecycle_state" in narrative
            assert narrative["lifecycle_state"] in ['emerging', 'rising', 'hot', 'cooling', 'dormant']
            
            # Verify database insert included lifecycle_state
            assert len(inserted_docs) > 0
            inserted_doc = inserted_docs[0]
            assert "lifecycle_state" in inserted_doc
            assert inserted_doc["lifecycle_state"] in ['emerging', 'rising', 'hot', 'cooling', 'dormant']
    
    @pytest.mark.asyncio
    async def test_updated_narrative_recalculates_lifecycle_state(self):
        """Test that updating existing narratives recalculates lifecycle_state."""
        with patch("crypto_news_aggregator.services.narrative_service.backfill_narratives_for_recent_articles") as mock_backfill, \
             patch("crypto_news_aggregator.services.narrative_service.mongo_manager") as mock_mongo, \
             patch("crypto_news_aggregator.services.narrative_service.cluster_by_narrative_salience") as mock_cluster, \
             patch("crypto_news_aggregator.services.narrative_service.generate_narrative_from_cluster") as mock_generate:
            
            # Mock backfill
            mock_backfill.return_value = 3
            
            # Mock database
            mock_db = MagicMock()
            mock_articles_collection = MagicMock()
            mock_narratives_collection = MagicMock()
            mock_db.articles = mock_articles_collection
            mock_db.narratives = mock_narratives_collection
            mock_mongo.get_async_database = AsyncMock(return_value=mock_db)
            
            # Mock existing narrative (matching)
            now = datetime.now(timezone.utc)
            existing_narrative = {
                "_id": "existing123",
                "title": "Bitcoin Growth",
                "article_ids": ["article1", "article2"],
                "article_count": 2,
                "first_seen": now - timedelta(days=5),
                "last_updated": now - timedelta(days=2),
                "lifecycle_state": "emerging",
                "status": "emerging",
                "fingerprint": {
                    "nucleus_entity": "Bitcoin",
                    "top_actors": ["Bitcoin"],
                    "key_actions": []
                }
            }
            
            # Mock narratives collection for find_matching_narrative
            class MockNarrativesCursor:
                async def to_list(self, length):
                    return [existing_narrative]
            
            mock_narratives_collection.find.return_value = MockNarrativesCursor()
            
            # Track update_one calls
            updated_docs = []
            async def mock_update_one(filter_query, update_query):
                updated_docs.append(update_query.get('$set', {}))
                return MagicMock()
            
            mock_narratives_collection.update_one = mock_update_one
            
            # Mock articles
            sample_articles = [
                {
                    "_id": f"article{i}",
                    "title": f"Article {i}",
                    "published_at": now - timedelta(hours=i),
                    "narrative_summary": {"actions": ["test"]},
                    "actors": ["Bitcoin"],
                    "actor_salience": {"Bitcoin": 5},
                    "nucleus_entity": "Bitcoin"
                }
                for i in range(3, 6)  # New articles
            ]
            
            # Mock cursor
            class MockCursor:
                async def to_list(self, length):
                    return sample_articles
            
            mock_articles_collection.find.return_value = MockCursor()
            
            # Mock clustering - cluster should be a dict with article_ids
            cluster = {
                "article_ids": ["article3", "article4", "article5"],
                "articles": sample_articles
            }
            mock_cluster.return_value = [sample_articles]  # cluster_by_narrative_salience returns list of article lists
            
            # Mock narrative generation
            mock_generate.return_value = {
                "title": "Bitcoin Growth",
                "summary": "Bitcoin continues to grow.",
                "actors": ["Bitcoin"],
                "nucleus_entity": "Bitcoin",
                "article_ids": ["article3", "article4", "article5"],
                "article_count": 3,
                "entity_relationships": []
            }
            
            # Detect narratives
            narratives = await detect_narratives(hours=48, min_articles=3, use_salience_clustering=True)
            
            # Verify update included recalculated lifecycle_state
            assert len(updated_docs) > 0
            update_doc = updated_docs[0]
            assert "lifecycle_state" in update_doc
            # Should be recalculated based on new article count and timing
            assert update_doc["lifecycle_state"] in ['emerging', 'rising', 'hot', 'cooling', 'dormant']
    
    @pytest.mark.asyncio
    async def test_theme_based_narratives_include_lifecycle_state(self):
        """Test that theme-based narratives also include lifecycle_state."""
        with patch("crypto_news_aggregator.services.narrative_service.backfill_themes_for_recent_articles") as mock_backfill, \
             patch("crypto_news_aggregator.services.narrative_service.get_articles_by_theme") as mock_get_articles, \
             patch("crypto_news_aggregator.services.narrative_service.extract_entities_from_articles") as mock_extract, \
             patch("crypto_news_aggregator.services.narrative_service.generate_narrative_from_theme") as mock_generate, \
             patch("crypto_news_aggregator.services.narrative_service.upsert_narrative") as mock_upsert, \
             patch("crypto_news_aggregator.services.narrative_service.mongo_manager") as mock_mongo:
            
            # Mock backfill
            mock_backfill.return_value = 5
            
            # Mock database
            mock_db = MagicMock()
            mock_collection = MagicMock()
            mock_db.narratives = mock_collection
            mock_mongo.get_async_database = AsyncMock(return_value=mock_db)
            
            # Mock cursor for existing narratives
            class MockCursor:
                def __aiter__(self):
                    return self
                
                async def __anext__(self):
                    raise StopAsyncIteration
            
            mock_collection.find.return_value = MockCursor()
            
            # Mock articles
            now = datetime.now(timezone.utc)
            sample_articles = [
                {
                    "_id": f"article{i}",
                    "title": f"Regulatory Article {i}",
                    "published_at": now - timedelta(hours=i),
                    "themes": ["regulatory"]
                }
                for i in range(5)
            ]
            
            # Mock get_articles_by_theme
            def mock_get_by_theme(theme, hours, min_articles):
                if theme == "regulatory":
                    return sample_articles
                return None
            
            mock_get_articles.side_effect = mock_get_by_theme
            
            # Mock entity extraction
            mock_extract.return_value = ["SEC", "Coinbase"]
            
            # Mock narrative generation
            mock_generate.return_value = {
                "title": "SEC Regulatory Actions",
                "summary": "The SEC intensifies enforcement."
            }
            
            # Track upsert calls
            upsert_calls = []
            async def mock_upsert_fn(**kwargs):
                upsert_calls.append(kwargs)
                return "narrative123"
            
            mock_upsert.side_effect = mock_upsert_fn
            
            # Detect narratives (theme-based)
            narratives = await detect_narratives(hours=48, min_articles=3, use_salience_clustering=False)
            
            # Verify lifecycle_state in returned narratives
            assert len(narratives) > 0
            narrative = narratives[0]
            assert "lifecycle_state" in narrative
            assert narrative["lifecycle_state"] in ['emerging', 'rising', 'hot', 'cooling', 'dormant']
            
            # Verify lifecycle_state was passed to upsert_narrative
            assert len(upsert_calls) > 0
            upsert_call = upsert_calls[0]
            assert "lifecycle_state" in upsert_call
            assert upsert_call["lifecycle_state"] in ['emerging', 'rising', 'hot', 'cooling', 'dormant']
