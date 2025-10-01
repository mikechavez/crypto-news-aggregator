"""
API tests for price endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from src.crypto_news_aggregator.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_price_service():
    """Mock the price service for testing."""
    with patch(
        "src.crypto_news_aggregator.api.v1.endpoints.price.get_price_service"
    ) as mock:
        yield mock


@pytest.fixture
def mock_auth():
    """Mock the authentication for testing."""
    with patch("src.crypto_news_aggregator.api.v1.endpoints.price.get_api_key") as mock:
        mock.return_value = "test-api-key"
        yield mock


class TestPriceEndpoints:
    """Test cases for price API endpoints."""

    def test_get_current_bitcoin_price_success(
        self, client, mock_price_service, mock_auth
    ):
        """Test successful Bitcoin price retrieval."""
        # Mock the price service response
        mock_service = mock_price_service.return_value
        mock_service.get_bitcoin_price.return_value = {
            "price": 50000.0,
            "change_24h": 2.5,
            "timestamp": "2023-01-01T12:00:00Z",
        }

        response = client.get("/api/v1/price/bitcoin/current")

        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "BTC"
        assert data["price_usd"] == 50000.0
        assert "last_updated" in data

    def test_get_current_bitcoin_price_service_error(
        self, client, mock_price_service, mock_auth
    ):
        """Test Bitcoin price retrieval when service fails."""
        mock_service = mock_price_service.return_value
        mock_service.get_bitcoin_price.return_value = None

        response = client.get("/api/v1/price/bitcoin/current")

        assert response.status_code == 503
        assert "Unable to fetch Bitcoin price" in response.json()["detail"]

    def test_get_bitcoin_price_history_success(
        self, client, mock_price_service, mock_auth
    ):
        """Test successful Bitcoin price history retrieval."""
        mock_service = mock_price_service.return_value
        mock_service.get_recent_price_history.return_value = [
            {"price": 50000.0, "timestamp": "2023-01-01T12:00:00"},
            {"price": 50100.0, "timestamp": "2023-01-01T13:00:00"},
        ]

        response = client.get("/api/v1/price/bitcoin/history")

        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "BTC"
        assert len(data["prices"]) == 2
        assert data["timeframe_hours"] == 24

    def test_get_bitcoin_price_history_invalid_hours(
        self, client, mock_price_service, mock_auth
    ):
        """Test Bitcoin price history with invalid hours parameter."""
        response = client.get("/api/v1/price/bitcoin/history?hours=200")

        assert response.status_code == 400
        assert "Hours must be between 1 and 168" in response.json()["detail"]

    def test_get_market_analysis_bitcoin_success(
        self, client, mock_price_service, mock_auth
    ):
        """Test successful Bitcoin market analysis."""
        mock_service = mock_price_service.return_value
        mock_service.generate_market_analysis_commentary.return_value = (
            "Bitcoin analysis: Trading at $50,000 with strong momentum."
        )

        response = client.get("/api/v1/price/analysis/bitcoin")

        assert response.status_code == 200
        data = response.json()
        assert data["coin_id"] == "bitcoin"
        assert "analysis" in data
        assert "generated_at" in data

    def test_get_market_analysis_ethereum_success(
        self, client, mock_price_service, mock_auth
    ):
        """Test successful Ethereum market analysis."""
        mock_service = mock_price_service.return_value
        mock_service.generate_market_analysis_commentary.return_value = (
            "Ethereum analysis: Trading at $3,000 with moderate growth."
        )

        response = client.get("/api/v1/price/analysis/ethereum")

        assert response.status_code == 200
        data = response.json()
        assert data["coin_id"] == "ethereum"
        assert "analysis" in data

    def test_get_market_analysis_service_error(
        self, client, mock_price_service, mock_auth
    ):
        """Test market analysis when service fails."""
        mock_service = mock_price_service.return_value
        mock_service.generate_market_analysis_commentary.side_effect = Exception(
            "Service error"
        )

        response = client.get("/api/v1/price/analysis/bitcoin")

        assert response.status_code == 503
        assert "Unable to generate market analysis" in response.json()["detail"]

    def test_bitcoin_price_movement_check(self, client, mock_price_service, mock_auth):
        """Test Bitcoin price movement check."""
        mock_service = mock_price_service.return_value
        mock_service.check_price_movement.return_value = None

        response = client.get("/api/v1/price/bitcoin/check-movement")

        assert response.status_code == 200
        data = response.json()
        assert data["alert"] is False
        assert "No significant price movement detected" in data["message"]
