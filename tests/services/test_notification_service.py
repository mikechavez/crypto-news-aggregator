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

class AsyncMockCursor:
    """A mock MongoDB cursor that supports async iteration and method chaining."""
    
    def __init__(self, items):
        self.items = items
        self._sort_key = None
        self._sort_direction = 1
        self._limit_count = None
    
    def sort(self, key, direction=1):
        self._sort_key = key
        self._sort_direction = direction
        return self
    
    def limit(self, count):
        self._limit_count = count
        return self
    
    def __aiter__(self):
        # Apply sorting if specified
        if self._sort_key is not None:
            self.items = sorted(
                self.items,
                key=lambda x: x.get(self._sort_key, 0),
                reverse=self._sort_direction == -1
            )
        
        # Apply limit if specified
        items = self.items[:self._limit_count] if self._limit_count is not None else self.items
        
        # Create an async iterator
        async def async_gen():
            for item in items:
                yield item
        
        return async_gen()


async def test_process_price_alert(notification_service, sample_alert, mock_mongo_manager):
    """Test processing price alerts."""
    # Create a list of alerts to return from the cursor
    alerts = [sample_alert.model_dump()]
    
    # Create a mock cursor with our test data
    mock_cursor = AsyncMockCursor(alerts)
    
    # Create a mock collection that returns our cursor
    mock_alerts = MagicMock()
    mock_alerts.find.return_value = mock_cursor
    mock_alerts.update_one = AsyncMock()
    
    # Mock the get_async_collection method to return our mock collection
    async def mock_get_collection(collection_name):
        if collection_name == 'alerts':
            return mock_alerts
        return MagicMock()
    
    mock_mongo_manager.get_async_collection = AsyncMock(side_effect=mock_get_collection)
    
    # Mock the _send_alert_notification method to avoid making actual notifications
    with patch.object(notification_service, '_send_alert_notification', new_callable=AsyncMock) as mock_send_alert:
        mock_send_alert.return_value = True  # Simulate successful notification
        
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
    
    # Verify the collection was accessed correctly
    mock_mongo_manager.get_async_collection.assert_awaited_once_with('alerts')
    mock_alerts.find.assert_called_once()
    
    # Verify the alert was processed and updated
    mock_send_alert.assert_awaited_once()
    mock_alerts.update_one.assert_awaited_once()

async def test_send_alert_notification(notification_service, sample_alert, mock_user, sample_news_articles, mock_mongo_manager, mock_send_price_alert):
    """Test sending alert notification with news."""
    # Mock the users collection
    mock_users = AsyncMock()
    mock_users.find_one = AsyncMock(return_value=mock_user)  # Make find_one return an awaitable
    
    # Create a mock cursor for articles with method chaining support
    mock_articles_cursor = MagicMock()
    
    # Set up the cursor to return sample news articles when to_list is awaited
    mock_articles_cursor.to_list = AsyncMock(return_value=sample_news_articles)
    
    # Set up method chaining for sort and limit
    mock_articles_cursor.sort.return_value = mock_articles_cursor
    mock_articles_cursor.limit.return_value = mock_articles_cursor
    
    # Mock the articles collection with proper async method chaining
    mock_articles = MagicMock()
    mock_articles.find.return_value = mock_articles_cursor
    
    # Mock the get_async_collection method to return the appropriate mock collection
    def get_collection_side_effect(collection_name):
        if collection_name == 'users':
            return mock_users
        elif collection_name == 'articles':
            return mock_articles
        return MagicMock()
    
    mock_mongo_manager.get_async_collection = AsyncMock(side_effect=get_collection_side_effect)
    
    # Patch the settings.BASE_URL to avoid AttributeError
    with patch('src.crypto_news_aggregator.services.notification_service.settings') as mock_settings:
        mock_settings.BASE_URL = 'http://testserver'
        
        # Call the method with patched settings
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
    
    # Check if the news articles are included in the call
    assert "news_articles" in call_args
    assert len(call_args["news_articles"]) > 0  # Ensure we have at least one article

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

@pytest.mark.asyncio
async def test_get_recent_news(notification_service, sample_news_articles, monkeypatch):
    """Test fetching recent news articles with proper MongoDB async mocking."""
    from unittest.mock import AsyncMock, MagicMock
    
    # Create a mock cursor with method chaining support
    mock_cursor = MagicMock()
    
    # Set up the method chaining for cursor methods
    mock_cursor.sort.return_value = mock_cursor
    mock_cursor.limit.return_value = mock_cursor
    
    # Sort articles by published_at in descending order
    sorted_articles = sorted(
        sample_news_articles.copy(),
        key=lambda x: x.get('published_at', ''),
        reverse=True
    )
    
    # Set up to_list to return our sample data
    mock_cursor.to_list = AsyncMock(return_value=sorted_articles[:2])  # Apply limit of 2
    
    # Create a mock collection with find method that returns our cursor
    mock_collection = MagicMock()
    mock_collection.find.return_value = mock_cursor
    
    # Create an async function that returns our mock collection
    async def mock_get_async_collection(collection_name):
        return mock_collection
    
    # Patch the mongo_manager.get_async_collection method
    mock_mongo_manager = MagicMock()
    mock_mongo_manager.get_async_collection = mock_get_async_collection
    
    # Apply the monkeypatch for mongo_manager
    monkeypatch.setattr(
        'src.crypto_news_aggregator.services.notification_service.mongo_manager',
        mock_mongo_manager
    )
    
    # Call the method
    result = await notification_service._get_recent_news("Bitcoin", limit=2)
    
    # Assertions
    assert len(result) == 2
    
    # Verify we got the expected articles
    article_titles = [article["title"] for article in result]
    assert "Bitcoin Reaches New All-Time High" in article_titles
    assert "Institutional Investors Flock to Bitcoin" in article_titles
    
    # Verify the query was made with the correct parameters
    mock_collection.find.assert_called_once()
    mock_cursor.sort.assert_called_once_with('published_at', -1)
    mock_cursor.limit.assert_called_once_with(2)
    mock_cursor.to_list.assert_awaited_once()

async def test_send_alert_notification_no_user(notification_service, sample_alert, mock_mongo_manager):
    """Test sending alert when user is not found."""
    # Mock the users collection to return no user
    mock_users = AsyncMock()
    mock_users.find_one.return_value = None
    
    # Mock the get_async_collection method to return our mock users collection
    mock_mongo_manager.get_async_collection = AsyncMock(return_value=mock_users)
    
    # Patch the settings.BASE_URL to avoid AttributeError
    with patch('src.crypto_news_aggregator.services.notification_service.settings') as mock_settings:
        mock_settings.BASE_URL = 'http://testserver'
        
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
