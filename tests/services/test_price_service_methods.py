"""
Unit tests for price service methods.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timezone, timedelta

from src.crypto_news_aggregator.services.price_service import CoinGeckoPriceService


@pytest.fixture
def price_service():
    """Create a price service instance for testing."""
    return CoinGeckoPriceService()


class TestPriceService:
    """Test cases for price service methods."""

    @pytest.mark.asyncio
    async def test_get_bitcoin_price_success(self, price_service):
        """Test successful Bitcoin price retrieval."""
        with patch.object(price_service, "get_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value = mock_session

            # Mock successful API response
            mock_response = AsyncMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json = AsyncMock(
                return_value={"bitcoin": {"usd": 50000.0, "usd_24h_change": 2.5}}
            )
            mock_session.get.return_value.__aenter__.return_value = mock_response

            result = await price_service.get_bitcoin_price()

            assert result["price"] == 50000.0
            assert result["change_24h"] == 2.5
            assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_get_bitcoin_price_api_error(self, price_service):
        """Test Bitcoin price retrieval with API error."""
        with patch.object(price_service, "get_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value = mock_session

            # Mock API error
            mock_response = AsyncMock()
            mock_response.raise_for_status.side_effect = Exception("API Error")
            mock_session.get.return_value.__aenter__.return_value = mock_response

            with pytest.raises(Exception):
                await price_service.get_bitcoin_price()

    @pytest.mark.asyncio
    async def test_get_prices_success(self, price_service):
        """Test successful price retrieval for multiple coins."""
        with patch.object(price_service, "get_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value = mock_session

            mock_response = AsyncMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json = AsyncMock(
                return_value={
                    "bitcoin": {"usd": 50000.0, "usd_24h_change": 2.5},
                    "ethereum": {"usd": 3000.0, "usd_24h_change": 1.8},
                }
            )
            mock_session.get.return_value.__aenter__.return_value = mock_response

            result = await price_service.get_prices(["bitcoin", "ethereum"])

            assert result["bitcoin"]["price"] == 50000.0
            assert result["ethereum"]["price"] == 3000.0

    @pytest.mark.asyncio
    async def test_get_markets_data_success(self, price_service):
        """Test successful market data retrieval."""
        with patch.object(price_service, "get_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value = mock_session

            mock_response = AsyncMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json = AsyncMock(
                return_value=[
                    {
                        "id": "bitcoin",
                        "current_price": 50000.0,
                        "price_change_percentage_24h": 2.5,
                        "market_cap": 1000000000000,
                        "total_volume": 50000000000,
                        "high_24h": 51000.0,
                        "low_24h": 49000.0,
                    }
                ]
            )
            mock_session.get.return_value.__aenter__.return_value = mock_response

            result = await price_service.get_markets_data(["bitcoin"])

            assert result["bitcoin"]["current_price"] == 50000.0
            assert result["bitcoin"]["price_change_percentage_24h"] == 2.5

    @pytest.mark.asyncio
    async def test_get_global_market_data_success(self, price_service):
        """Test successful global market data retrieval."""
        with patch.object(price_service, "get_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value = mock_session

            mock_response = AsyncMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json = AsyncMock(
                return_value={
                    "data": {
                        "total_market_cap": {"usd": 2500000000000},
                        "total_volume": {"usd": 150000000000},
                        "market_cap_percentage": {"btc": 45.0, "eth": 18.0},
                    }
                }
            )
            mock_session.get.return_value.__aenter__.return_value = mock_response

            result = await price_service.get_global_market_data()

            assert result["total_market_cap"]["usd"] == 2500000000000
            assert result["market_cap_percentage"]["btc"] == 45.0

    @pytest.mark.asyncio
    async def test_get_historical_prices_success(self, price_service):
        """Test successful historical price data retrieval."""
        with patch.object(price_service, "get_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value = mock_session

            mock_response = AsyncMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json = AsyncMock(
                return_value={
                    "prices": [[1609459200000, 50000.0], [1609545600000, 50100.0]],
                    "total_volumes": [
                        [1609459200000, 50000000000],
                        [1609545600000, 51000000000],
                    ],
                }
            )
            mock_session.get.return_value.__aenter__.return_value = mock_response

            result = await price_service.get_historical_prices("bitcoin", days=7)

            assert "prices" in result
            assert "volumes" in result
            assert len(result["prices"]) == 2

    def test_format_percent(self, price_service):
        """Test percentage formatting."""
        assert price_service._format_percent(2.5) == "+2.50%"
        assert price_service._format_percent(-1.8) == "-1.80%"
        assert price_service._format_percent(None) == "N/A"

    def test_trend_momentum_commentary(self, price_service):
        """Test trend and momentum commentary generation."""
        trend, momentum = price_service._get_trend_momentum_commentary(1.0, 2.5, 3.0)
        assert trend in [
            "strong bullish momentum",
            "strong bearish momentum",
            "a potential bullish reversal",
            "a potential bearish reversal",
            "a consolidation phase",
            "mixed signals",
        ]
        assert momentum in ["high", "moderate", "low"]

    @pytest.mark.asyncio
    async def test_calculate_price_change_percent(self, price_service):
        """Test price change percentage calculation."""
        result = await price_service.calculate_price_change_percent(51000.0, 50000.0)
        assert result == 2.0

        result = await price_service.calculate_price_change_percent(50000.0, 51000.0)
        assert result == -1.9607843137254901

    @pytest.mark.asyncio
    async def test_should_trigger_alert(self, price_service):
        """Test alert triggering logic."""
        should_alert, change = await price_service.should_trigger_alert(
            51000.0, 50000.0, 2.0
        )
        assert should_alert is True
        assert change == 2.0

        should_alert, change = await price_service.should_trigger_alert(
            50100.0, 50000.0, 2.0
        )
        assert should_alert is False
        assert change == 0.2

    @pytest.mark.asyncio
    async def test_fetch_related_news_success(self, price_service):
        """Test successful related news fetching."""
        with patch(
            "src.crypto_news_aggregator.services.price_service.article_service"
        ) as mock_article_service:
            mock_article_service.get_top_articles_for_symbols = AsyncMock(
                return_value=[
                    {
                        "title": "Bitcoin surges to new highs",
                        "source": "test_source",
                        "sentiment_score": 0.2,
                        "keywords": ["Bitcoin", "surge"],
                    }
                ]
            )

            result = await price_service._fetch_related_news(["Bitcoin", "BTC"])

            assert len(result) == 1
            assert result[0]["title"] == "Bitcoin surges to new highs"

    @pytest.mark.asyncio
    async def test_fetch_related_news_error(self, price_service):
        """Test related news fetching with error."""
        with patch(
            "src.crypto_news_aggregator.services.price_service.article_service"
        ) as mock_article_service:
            mock_article_service.get_top_articles_for_symbols = AsyncMock(
                side_effect=Exception("DB Error")
            )

            result = await price_service._fetch_related_news(["Bitcoin", "BTC"])

            assert result == []

    @pytest.mark.asyncio
    async def test_generate_market_analysis_commentary_basic(self, price_service):
        """Test basic market analysis commentary generation."""
        with (
            patch.object(price_service, "get_markets_data") as mock_get_markets,
            patch.object(price_service, "get_global_market_data") as mock_get_global,
            patch.object(price_service, "get_historical_prices") as mock_get_historical,
            patch.object(price_service, "_fetch_related_news") as mock_fetch_news,
        ):

            # Mock all the required data
            mock_get_markets.return_value = {
                "bitcoin": {
                    "name": "Bitcoin",
                    "current_price": 50000.0,
                    "price_change_percentage_1h_in_currency": 0.5,
                    "price_change_percentage_24h_in_currency": 2.0,
                    "price_change_percentage_7d_in_currency": 5.0,
                    "total_volume": 50000000000,
                    "high_24h": 51000.0,
                    "low_24h": 49000.0,
                }
            }

            mock_get_global.return_value = {"market_cap_percentage": {"btc": 45.0}}

            mock_get_historical.return_value = {
                "prices": [[1609459200000, 50000.0]],
                "volumes": [[1609459200000, 50000000000]],
            }

            mock_fetch_news.return_value = []

            result = await price_service.generate_market_analysis_commentary("bitcoin")

            assert isinstance(result, str)
            assert len(result) > 100  # Should be a substantial commentary
            assert "Bitcoin" in result
            assert "trading at" in result
