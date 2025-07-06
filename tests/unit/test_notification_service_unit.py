"""
Unit tests for the notification service with all external dependencies mocked.
"""
import pytest
import sys
from unittest.mock import AsyncMock, MagicMock, patch, ANY, PropertyMock
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from types import SimpleNamespace

# Import the AlertCondition enum for testing
from src.crypto_news_aggregator.models.alert import AlertCondition, AlertInDB

# Disable logging during tests
import logging
logging.basicConfig(level=logging.CRITICAL)

# Test data
SAMPLE_ALERT = {
    "id": str(ObjectId()),
    "user_id": str(ObjectId()),
    "crypto_id": "bitcoin",
    "condition": "ABOVE",
    "threshold": 50000.0,
    "is_active": True,
    "created_at": datetime.now(timezone.utc),
    "last_triggered": None,
    "cooldown_minutes": 60,
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
        "snippet": "Bitcoin has reached a new all-time high price of $50,000.",
        "tags": ["Bitcoin", "Price"]
    },
    {
        "_id": ObjectId(),
        "title": "Institutional Investors Flock to Bitcoin",
        "source": {"name": "Crypto Insights"},
        "url": "https://example.com/btc-institutional",
        "published_at": "2023-01-02T10:30:00Z",
        "snippet": "Major institutions are increasing their Bitcoin holdings.",
        "tags": ["Bitcoin", "Institutional"]
    }
]

@pytest.fixture
def mock_mongo_manager():
    """Mock MongoDB manager with async methods."""
    from src.crypto_news_aggregator.db.mongodb import MongoManager
    
    # Create a mock manager
    mock_manager = MagicMock(spec=MongoManager)
    
    # Create test data
    test_articles = [
        {
            "_id": ObjectId(),
            "title": "Bitcoin Price Surges",
            "url": "https://example.com/bitcoin-surge",
            "description": "Bitcoin price surges past $50,000",
            "source": {"name": "Crypto News"},
            "published_at": datetime.now(timezone.utc),
            "snippet": "Bitcoin price surges past $50,000",
            "tags": ["bitcoin", "crypto"],
            "crypto_ids": ["bitcoin"]
        },
        {
            "_id": ObjectId(),
            "title": "Ethereum 2.0 Launches",
            "url": "https://example.com/eth2-launch",
            "description": "Ethereum completes the merge to proof-of-stake",
            "source": {"name": "Crypto Updates"},
            "published_at": datetime.now(timezone.utc) - timedelta(hours=1),
            "snippet": "Ethereum completes the merge to proof-of-stake",
            "tags": ["ethereum", "crypto"],
            "crypto_ids": ["ethereum"]
        }
    ]
    
    # Create a proper async iterator for articles
    class AsyncIterator:
        def __init__(self, items):
            self.items = items.copy()
            self.index = 0
            
        def __aiter__(self):
            return self
            
        async def __anext__(self):
            if self.index >= len(self.items):
                raise StopAsyncIteration
            item = self.items[self.index]
            self.index += 1
            return item
    
    # Create a mock cursor for articles with proper async iterator and sort support
    class MockAsyncCursor:
        def __init__(self, items):
            self.items = items.copy()
            self.sorted = False
            self.sort_key = None
            self.sort_direction = 1
            
        def __aiter__(self):
            self._iter = iter(self.items)
            return self
            
        async def __anext__(self):
            try:
                return next(self._iter)
            except StopIteration:
                raise StopAsyncIteration
            
        async def to_list(self, length=None):
            result = self.items[:length] if length is not None else self.items
            if self.sorted and self.sort_key:
                result = sorted(
                    result,
                    key=lambda x: x.get(self.sort_key, 0),
                    reverse=self.sort_direction == -1
                )
            return result
            
        def sort(self, sort_list):
            if sort_list:
                self.sort_key = sort_list[0][0]
                self.sort_direction = sort_list[0][1]
                self.sorted = True
            return self
    
    # Create test alert data with proper ObjectId
    test_alert = {**SAMPLE_ALERT, "_id": ObjectId(SAMPLE_ALERT["id"])}
    
    # Create mock collections with proper async support
    mock_articles = AsyncMock()
    mock_articles_cursor = MockAsyncCursor(test_articles)
    
    # Set up the articles find method to return our cursor
    async def mock_articles_find(*args, **kwargs):
        return mock_articles_cursor
    
    mock_articles.find = mock_articles_find
    
    # Mock alerts collection with proper async support
    mock_alerts = AsyncMock()
    mock_alerts_cursor = MockAsyncCursor([test_alert])
    
    # Set up the alerts find method to return our cursor
    async def mock_alerts_find(*args, **kwargs):
        return mock_alerts_cursor
    
    mock_alerts.find = mock_alerts_find
    
    # Mock update_one for alerts
    async def mock_update_one(filter, update, **kwargs):
        return type('obj', (object,), {'modified_count': 1})
    
    mock_alerts.update_one = mock_update_one
    
    # Mock the get_async_collection method
    async def get_collection(name):
        if name == 'alerts':
            return mock_alerts
        elif name == 'articles':
            return mock_articles
        return AsyncMock()
    
    mock_manager.get_async_collection = AsyncMock(side_effect=get_collection)
    
    # Mock the database
    mock_db = AsyncMock()
    mock_db.__getitem__.side_effect = get_collection
    mock_manager.get_async_database.return_value = mock_db
    
    # Mock the client
    mock_client = AsyncMock()
    mock_client.__getitem__.side_effect = lambda x: mock_db
    mock_manager._async_client = mock_client
    
    # Patch the global mongo_manager
    with patch('src.crypto_news_aggregator.db.mongodb.mongo_manager', mock_manager):
        yield mock_manager
    return manager

