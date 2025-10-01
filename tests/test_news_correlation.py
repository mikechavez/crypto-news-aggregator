"""Test news correlation with price movements."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta

from src.crypto_news_aggregator.tasks.price_monitor import PriceMonitor
from src.crypto_news_aggregator.services.news_correlator import NewsCorrelator
from src.crypto_news_aggregator.services.notification_service import NotificationService


@pytest.fixture
def price_monitor():
    """Fixture for price monitor with mocked dependencies."""
    monitor = PriceMonitor()
    monitor.is_running = False  # Prevent background tasks
    return monitor


@pytest.mark.asyncio
async def test_handle_price_movement_with_news(price_monitor):
    """Test that price movements trigger news correlation."""
    # Mock the notification service
    mock_notification = AsyncMock(spec=NotificationService)
    mock_notification.process_price_alert.return_value = {
        "alerts_processed": 1,
        "alerts_triggered": 1,
        "notifications_sent": 1,
        "errors": 0,
    }

    # Mock the news correlator
    mock_correlator = MagicMock(spec=NewsCorrelator)
    mock_correlator.get_relevant_news.return_value = [
        {
            "title": "Bitcoin price surges after positive news",
            "source": "Test News",
            "url": "http://example.com/1",
            "published_at": (datetime.utcnow() - timedelta(hours=1)).isoformat(),
            "relevance_score": 0.9,
            "snippet": "Bitcoin price increased significantly...",
        }
    ]

    # Patch the dependencies
    with (
        patch(
            "src.crypto_news_aggregator.tasks.price_monitor.notification_service",
            mock_notification,
        ),
        patch(
            "src.crypto_news_aggregator.tasks.price_monitor.NewsCorrelator",
            return_value=mock_correlator,
        ),
    ):

        # Test data
        movement = {
            "symbol": "bitcoin",
            "current_price": 60000.0,
            "change_pct": 5.2,  # 5.2% increase
        }

        # Call the method
        await price_monitor._handle_price_movement(movement)

        # Verify news correlator was called
        mock_correlator.get_relevant_news.assert_called_once_with(
            price_change_percent=5.2, max_articles=3  # Should be absolute value
        )

        # Verify notification service was called with news articles
        args, kwargs = mock_notification.process_price_alert.call_args
        assert kwargs["context_articles"] is not None
        assert len(kwargs["context_articles"]) == 1
        assert (
            kwargs["context_articles"][0]["title"]
            == "Bitcoin price surges after positive news"
        )


@pytest.mark.asyncio
async def test_handle_price_movement_no_news(price_monitor):
    """Test price movement when no relevant news is found."""
    # Mock the notification service
    mock_notification = AsyncMock(spec=NotificationService)
    mock_notification.process_price_alert.return_value = {
        "alerts_processed": 1,
        "alerts_triggered": 1,
        "notifications_sent": 1,
        "errors": 0,
    }

    # Mock the news correlator to return no articles
    mock_correlator = MagicMock(spec=NewsCorrelator)
    mock_correlator.get_relevant_news.return_value = []

    # Patch the dependencies
    with (
        patch(
            "src.crypto_news_aggregator.tasks.price_monitor.notification_service",
            mock_notification,
        ),
        patch(
            "src.crypto_news_aggregator.tasks.price_monitor.NewsCorrelator",
            return_value=mock_correlator,
        ),
    ):

        # Test data
        movement = {
            "symbol": "bitcoin",
            "current_price": 59000.0,
            "change_pct": -2.5,  # 2.5% decrease
        }

        # Call the method
        await price_monitor._handle_price_movement(movement)

        # Verify notification service was called with empty articles list
        args, kwargs = mock_notification.process_price_alert.call_args
        assert kwargs["context_articles"] == []
