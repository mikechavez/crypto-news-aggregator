"""
Tests for narrative timeline tracking functionality.

Tests the daily snapshot system that tracks narrative evolution over time.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from crypto_news_aggregator.db.operations.narratives import (
    upsert_narrative,
    get_narrative_timeline,
    _should_append_timeline_snapshot,
    _calculate_days_active
)


class TestTimelineHelpers:
    """Test helper functions for timeline tracking."""
    
    def test_calculate_days_active_same_day(self):
        """Test days_active calculation for same day."""
        now = datetime.now(timezone.utc)
        days = _calculate_days_active(now)
        assert days == 1
    
    def test_calculate_days_active_multiple_days(self):
        """Test days_active calculation for multiple days."""
        five_days_ago = datetime.now(timezone.utc) - timedelta(days=5)
        days = _calculate_days_active(five_days_ago)
        assert days == 6  # 5 full days + today
    
    def test_should_append_no_existing(self):
        """Test should append when no existing narrative."""
        assert _should_append_timeline_snapshot(None) is True
    
    def test_should_append_no_timeline_data(self):
        """Test should append when no timeline data exists."""
        existing = {"theme": "test"}
        assert _should_append_timeline_snapshot(existing) is True
    
    def test_should_append_empty_timeline(self):
        """Test should append when timeline is empty."""
        existing = {"timeline_data": []}
        assert _should_append_timeline_snapshot(existing) is True
    
    def test_should_append_different_day(self):
        """Test should append when last snapshot is from different day."""
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date().isoformat()
        existing = {
            "timeline_data": [
                {"date": yesterday, "article_count": 5}
            ]
        }
        assert _should_append_timeline_snapshot(existing) is True
    
    def test_should_not_append_same_day(self):
        """Test should not append when last snapshot is from today."""
        today = datetime.now(timezone.utc).date().isoformat()
        existing = {
            "timeline_data": [
                {"date": today, "article_count": 5}
            ]
        }
        assert _should_append_timeline_snapshot(existing) is False


class TestUpsertNarrativeTimeline:
    """Test timeline tracking in upsert_narrative."""
    
    @pytest.mark.asyncio
    async def test_create_narrative_with_timeline(self):
        """Test creating new narrative includes initial timeline snapshot."""
        mock_db = MagicMock()
        mock_collection = AsyncMock()
        mock_db.narratives = mock_collection
        
        # No existing narrative
        mock_collection.find_one = AsyncMock(return_value=None)
        mock_collection.insert_one = AsyncMock(return_value=MagicMock(inserted_id="test_id"))
        
        with patch('crypto_news_aggregator.db.operations.narratives.mongo_manager') as mock_mongo:
            mock_mongo.get_async_database = AsyncMock(return_value=mock_db)
            
            narrative_id = await upsert_narrative(
                theme="regulatory",
                title="Test Narrative",
                summary="Test summary",
                entities=["SEC", "Bitcoin"],
                article_ids=["1", "2", "3"],
                article_count=3,
                mention_velocity=1.5,
                lifecycle="emerging"
            )
            
            # Verify insert was called
            assert mock_collection.insert_one.called
            call_args = mock_collection.insert_one.call_args[0][0]
            
            # Check timeline_data was created
            assert "timeline_data" in call_args
            assert len(call_args["timeline_data"]) == 1
            
            snapshot = call_args["timeline_data"][0]
            assert "date" in snapshot
            assert snapshot["article_count"] == 3
            assert snapshot["entities"] == ["SEC", "Bitcoin"]
            assert snapshot["velocity"] == 1.5
            
            # Check peak_activity was created
            assert "peak_activity" in call_args
            assert call_args["peak_activity"]["article_count"] == 3
            
            # Check days_active was set
            assert "days_active" in call_args
            assert call_args["days_active"] == 1
    
    @pytest.mark.asyncio
    async def test_update_narrative_appends_timeline(self):
        """Test updating narrative appends new timeline snapshot for new day."""
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date().isoformat()
        first_seen = datetime.now(timezone.utc) - timedelta(days=1)
        
        existing_narrative = {
            "_id": "test_id",
            "theme": "regulatory",
            "first_seen": first_seen,
            "timeline_data": [
                {
                    "date": yesterday,
                    "article_count": 3,
                    "entities": ["SEC"],
                    "velocity": 1.5
                }
            ],
            "peak_activity": {
                "date": yesterday,
                "article_count": 3,
                "velocity": 1.5
            }
        }
        
        mock_db = MagicMock()
        mock_collection = AsyncMock()
        mock_db.narratives = mock_collection
        
        mock_collection.find_one = AsyncMock(return_value=existing_narrative)
        mock_collection.update_one = AsyncMock()
        
        with patch('crypto_news_aggregator.db.operations.narratives.mongo_manager') as mock_mongo:
            mock_mongo.get_async_database = AsyncMock(return_value=mock_db)
            
            await upsert_narrative(
                theme="regulatory",
                title="Updated Narrative",
                summary="Updated summary",
                entities=["SEC", "Bitcoin", "Coinbase"],
                article_ids=["1", "2", "3", "4", "5"],
                article_count=5,
                mention_velocity=2.5,
                lifecycle="hot"
            )
            
            # Verify update was called
            assert mock_collection.update_one.called
            update_data = mock_collection.update_one.call_args[0][1]["$set"]
            
            # Check timeline_data was appended
            assert len(update_data["timeline_data"]) == 2
            new_snapshot = update_data["timeline_data"][1]
            assert new_snapshot["article_count"] == 5
            assert new_snapshot["velocity"] == 2.5
            
            # Check peak_activity was updated (5 > 3)
            assert update_data["peak_activity"]["article_count"] == 5
            
            # Check days_active was calculated
            assert update_data["days_active"] == 2
    
    @pytest.mark.asyncio
    async def test_update_narrative_same_day_replaces_snapshot(self):
        """Test updating narrative on same day replaces last snapshot."""
        today = datetime.now(timezone.utc).date().isoformat()
        first_seen = datetime.now(timezone.utc)
        
        existing_narrative = {
            "_id": "test_id",
            "theme": "regulatory",
            "first_seen": first_seen,
            "timeline_data": [
                {
                    "date": today,
                    "article_count": 3,
                    "entities": ["SEC"],
                    "velocity": 1.5
                }
            ],
            "peak_activity": {
                "date": today,
                "article_count": 3,
                "velocity": 1.5
            }
        }
        
        mock_db = MagicMock()
        mock_collection = AsyncMock()
        mock_db.narratives = mock_collection
        
        mock_collection.find_one = AsyncMock(return_value=existing_narrative)
        mock_collection.update_one = AsyncMock()
        
        with patch('crypto_news_aggregator.db.operations.narratives.mongo_manager') as mock_mongo:
            mock_mongo.get_async_database = AsyncMock(return_value=mock_db)
            
            await upsert_narrative(
                theme="regulatory",
                title="Updated Narrative",
                summary="Updated summary",
                entities=["SEC", "Bitcoin"],
                article_ids=["1", "2", "3", "4"],
                article_count=4,
                mention_velocity=2.0,
                lifecycle="emerging"
            )
            
            # Verify update was called
            assert mock_collection.update_one.called
            update_data = mock_collection.update_one.call_args[0][1]["$set"]
            
            # Check timeline_data still has only 1 entry (replaced, not appended)
            assert len(update_data["timeline_data"]) == 1
            snapshot = update_data["timeline_data"][0]
            assert snapshot["article_count"] == 4
            assert snapshot["velocity"] == 2.0
    
    @pytest.mark.asyncio
    async def test_peak_activity_not_updated_if_lower(self):
        """Test peak_activity is not updated if current count is lower."""
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date().isoformat()
        first_seen = datetime.now(timezone.utc) - timedelta(days=1)
        
        existing_narrative = {
            "_id": "test_id",
            "theme": "regulatory",
            "first_seen": first_seen,
            "timeline_data": [
                {
                    "date": yesterday,
                    "article_count": 10,
                    "entities": ["SEC"],
                    "velocity": 5.0
                }
            ],
            "peak_activity": {
                "date": yesterday,
                "article_count": 10,
                "velocity": 5.0
            }
        }
        
        mock_db = MagicMock()
        mock_collection = AsyncMock()
        mock_db.narratives = mock_collection
        
        mock_collection.find_one = AsyncMock(return_value=existing_narrative)
        mock_collection.update_one = AsyncMock()
        
        with patch('crypto_news_aggregator.db.operations.narratives.mongo_manager') as mock_mongo:
            mock_mongo.get_async_database = AsyncMock(return_value=mock_db)
            
            await upsert_narrative(
                theme="regulatory",
                title="Updated Narrative",
                summary="Updated summary",
                entities=["SEC"],
                article_ids=["1", "2", "3"],
                article_count=3,
                mention_velocity=1.5,
                lifecycle="declining"
            )
            
            # Verify update was called
            assert mock_collection.update_one.called
            update_data = mock_collection.update_one.call_args[0][1]["$set"]
            
            # Check peak_activity was NOT updated (still 10)
            assert update_data["peak_activity"]["article_count"] == 10
            assert update_data["peak_activity"]["date"] == yesterday


class TestGetNarrativeTimeline:
    """Test retrieving narrative timeline data."""
    
    @pytest.mark.asyncio
    async def test_get_timeline_success(self):
        """Test successfully retrieving timeline data."""
        from bson import ObjectId
        
        narrative_id = str(ObjectId())
        timeline_data = [
            {"date": "2025-10-01", "article_count": 3, "entities": ["SEC"], "velocity": 1.5},
            {"date": "2025-10-02", "article_count": 5, "entities": ["SEC", "Bitcoin"], "velocity": 2.5}
        ]
        
        mock_db = MagicMock()
        mock_collection = AsyncMock()
        mock_db.narratives = mock_collection
        
        mock_collection.find_one = AsyncMock(return_value={
            "_id": ObjectId(narrative_id),
            "timeline_data": timeline_data
        })
        
        with patch('crypto_news_aggregator.db.operations.narratives.mongo_manager') as mock_mongo:
            mock_mongo.get_async_database = AsyncMock(return_value=mock_db)
            
            result = await get_narrative_timeline(narrative_id)
            
            assert result == timeline_data
            assert len(result) == 2
    
    @pytest.mark.asyncio
    async def test_get_timeline_not_found(self):
        """Test retrieving timeline for non-existent narrative."""
        from bson import ObjectId
        
        narrative_id = str(ObjectId())
        
        mock_db = MagicMock()
        mock_collection = AsyncMock()
        mock_db.narratives = mock_collection
        
        mock_collection.find_one = AsyncMock(return_value=None)
        
        with patch('crypto_news_aggregator.db.operations.narratives.mongo_manager') as mock_mongo:
            mock_mongo.get_async_database = AsyncMock(return_value=mock_db)
            
            result = await get_narrative_timeline(narrative_id)
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_get_timeline_empty(self):
        """Test retrieving timeline when no timeline_data exists."""
        from bson import ObjectId
        
        narrative_id = str(ObjectId())
        
        mock_db = MagicMock()
        mock_collection = AsyncMock()
        mock_db.narratives = mock_collection
        
        mock_collection.find_one = AsyncMock(return_value={
            "_id": ObjectId(narrative_id),
            "theme": "regulatory"
            # No timeline_data field
        })
        
        with patch('crypto_news_aggregator.db.operations.narratives.mongo_manager') as mock_mongo:
            mock_mongo.get_async_database = AsyncMock(return_value=mock_db)
            
            result = await get_narrative_timeline(narrative_id)
            
            assert result == []