@pytest.fixture
def notification_service(mock_mongo_manager):
    """Create a NotificationService with all external dependencies mocked."""
    # Patch the mongo_manager before importing the notification service
    with patch('src.crypto_news_aggregator.services.notification_service.mongo_manager', mock_mongo_manager):
        # Import the service after patching
        from src.crypto_news_aggregator.services.notification_service import NotificationService
        from src.crypto_news_aggregator.services.email_service import EmailService
        
        # Create the service
        service = NotificationService()
        
        # Patch the email service
        mock_email_service = AsyncMock()
        mock_email_service.send_price_alert = AsyncMock(return_value=True)
        service._email_service = mock_email_service
        
        # Patch the template renderer
        mock_renderer = AsyncMock()
        mock_renderer.render_template = AsyncMock(return_value="<html>Test email</html>")
        service._template_renderer = mock_renderer
        
        # Mock the _get_recent_news method
        service._get_recent_news = AsyncMock(return_value=SAMPLE_NEWS_ARTICLES)
        
        return service

@pytest.mark.asyncio
async def test_process_price_alert(notification_service, mock_mongo_manager, mock_email_service):
    """Test processing price alerts."""
    # Setup test data
    crypto_id = "bitcoin"
    crypto_name = "Bitcoin"
    crypto_symbol = "BTC"
    current_price = 51000.0
    price_change_24h = 5.2
    
    # Mock the _send_alert_notification method
    async def mock_send_alert_notification(alert, **kwargs):
        return True
    
    notification_service._send_alert_notification = mock_send_alert_notification
    
    # Call the method
    result = await notification_service.process_price_alert(
        crypto_id="bitcoin",
        crypto_name="Bitcoin",
        crypto_symbol="BTC",
        current_price=51000.0,
        price_change_24h=5.0
    )
    
    # Assertions
    assert result["alerts_triggered"] == 1
    assert result["alerts_processed"] == 1
    
    # Get the alerts collection
    alerts_collection = await mock_mongo_manager.get_async_collection('alerts')
    
    # Verify the alert was queried with the correct parameters
    assert mock_alerts.find.called
    
    # Verify the alert was updated
    assert mock_alerts.update_one.called
    
    # Verify the email was sent
    mock_email_service.assert_awaited()

@pytest.fixture
def mock_settings(monkeypatch):
    """Mock application settings for testing."""
    # Create a mock settings object with all required attributes
    settings = SimpleNamespace(
        BASE_URL='https://test.example.com',
        SMTP_SERVER='smtp.test.com',
        SMTP_PORT=587,
        SMTP_USERNAME='test@example.com',
        SMTP_PASSWORD='testpass',
        EMAIL_FROM='noreply@test.com',
        ENVIRONMENT='testing'
    )
    
    # Patch the settings module
    monkeypatch.setattr('src.crypto_news_aggregator.core.config.settings', settings)
    return settings

@pytest.fixture
def mock_email_service():
    """Mock email service."""
    with patch('src.crypto_news_aggregator.services.notification_service.send_price_alert') as mock_send_price_alert:
        mock_send_price_alert.return_value = True
        yield mock_send_price_alert

