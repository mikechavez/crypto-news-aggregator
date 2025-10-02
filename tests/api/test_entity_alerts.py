"""
Smoke tests for entity alerts API endpoints.
"""

import pytest
from fastapi.testclient import TestClient


class TestEntityAlertsAPI:
    """Smoke tests for entity alerts API endpoints."""
    
    def test_get_recent_alerts_endpoint(self, client: TestClient):
        """Test that the recent alerts endpoint works."""
        response = client.get("/api/v1/entity-alerts/recent")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_recent_alerts_with_severity_filter(self, client: TestClient):
        """Test retrieval with severity filter."""
        response = client.get("/api/v1/entity-alerts/recent?severity=high&hours=12")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_recent_alerts_invalid_severity(self, client: TestClient):
        """Test that invalid severity parameter is rejected."""
        response = client.get("/api/v1/entity-alerts/recent?severity=invalid")
        assert response.status_code == 422  # Validation error
    
    def test_get_recent_alerts_invalid_hours(self, client: TestClient):
        """Test that invalid hours parameter is rejected."""
        response = client.get("/api/v1/entity-alerts/recent?hours=200")
        assert response.status_code == 422  # Validation error
    
    def test_get_alert_stats_endpoint(self, client: TestClient):
        """Test that the stats endpoint works."""
        response = client.get("/api/v1/entity-alerts/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "unresolved" in data
        assert "resolved" in data
        assert "by_type" in data
        assert "by_severity" in data
        assert "by_entity_type" in data


@pytest.fixture
def client():
    """Create a test client for the API."""
    from crypto_news_aggregator.main import app
    from fastapi.testclient import TestClient
    
    return TestClient(app)
