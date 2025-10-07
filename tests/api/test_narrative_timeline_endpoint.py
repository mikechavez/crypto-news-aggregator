"""
Tests for narrative timeline API endpoint.

Tests the GET /api/v1/narratives/{id}/timeline endpoint.
"""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from bson import ObjectId


@pytest.fixture
def mock_timeline_data():
    """Sample timeline data for testing."""
    return [
        {
            "date": "2025-10-01",
            "article_count": 3,
            "entities": ["SEC", "Bitcoin"],
            "velocity": 1.5
        },
        {
            "date": "2025-10-02",
            "article_count": 5,
            "entities": ["SEC", "Bitcoin", "Coinbase"],
            "velocity": 2.5
        },
        {
            "date": "2025-10-03",
            "article_count": 7,
            "entities": ["SEC", "Bitcoin", "Coinbase", "Gary Gensler"],
            "velocity": 3.5
        }
    ]


class TestNarrativeTimelineEndpoint:
    """Test the narrative timeline API endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_timeline_success(self, mock_timeline_data):
        """Test successfully retrieving timeline data."""
        from crypto_news_aggregator.api.v1.endpoints.narratives import router
        from fastapi import FastAPI
        
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        
        narrative_id = str(ObjectId())
        
        with patch('crypto_news_aggregator.api.v1.endpoints.narratives.get_narrative_timeline') as mock_get:
            mock_get.return_value = mock_timeline_data
            
            response = client.get(f"/{narrative_id}/timeline")
            
            assert response.status_code == 200
            data = response.json()
            
            assert len(data) == 3
            assert data[0]["date"] == "2025-10-01"
            assert data[0]["article_count"] == 3
            assert data[0]["velocity"] == 1.5
            assert "SEC" in data[0]["entities"]
            
            assert data[2]["article_count"] == 7
            assert data[2]["velocity"] == 3.5
    
    @pytest.mark.asyncio
    async def test_get_timeline_not_found(self):
        """Test retrieving timeline for non-existent narrative."""
        from crypto_news_aggregator.api.v1.endpoints.narratives import router
        from fastapi import FastAPI
        
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        
        narrative_id = str(ObjectId())
        
        with patch('crypto_news_aggregator.api.v1.endpoints.narratives.get_narrative_timeline') as mock_get:
            mock_get.return_value = None
            
            response = client.get(f"/{narrative_id}/timeline")
            
            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_get_timeline_empty(self):
        """Test retrieving timeline when narrative has no timeline data."""
        from crypto_news_aggregator.api.v1.endpoints.narratives import router
        from fastapi import FastAPI
        
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        
        narrative_id = str(ObjectId())
        
        with patch('crypto_news_aggregator.api.v1.endpoints.narratives.get_narrative_timeline') as mock_get:
            mock_get.return_value = []
            
            response = client.get(f"/{narrative_id}/timeline")
            
            assert response.status_code == 200
            data = response.json()
            assert data == []
    
    @pytest.mark.asyncio
    async def test_get_timeline_database_error(self):
        """Test handling database errors gracefully."""
        from crypto_news_aggregator.api.v1.endpoints.narratives import router
        from fastapi import FastAPI
        
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        
        narrative_id = str(ObjectId())
        
        with patch('crypto_news_aggregator.api.v1.endpoints.narratives.get_narrative_timeline') as mock_get:
            mock_get.side_effect = Exception("Database connection failed")
            
            response = client.get(f"/{narrative_id}/timeline")
            
            assert response.status_code == 500
            assert "failed" in response.json()["detail"].lower()


class TestNarrativeResponseWithTimeline:
    """Test that active narratives endpoint includes timeline fields."""
    
    @pytest.mark.asyncio
    async def test_active_narratives_includes_timeline_fields(self):
        """Test that /active endpoint includes new timeline tracking fields."""
        from crypto_news_aggregator.api.v1.endpoints.narratives import router
        from fastapi import FastAPI
        from datetime import datetime, timezone
        
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        
        mock_narratives = [
            {
                "theme": "regulatory",
                "title": "SEC Enforcement Actions",
                "summary": "Test summary",
                "entities": ["SEC", "Bitcoin"],
                "article_count": 10,
                "mention_velocity": 3.5,
                "lifecycle": "hot",
                "first_seen": datetime.now(timezone.utc),
                "last_updated": datetime.now(timezone.utc),
                "days_active": 5,
                "peak_activity": {
                    "date": "2025-10-05",
                    "article_count": 12,
                    "velocity": 4.0
                },
                "timeline_data": [
                    {"date": "2025-10-01", "article_count": 3, "entities": ["SEC"], "velocity": 1.5},
                    {"date": "2025-10-02", "article_count": 5, "entities": ["SEC", "Bitcoin"], "velocity": 2.5}
                ]
            }
        ]
        
        with patch('crypto_news_aggregator.api.v1.endpoints.narratives.get_active_narratives') as mock_get:
            mock_get.return_value = mock_narratives
            
            with patch('crypto_news_aggregator.api.v1.endpoints.narratives.redis_client') as mock_redis:
                mock_redis.enabled = False
                
                response = client.get("/active?limit=10")
                
                assert response.status_code == 200
                data = response.json()
                
                assert len(data) == 1
                narrative = data[0]
                
                # Check timeline fields are present
                assert "days_active" in narrative
                assert narrative["days_active"] == 5
                
                assert "peak_activity" in narrative
                assert narrative["peak_activity"]["article_count"] == 12
                assert narrative["peak_activity"]["date"] == "2025-10-05"
    
    @pytest.mark.asyncio
    async def test_active_narratives_handles_missing_timeline_fields(self):
        """Test that endpoint handles narratives without timeline fields (backward compatibility)."""
        from crypto_news_aggregator.api.v1.endpoints.narratives import router
        from fastapi import FastAPI
        from datetime import datetime, timezone
        
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        
        # Old narrative without timeline fields
        mock_narratives = [
            {
                "theme": "regulatory",
                "title": "SEC Enforcement Actions",
                "summary": "Test summary",
                "entities": ["SEC", "Bitcoin"],
                "article_count": 10,
                "mention_velocity": 3.5,
                "lifecycle": "hot",
                "first_seen": datetime.now(timezone.utc),
                "last_updated": datetime.now(timezone.utc)
                # No days_active, peak_activity, or timeline_data
            }
        ]
        
        with patch('crypto_news_aggregator.api.v1.endpoints.narratives.get_active_narratives') as mock_get:
            mock_get.return_value = mock_narratives
            
            with patch('crypto_news_aggregator.api.v1.endpoints.narratives.redis_client') as mock_redis:
                mock_redis.enabled = False
                
                response = client.get("/active?limit=10")
                
                assert response.status_code == 200
                data = response.json()
                
                assert len(data) == 1
                narrative = data[0]
                
                # Check defaults are applied
                assert narrative["days_active"] == 1
                assert narrative["peak_activity"] is None
