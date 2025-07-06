"""
Unit tests for the notification service with all external dependencies mocked.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from bson import ObjectId

# Test data
SAMPLE_ALERT = {
    "id": str(ObjectId()),
    "user_id": str(ObjectId()),
    "crypto_id": "bitcoin",
    "condition": "ABOVE",
    "threshold": 50000.0,
    "is_active": True,
    "created_at": datetime.utcnow(),
    "last_triggered": None,
}

SAMPLE_USER = {
    "_id": ObjectId(SAMPLE_ALERT["user_id"]),
    "email": "test@example.com",
    "name": "Test User"
}

SAMPLE_NEWS_ARTICLES = [
    {
        "_id": ObjectId(),
        "title": "Bitcoin Reaches New All-Time High",
        "source": {"name": "Crypto News"},
        "url": "https://example.com/btc-news",
        "published_at": "2023-01-01T12:00:00Z",
        "description": "Bitcoin has reached a new all-time high price of $50,000."
    },
    {
        "_id": ObjectId(),
        "title": "Institutional Investors Flock to Bitcoin",
        "source": {"name": "Crypto Insights"},
        "url": "https://example.com/btc-institutional",
        "published_at": "2023-01-02T10:30:00Z",
        "description": "Major institutions are increasing their Bitcoin holdings."
    }
]

@pytest.fixture
def mock_mongo_manager():
    """Create a mock MongoDB manager."""
    manager = MagicMock()
    manager.get_async_collection = MagicMock()
    return manager

@pytest.fixture
def notification_service(mock_mongo_manager):
    """Create a NotificationService with all external dependencies mocked."""
    # Patch the mongo_manager before importing the notification service
    with patch('src.crypto_news_aggregator.services.notification_service.mongo_manager', mock_mongo_manager):
        # Import the service after patching
        from src.crypto_news_aggregator.services.notification_service import NotificationService
        
        # Create the service
        service = NotificationService()
        
        # Patch the _send_price_alert method
        service._send_price_alert = AsyncMock(return_value=True)
        
        return service

@pytest.mark.asyncio
async def test_process_price_alert(notification_service, mock_mongo_manager):
    """Test processing price alerts."""
    # Mock the alerts collection
    mock_alerts = AsyncMock()
    mock_alerts.find.return_value = [SAMPLE_ALERT]
    mock_mongo_manager.get_async_collection.return_value = mock_alerts
    
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

@pytest.mark.asyncio
async def test_send_alert_notification(notification_service, mock_mongo_manager):
    """Test sending alert notification with news."""
    # Mock the users and articles collections
    mock_users = AsyncMock()
    mock_users.find_one.return_value = SAMPLE_USER
    
    mock_articles = AsyncMock()
    mock_articles.find.return_value = SAMPLE_NEWS_ARTICLES
    
    # Configure the side effect to return different collections
    mock_mongo_manager.get_async_collection.side_effect = [
        mock_users,      # For users collection
        mock_articles    # For articles collection
    ]
    
    # Call the method
    result = await notification_service._send_alert_notification(
        alert=SAMPLE_ALERT,
        crypto_name="Bitcoin",
        crypto_symbol="BTC",
        current_price=51000.0,
        price_change_24h=5.0
    )
    
    # Assertions
    assert result is True
    notification_service._send_price_alert.assert_awaited_once()
    
    # Verify email was sent with news articles
    call_args = notification_service._send_price_alert.await_args[1]
    assert call_args["to"] == "test@example.com"
    assert call_args["crypto_name"] == "Bitcoin"
    assert "news_articles" in call_args

@pytest.mark.asyncio
async def test_check_alert_condition(notification_service):
    """Test alert condition checking."""
    # Test ABOVE condition
    alert_above = SAMPLE_ALERT.copy()
    alert_above["condition"] = "ABOVE"
    alert_above["threshold"] = 50000.0
    assert notification_service._check_alert_condition(alert_above, 51000.0, 0) is True
    assert notification_service._check_alert_condition(alert_above, 49000.0, 0) is False
    
    # Test BELOW condition
    alert_below = SAMPLE_ALERT.copy()
    alert_below["condition"] = "BELOW"
    alert_below["threshold"] = 50000.0
    assert notification_service._check_alert_condition(alert_below, 49000.0, 0) is True
    assert notification_service._check_alert_condition(alert_below, 51000.0, 0) is False
    
    # Test PERCENT_UP condition
    alert_pct_up = SAMPLE_ALERT.copy()
    alert_pct_up["condition"] = "PERCENT_UP"
    alert_pct_up["threshold"] = 5.0
    assert notification_service._check_alert_condition(alert_pct_up, 0, 5.1) is True
    assert notification_service._check_alert_condition(alert_pct_up, 0, 4.9) is False
    
    # Test PERCENT_DOWN condition
    alert_pct_down = SAMPLE_ALERT.copy()
    alert_pct_down["condition"] = "PERCENT_DOWN"
    alert_pct_down["threshold"] = 5.0
    assert notification_service._check_alert_condition(alert_pct_down, 0, -5.1) is True
    assert notification_service._check_alert_condition(alert_pct_down, 0, -4.9) is False

@pytest.mark.asyncio
async def test_get_recent_news(notification_service, mock_mongo_manager):
    """Test fetching recent news articles."""
    # Mock the articles collection
    mock_articles = AsyncMock()
    mock_articles.find.return_value = SAMPLE_NEWS_ARTICLES
    mock_mongo_manager.get_async_collection.return_value = mock_articles
    
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

@pytest.mark.asyncio
async def test_send_alert_notification_no_user(notification_service, mock_mongo_manager):
    """Test sending alert when user is not found."""
    # Mock the users collection to return no user
    mock_users = AsyncMock()
    mock_users.find_one.return_value = None
    mock_mongo_manager.get_async_collection.return_value = mock_users
    
    # Call the method
    result = await notification_service._send_alert_notification(
        alert=SAMPLE_ALERT,
        crypto_name="Bitcoin",
        crypto_symbol="BTC",
        current_price=51000.0,
        price_change_24h=5.0
    )
    
    # Assertions
    assert result is False