@pytest.fixture
def notification_service(mock_mongo_manager, mock_settings, mock_email_service):
    """Create a notification service with mocked dependencies."""
    # Import after patching settings
    from src.crypto_news_aggregator.services.notification_service import NotificationService
    
    # Create the service with our mock manager
    service = NotificationService()
    
    # Mock the template rendering
    service._render_template = AsyncMock(return_value="<html>Test email</html>")
    
    # Mock the _get_user method
    async def mock_get_user(user_id):
        return {
            "_id": ObjectId(user_id),
            "email": "test@example.com",
            "name": "Test User"
        }
    
    service._get_user = mock_get_user
    
    # Don't mock _get_recent_news - let it use the actual implementation
    # which will use our mocked MongoDB collections
    pass
       
    yield service
    
    # Cleanup
    del service._get_user
    del service._get_recent_news

@pytest.mark.asyncio
async def test_send_alert_notification(notification_service, mock_mongo_manager, mock_email_service):
    """Test sending alert notification with news."""
    # Setup test data
    user_id = "507f1f77bcf86cd799439011"
    alert_data = {
        **SAMPLE_ALERT,
        "user_id": user_id,
        "condition": "above",
        "threshold": 50000.0,
        "is_active": True
    }
    
    # Create a proper AlertInDB object
    alert = AlertInDB(**alert_data)
    
    # Setup mock articles
    mock_articles = [
        {
            "title": "Bitcoin Price Surge",
            "url": "https://example.com/bitcoin-surge",
            "source": {"name": "Crypto News"},
            "published_at": datetime.now(timezone.utc),
            "snippet": "Bitcoin price surges past $50,000",
            "crypto_ids": ["bitcoin"]
        }
    ]
    
    # Get the articles collection mock
    articles_collection = await mock_mongo_manager.get_async_collection('articles')
    
    # Call the method
    result = await notification_service._send_alert_notification(
        alert=alert,
        crypto_name="Bitcoin",
        crypto_symbol="BTC",
        current_price=51000.0,
        price_change_24h=5.0
    )
    
    # Assertions
    assert result is True
    
    # Verify articles were queried with the correct parameters
    articles_collection.find.assert_awaited_once()
    
    # Get the query that was used
    query = articles_collection.find.await_args[0][0]
    assert "crypto_ids" in query
    assert "bitcoin" in query["crypto_ids"]
    
    # Verify email was sent with the correct template
    notification_service._render_template.assert_awaited_once()
    
    # Verify send_price_alert was called
    from src.crypto_news_aggregator.services.notification_service import send_price_alert
    send_price_alert.assert_awaited_once()

