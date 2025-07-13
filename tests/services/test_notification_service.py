"""
Tests for the notification service.

Refactored to use SQLAlchemy and align with the current implementation.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from datetime import timezone

from src.crypto_news_aggregator.services.notification_service import NotificationService
from src.crypto_news_aggregator.db.models import User, Alert


@pytest.fixture
def notification_service():
    """Fixture for NotificationService."""
    return NotificationService()

@pytest.fixture
def mock_user():
    """Fixture for a mock user."""
    return User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_password"
    )

@pytest.fixture
def sample_alert(mock_user):
    """Fixture for a sample alert.""" 
    return Alert(
        id=1,
        user_id=mock_user.id,
        user=mock_user,
        symbol="BTC",
        threshold_percentage=5.0,
        direction="up",
        last_triggered=None
    )

@pytest.mark.asyncio
async def test_process_price_alert(notification_service, db_session, sample_alert):
    """Test processing price alerts with SQLAlchemy."""
    db_session.add(sample_alert.user)
    db_session.add(sample_alert)
    await db_session.commit()

    with patch('src.crypto_news_aggregator.services.notification_service.get_active_alerts', new_callable=AsyncMock) as mock_get_active_alerts, \
         patch('src.crypto_news_aggregator.services.notification_service.update_alert_last_triggered', new_callable=AsyncMock) as mock_update_alert, \
         patch.object(notification_service, '_send_alert_notification', new_callable=AsyncMock) as mock_send_notification:

        mock_get_active_alerts.return_value = [sample_alert]

        stats = await notification_service.process_price_alert(
            db=db_session,
            crypto_id="bitcoin",
            crypto_name="Bitcoin",
            crypto_symbol="BTC",
            current_price=52000.0,
            price_change_24h=6.0
        )

    assert stats['alerts_processed'] == 1
    assert stats['alerts_triggered'] == 1
    assert stats['notifications_sent'] == 1
    assert stats['errors'] == 0
    mock_get_active_alerts.assert_awaited_once_with(db_session)
    mock_send_notification.assert_awaited_once()
    mock_update_alert.assert_awaited_once()

@pytest.mark.asyncio
async def test_send_alert_notification(notification_service, sample_alert):
    """Test sending an alert notification."""
    with patch('src.crypto_news_aggregator.services.notification_service.send_price_alert', new_callable=AsyncMock) as mock_send_price_alert:
        await notification_service._send_alert_notification(
            alert=sample_alert,
            crypto_name="Bitcoin",
            crypto_symbol="BTC",
            current_price=52000.0,
            price_change_24h=6.0,
            context_articles=[]
        )

        mock_send_price_alert.assert_awaited_once()
        call_args = mock_send_price_alert.call_args.kwargs
        assert call_args['to'] == sample_alert.user.email
        assert call_args['user_name'] == sample_alert.user.username
        assert call_args['crypto_name'] == "Bitcoin"
        assert call_args['current_price'] == 52000.0

def test_should_trigger_alert(notification_service, sample_alert):
    """Test the logic for deciding whether to trigger an alert."""
    # Should trigger: price change is above threshold and direction is correct
    assert notification_service._should_trigger_alert(sample_alert, 6.0) is True

    # Should not trigger: price change is below threshold
    assert notification_service._should_trigger_alert(sample_alert, 4.0) is False

    # Should not trigger: direction is wrong
    assert notification_service._should_trigger_alert(sample_alert, -6.0) is False

    # Should not trigger: cooldown period
    sample_alert.last_triggered = datetime.now(timezone.utc) - timedelta(minutes=30)
    assert notification_service._should_trigger_alert(sample_alert, 6.0) is False

@pytest.mark.asyncio
async def test_send_alert_notification_no_user(notification_service, sample_alert):
    """Test that no email is sent if the alert has no associated user."""
    sample_alert.user = None

    with patch('src.crypto_news_aggregator.services.notification_service.send_price_alert', new_callable=AsyncMock) as mock_send_price_alert, \
         patch('src.crypto_news_aggregator.services.notification_service.logger') as mock_logger:
        
        await notification_service._send_alert_notification(
            alert=sample_alert,
            crypto_name="Bitcoin",
            crypto_symbol="BTC",
            current_price=52000.0,
            price_change_24h=6.0,
            context_articles=[]
        )

    mock_send_price_alert.assert_not_called()
    mock_logger.warning.assert_called_with(f"Alert {sample_alert.id} has no associated user or email")
