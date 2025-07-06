"""
Tests for the notification service.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from bson import ObjectId

from src.crypto_news_aggregator.services.notification_service import NotificationService
from src.crypto_news_aggregator.models.alert import AlertInDB, AlertCondition

# Import test fixtures
pytestmark = pytest.mark.asyncio

async def test_process_price_alert(notification_service, sample_alert, mock_mongo_manager):
    """Test processing price alerts."""
    # Mock the alerts collection
    mock_alerts = AsyncMock()
    mock_alerts.find.return_value = [sample_alert.dict()]
    mock_mongo_manager.collections["alerts"] = mock_alerts
    
    # Call the method
    result = await notification_service.process_price_alert(
        crypto_id="bitcoin",
        crypto_name="Bitcoin",
        crypto_symbol="BTC",
        current_price=51000.0,
        price_change_24h=5.0
    )
    
    # Assertions
    assert result["crypto_id"] == "bitcoin"
    assert result["alerts_processed"] == 1
    assert result["alerts_triggered"] == 1
    assert result["notifications_sent"] == 1
    assert result["errors"] == 0

async def test_send_alert_notification(notification_service, sample_alert, mock_user, sample_news_articles, mock_mongo_manager, mock_send_price_alert):
    """Test sending alert notification with news."""
    # Mock the users and articles collections
    mock_users = AsyncMock()
    mock_users.find_one.return_value = mock_user
    
    mock_articles = AsyncMock()
    mock_articles.find.return_value = sample_news_articles
    
    # Configure the mock collections in the manager
    mock_mongo_manager.collections["users"] = mock_users
    mock_mongo_manager.collections["articles"] = mock_articles
    
    # Call the method
    result = await notification_service._send_alert_notification(
        alert=sample_alert,
        crypto_name="Bitcoin",
        crypto_symbol="BTC",
        current_price=51000.0,
        price_change_24h=5.0
    )
    
    # Assertions
    assert result is True
    mock_send_price_alert.assert_awaited_once()
    
    # Verify email was sent with news articles
    call_args = mock_send_price_alert.await_args[1]
    assert call_args["to"] == "test@example.com"
    assert call_args["crypto_name"] == "Bitcoin"
    assert call_args["news_articles"] == sample_news_articles

def test_check_alert_condition(notification_service, sample_alert):
    """Test alert condition checking."""
    # Test ABOVE condition
    sample_alert.condition = AlertCondition.ABOVE
    sample_alert.threshold = 50000.0
    assert notification_service._check_alert_condition(sample_alert, 51000.0, 0) is True
    assert notification_service._check_alert_condition(sample_alert, 49000.0, 0) is False
    
    # Test BELOW condition
    sample_alert.condition = AlertCondition.BELOW
    assert notification_service._check_alert_condition(sample_alert, 49000.0, 0) is True
    assert notification_service._check_alert_condition(sample_alert, 51000.0, 0) is False
    
    # Test PERCENT_UP condition
    sample_alert.condition = AlertCondition.PERCENT_UP
    sample_alert.threshold = 5.0
    assert notification_service._check_alert_condition(sample_alert, 0, 5.1) is True
    assert notification_service._check_alert_condition(sample_alert, 0, 4.9) is False
    
    # Test PERCENT_DOWN condition
    sample_alert.condition = AlertCondition.PERCENT_DOWN
    assert notification_service._check_alert_condition(sample_alert, 0, -5.1) is True
    assert notification_service._check_alert_condition(sample_alert, 0, -4.9) is False

async def test_get_recent_news(notification_service, sample_news_articles, mock_mongo_manager):
    """Test fetching recent news articles."""
    # Mock the articles collection
    mock_articles = AsyncMock()
    mock_articles.find.return_value = sample_news_articles
    mock_mongo_manager.collections["articles"] = mock_articles
    
    # Call the method
    result = await notification_service._get_recent_news("Bitcoin", limit=2)
    
    # Assertions
    assert len(result) == 2
    assert result[0]["title"] == "Bitcoin Reaches New All-Time High"
    assert result[1]["title"] == "Institutional Investors Flock to Bitcoin"
    
    # Verify the query
    query = mock_articles.find.await_args[0][0]
    assert query["$or"][0]["title"]["$regex"] == "Bitcoin"
    assert query["$or"][1]["content"]["$regex"] == "Bitcoin"
    assert query["$or"][2]["tags"] == {"$in": ["Bitcoin"]}

async def test_send_alert_notification_no_user(notification_service, sample_alert, mock_mongo_manager):
    """Test sending alert when user is not found."""
    # Mock the users collection to return no user
    mock_users = AsyncMock()
    mock_users.find_one.return_value = None
    mock_mongo_manager.collections["users"] = mock_users
    
    # Call the method
    result = await notification_service._send_alert_notification(
        alert=sample_alert,
        crypto_name="Bitcoin",
        crypto_symbol="BTC",
        current_price=51000.0,
        price_change_24h=5.0
    )
    
    # Assertions
    assert result is False