@pytest.mark.asyncio
async def test_check_alert_condition(notification_service):
    """Test alert condition checking with various threshold values."""
    # Create AlertInDB objects for testing
    from src.crypto_news_aggregator.models.alert import AlertInDB, AlertCondition
    
    # Test ABOVE condition
    alert_above = AlertInDB(
        **{
            **SAMPLE_ALERT,
            "condition": AlertCondition.ABOVE,
            "threshold": 50000.0,
        }
    )
    
    # Test with standard threshold
    assert notification_service._check_alert_condition(alert_above, 51000.0, 0) is True
    assert notification_service._check_alert_condition(alert_above, 50000.0, 0) is False  # Boundary
    assert notification_service._check_alert_condition(alert_above, 49000.0, 0) is False
    
    # Test with small threshold
    alert_above.threshold = 0.01
    assert notification_service._check_alert_condition(alert_above, 0.02, 0) is True
    assert notification_service._check_alert_condition(alert_above, 0.01, 0) is False  # Boundary
    assert notification_service._check_alert_condition(alert_above, 0.0099, 0) is False
    
    # Test with zero threshold
    alert_above.threshold = 0.0
    assert notification_service._check_alert_condition(alert_above, 0.0001, 0) is True
    assert notification_service._check_alert_condition(alert_above, 0.0, 0) is False
    assert notification_service._check_alert_condition(alert_above, -0.0001, 0) is False
    
    # Test BELOW condition
    alert_below = AlertInDB(
        **{
            **SAMPLE_ALERT,
            "condition": AlertCondition.BELOW,
            "threshold": 50000.0,
        }
    )
    
    # Test with standard threshold
    assert notification_service._check_alert_condition(alert_below, 49000.0, 0) is True
    assert notification_service._check_alert_condition(alert_below, 50000.0, 0) is False  # Boundary
    assert notification_service._check_alert_condition(alert_below, 51000.0, 0) is False
    
    # Test with small threshold
    alert_below.threshold = 0.01
    assert notification_service._check_alert_condition(alert_below, 0.0099, 0) is True
    assert notification_service._check_alert_condition(alert_below, 0.01, 0) is False  # Boundary
    assert notification_service._check_alert_condition(alert_below, 0.0101, 0) is False
    
    # Test with zero threshold
    alert_below.threshold = 0.0
    assert notification_service._check_alert_condition(alert_below, -0.0001, 0) is True
    assert notification_service._check_alert_condition(alert_below, 0.0, 0) is False
    assert notification_service._check_alert_condition(alert_below, 0.0001, 0) is False
    
    # Test PERCENT_UP condition
    alert_pct_up = AlertInDB(
        **{
            **SAMPLE_ALERT,
            "condition": AlertCondition.PERCENT_UP,
            "threshold": 5.0,
        }
    )
    
    # Test with standard threshold
    assert notification_service._check_alert_condition(alert_pct_up, 0, 5.1) is True
    assert notification_service._check_alert_condition(alert_pct_up, 0, 5.0) is True  # Boundary (inclusive)
    assert notification_service._check_alert_condition(alert_pct_up, 0, 4.9) is False
    
    # Test with small threshold
    alert_pct_up.threshold = 0.1
    assert notification_service._check_alert_condition(alert_pct_up, 0, 0.101) is True
    assert notification_service._check_alert_condition(alert_pct_up, 0, 0.1) is True  # Boundary (inclusive)
    assert notification_service._check_alert_condition(alert_pct_up, 0, 0.099) is False
    
    # Test with zero threshold (should trigger on any increase)
    alert_pct_up.threshold = 0.0
    assert notification_service._check_alert_condition(alert_pct_up, 0, 0.1) is True
    assert notification_service._check_alert_condition(alert_pct_up, 0, 0.0) is True  # Boundary (inclusive)
    assert notification_service._check_alert_condition(alert_pct_up, 0, -0.1) is False
    
    # Test PERCENT_DOWN condition
    alert_pct_down = AlertInDB(
        **{
            **SAMPLE_ALERT,
            "condition": AlertCondition.PERCENT_DOWN,
            "threshold": 5.0,
        }
    )
    
    # Test with standard threshold
    assert notification_service._check_alert_condition(alert_pct_down, 0, -5.1) is True
    assert notification_service._check_alert_condition(alert_pct_down, 0, -5.0) is True  # Boundary (inclusive)
    assert notification_service._check_alert_condition(alert_pct_down, 0, -4.9) is False
    
    # Test with small threshold
    alert_pct_down.threshold = 0.1
    assert notification_service._check_alert_condition(alert_pct_down, 0, -0.101) is True
    assert notification_service._check_alert_condition(alert_pct_down, 0, -0.1) is True  # Boundary (inclusive)
    assert notification_service._check_alert_condition(alert_pct_down, 0, -0.099) is False
    
    # Test with zero threshold (should trigger on any decrease)
    alert_pct_down.threshold = 0.0
    assert notification_service._check_alert_condition(alert_pct_down, 0, -0.1) is True
    assert notification_service._check_alert_condition(alert_pct_down, 0, 0.0) is True  # Boundary (inclusive)
    assert notification_service._check_alert_condition(alert_pct_down, 0, 0.1) is False

@pytest.mark.asyncio
async def test_get_recent_news(notification_service, mock_mongo_manager):
    """Test fetching recent news articles."""
    # Call the method
    result = await notification_service._get_recent_news("bitcoin", limit=2)
    
    # Assertions
    assert len(result) == 2
    assert result[0]["title"] == "Bitcoin Price Surges"
    assert result[1]["title"] == "Ethereum 2.0 Launches"
    
    # Verify the MongoDB query
    await mock_mongo_manager.get_async_collection('articles')
    
    # Verify find was called
    assert mock_articles.find.called
    
    # Get the query that was used
    find_args, find_kwargs = mock_articles.find.call_args
    assert find_kwargs.get('limit') == 2
    
    # Verify the result structure
    assert isinstance(result[0], dict)
    assert "title" in result[0]
    assert "url" in result[0]
    assert "snippet" in result[0] or "description" in result[0]
    assert "source" in result[0] and "name" in result[0]["source"]
    
    # Verify sort was called on the cursor
    assert mock_articles_cursor.sorted
    assert mock_articles_cursor.sort_key == "published_at"
    assert mock_articles_cursor.sort_direction == -1

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
