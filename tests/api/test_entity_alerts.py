"""
Tests for entity alerts API endpoints.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient


@pytest.mark.asyncio
class TestEntityAlertsAPI:
    """Tests for entity alerts API endpoints."""
    
    async def test_get_recent_alerts_success(self, client: TestClient):
        """Test successful retrieval of recent alerts."""
        mock_alerts = [
            {
                "_id": "alert_1",
                "type": "NEW_ENTITY",
                "entity": "TEST_TOKEN",
                "entity_type": "ticker",
                "severity": "high",
                "signal_score": 8.0,
                "details": {"source_count": 5},
                "triggered_at": datetime.now(timezone.utc),
                "resolved_at": None
            },
            {
                "_id": "alert_2",
                "type": "VELOCITY_SPIKE",
                "entity": "SPIKE_TOKEN",
                "entity_type": "project",
                "severity": "medium",
                "signal_score": 7.0,
                "details": {"velocity": 15.0},
                "triggered_at": datetime.now(timezone.utc) - timedelta(hours=2),
                "resolved_at": None
            }
        ]
        
        with patch("crypto_news_aggregator.api.v1.endpoints.entity_alerts.get_recent_alerts", new_callable=AsyncMock) as mock_get_alerts:
            mock_get_alerts.return_value = mock_alerts
            
            response = client.get("/api/v1/entity-alerts/recent")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["type"] == "NEW_ENTITY"
            assert data[1]["type"] == "VELOCITY_SPIKE"
    
    async def test_get_recent_alerts_with_filters(self, client: TestClient):
        """Test retrieval with severity filter."""
        mock_alerts = [
            {
                "_id": "alert_1",
                "type": "NEW_ENTITY",
                "entity": "TEST_TOKEN",
                "entity_type": "ticker",
                "severity": "high",
                "signal_score": 8.0,
                "details": {},
                "triggered_at": datetime.now(timezone.utc),
                "resolved_at": None
            }
        ]
        
        with patch("crypto_news_aggregator.api.v1.endpoints.entity_alerts.get_recent_alerts", new_callable=AsyncMock) as mock_get_alerts:
            mock_get_alerts.return_value = mock_alerts
            
            response = client.get("/api/v1/entity-alerts/recent?severity=high&hours=12")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["severity"] == "high"
            
            # Verify the function was called with correct parameters
            mock_get_alerts.assert_called_once()
            call_kwargs = mock_get_alerts.call_args.kwargs
            assert call_kwargs["severity"] == "high"
            assert call_kwargs["hours"] == 12
    
    async def test_get_recent_alerts_empty(self, client: TestClient):
        """Test retrieval when no alerts exist."""
        with patch("crypto_news_aggregator.api.v1.endpoints.entity_alerts.get_recent_alerts", new_callable=AsyncMock) as mock_get_alerts:
            mock_get_alerts.return_value = []
            
            response = client.get("/api/v1/entity-alerts/recent")
            
            assert response.status_code == 200
            data = response.json()
            assert data == []
    
    async def test_get_recent_alerts_invalid_severity(self, client: TestClient):
        """Test that invalid severity parameter is rejected."""
        response = client.get("/api/v1/entity-alerts/recent?severity=invalid")
        
        assert response.status_code == 422  # Validation error
    
    async def test_get_recent_alerts_invalid_hours(self, client: TestClient):
        """Test that invalid hours parameter is rejected."""
        response = client.get("/api/v1/entity-alerts/recent?hours=200")
        
        assert response.status_code == 422  # Validation error
    
    async def test_get_alert_stats_success(self, client: TestClient):
        """Test successful retrieval of alert statistics."""
        mock_alerts = [
            {
                "_id": "alert_1",
                "type": "NEW_ENTITY",
                "entity": "TEST_TOKEN",
                "entity_type": "ticker",
                "severity": "high",
                "signal_score": 8.0,
                "details": {},
                "triggered_at": datetime.now(timezone.utc),
                "resolved_at": None
            },
            {
                "_id": "alert_2",
                "type": "VELOCITY_SPIKE",
                "entity": "SPIKE_TOKEN",
                "entity_type": "project",
                "severity": "medium",
                "signal_score": 7.0,
                "details": {},
                "triggered_at": datetime.now(timezone.utc) - timedelta(hours=2),
                "resolved_at": datetime.now(timezone.utc)
            },
            {
                "_id": "alert_3",
                "type": "NEW_ENTITY",
                "entity": "ANOTHER_TOKEN",
                "entity_type": "ticker",
                "severity": "high",
                "signal_score": 9.0,
                "details": {},
                "triggered_at": datetime.now(timezone.utc) - timedelta(hours=5),
                "resolved_at": None
            }
        ]
        
        with patch("crypto_news_aggregator.api.v1.endpoints.entity_alerts.get_recent_alerts", new_callable=AsyncMock) as mock_get_alerts:
            mock_get_alerts.return_value = mock_alerts
            
            response = client.get("/api/v1/entity-alerts/stats")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["total"] == 3
            assert data["unresolved"] == 2
            assert data["resolved"] == 1
            assert data["by_type"]["NEW_ENTITY"] == 2
            assert data["by_type"]["VELOCITY_SPIKE"] == 1
            assert data["by_severity"]["high"] == 2
            assert data["by_severity"]["medium"] == 1
            assert data["by_entity_type"]["ticker"] == 2
            assert data["by_entity_type"]["project"] == 1
    
    async def test_get_alert_stats_empty(self, client: TestClient):
        """Test statistics when no alerts exist."""
        with patch("crypto_news_aggregator.api.v1.endpoints.entity_alerts.get_recent_alerts", new_callable=AsyncMock) as mock_get_alerts:
            mock_get_alerts.return_value = []
            
            response = client.get("/api/v1/entity-alerts/stats")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["total"] == 0
            assert data["unresolved"] == 0
            assert data["resolved"] == 0
            assert data["by_type"] == {}
            assert data["by_severity"] == {}
            assert data["by_entity_type"] == {}
    
    async def test_cache_behavior(self, client: TestClient):
        """Test that caching works correctly."""
        mock_alerts = [
            {
                "_id": "alert_1",
                "type": "NEW_ENTITY",
                "entity": "TEST_TOKEN",
                "entity_type": "ticker",
                "severity": "high",
                "signal_score": 8.0,
                "details": {},
                "triggered_at": datetime.now(timezone.utc),
                "resolved_at": None
            }
        ]
        
        with patch("crypto_news_aggregator.api.v1.endpoints.entity_alerts.get_recent_alerts", new_callable=AsyncMock) as mock_get_alerts:
            mock_get_alerts.return_value = mock_alerts
            
            # First request
            response1 = client.get("/api/v1/entity-alerts/recent")
            assert response1.status_code == 200
            
            # Second request (should use cache)
            response2 = client.get("/api/v1/entity-alerts/recent")
            assert response2.status_code == 200
            
            # Database should only be called once due to caching
            assert mock_get_alerts.call_count == 1


@pytest.fixture
def client():
    """Create a test client for the API."""
    from crypto_news_aggregator.main import app
    from fastapi.testclient import TestClient
    
    return TestClient(app)
