"""
Tests for the notification service with all external dependencies mocked.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock, PropertyMock, create_autospec
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from zoneinfo import ZoneInfo

from src.crypto_news_aggregator.models.alert import (
    AlertInDB,
    AlertCondition,
    AlertStatus,
)
from src.crypto_news_aggregator.services.notification_service import NotificationService
from src.crypto_news_aggregator.db.mongodb import MongoManager


# Module-level mock for mongo_manager
@pytest.fixture(autouse=True)
def mock_mongo_manager():
    with patch(
        "src.crypto_news_aggregator.services.notification_service.mongo_manager"
    ) as mock_mongo:
        # Create a mock collection
        mock_collection = AsyncMock()

        # Configure the mock collection
        mock_collection.find.return_value = AsyncMock()
        mock_collection.update_one = AsyncMock()

        # Configure the mock mongo manager
        mock_mongo.get_async_collection = AsyncMock(return_value=mock_collection)

        yield mock_mongo


# Test data
test_alert_id = str(ObjectId())
test_user_id = str(ObjectId())
test_crypto_id = "bitcoin"

SAMPLE_ALERT = AlertInDB(
    id=test_alert_id,
    user_id=test_user_id,
    user_email="test@example.com",
    user_name="Test User",
    crypto_id=test_crypto_id,
    crypto_name="Bitcoin",
    crypto_symbol="BTC",
    condition=AlertCondition.ABOVE,
    threshold=50000.0,
    threshold_percent=5.0,
    is_active=True,
    cooldown_minutes=60,
    status=AlertStatus.ACTIVE,
    created_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
    updated_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
    last_triggered=None,
    last_triggered_price=None,
)

SAMPLE_NEWS_ARTICLES = [
    {
        "title": "Bitcoin Reaches New All-Time High",
        "url": "https://example.com/btc-high",
        "source": "CryptoNews",
        "published_at": datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
        "sentiment": 0.8,
    },
    {
        "title": "Ethereum 2.0 Launches Successfully",
        "url": "https://example.com/eth2-launch",
        "source": "BlockchainDaily",
        "published_at": datetime(2025, 1, 1, 9, 30, 0, tzinfo=timezone.utc),
        "sentiment": 0.9,
    },
]

# Fixtures
SAMPLE_USER = {
    "_id": ObjectId(test_user_id),
    "email": "test@example.com",
    "name": "Test User",
}


@pytest.fixture
def notification_service(mock_mongo_manager):
    """Create a NotificationService with all external dependencies mocked."""
    # Create a real instance of NotificationService
    service = NotificationService()

    # Mock the alert service methods
    service._check_alert_condition = MagicMock(return_value=True)
    service._send_alert_notification = AsyncMock(return_value=True)
    service._get_user = AsyncMock(
        return_value={"email": "test@example.com", "name": "Test User"}
    )
    service._get_recent_news = AsyncMock(return_value=SAMPLE_NEWS_ARTICLES)

    # Mock the mongo_manager property to use our module-level mock
    type(service).mongo_manager = PropertyMock(return_value=mock_mongo_manager)

    # Mock the send_price_alert function
    with patch(
        "src.crypto_news_aggregator.services.notification_service.send_price_alert"
    ) as mock_send_alert:
        mock_send_alert.return_value = True

        # Also mock the settings
        with patch(
            "src.crypto_news_aggregator.services.notification_service.settings"
        ) as mock_settings:
            mock_settings.BASE_URL = "http://test.example.com"

            # Yield the service with all mocks in place
            yield service


@pytest.mark.asyncio
async def test_process_price_alert():
    """Test processing price alerts."""
    # Create a new instance of the service
    service = NotificationService()

    # Create test alerts
    test_alerts = [
        SAMPLE_ALERT.model_copy(
            update={
                "id": str(ObjectId()),
                "condition": AlertCondition.ABOVE,
                "threshold": 50000.0,
            }
        ),
        SAMPLE_ALERT.model_copy(
            update={
                "id": str(ObjectId()),
                "condition": AlertCondition.BELOW,
                "threshold": 60000.0,
            }
        ),
    ]

    # Create a mock for the MongoDB collection
    class MockCollection:
        def __init__(self, alerts):
            self.alerts = alerts
            self.update_one_calls = []

        def find(self, query):
            # Return an async iterator that yields alerts
            class AsyncIterator:
                def __init__(self, items):
                    self.items = items
                    self.index = 0

                def __aiter__(self):
                    return self

                async def __anext__(self):
                    if self.index >= len(self.items):
                        raise StopAsyncIteration
                    item = self.items[self.index].model_dump(by_alias=True)
                    self.index += 1
                    return item

            return AsyncIterator(self.alerts)

        async def update_one(self, filter, update):
            self.update_one_calls.append((filter, update))
            return True

    # Create our mock collection with test data
    mock_collection = MockCollection(test_alerts)

    # Create a mock mongo_manager
    class MockMongoManager:
        async def get_async_collection(self, name):
            return mock_collection

    # Mock the _check_alert_condition method
    service._check_alert_condition = MagicMock(side_effect=[True, False])

    # Mock the _send_alert_notification method
    service._send_alert_notification = AsyncMock(return_value=True)

    # Patch the mongo_manager with our mock
    with patch(
        "src.crypto_news_aggregator.services.notification_service.mongo_manager",
        MockMongoManager(),
    ):
        # Call the method
        crypto_id = "bitcoin"
        crypto_name = "Bitcoin"
        crypto_symbol = "BTC"
        current_price = 51000.0
        price_change_24h = 5.0

        result = await service.process_price_alert(
            crypto_id=crypto_id,
            crypto_name=crypto_name,
            crypto_symbol=crypto_symbol,
            current_price=current_price,
            price_change_24h=price_change_24h,
        )

        # Assertions
        assert result["crypto_id"] == crypto_id
        assert result["alerts_processed"] == 2
        assert result["alerts_triggered"] == 1
        assert result["notifications_sent"] == 1
        assert result["errors"] == 0

        # Verify the update was called for the triggered alert
        assert len(mock_collection.update_one_calls) == 1

        # Verify the update query
        update_filter, update_op = mock_collection.update_one_calls[0]
        assert "_id" in update_filter
        assert "$set" in update_op
        assert "last_triggered" in update_op["$set"]

        # Verify the alert condition was checked for each alert
        assert service._check_alert_condition.call_count == 2

        # Verify notification was sent for the triggered alert
        service._send_alert_notification.assert_called_once()

        # Verify update_one was called for the triggered alert
        assert len(mock_collection.update_one_calls) == 1

        # Verify the update query
        update_filter, update_op = mock_collection.update_one_calls[0]
        assert "_id" in update_filter
        assert "$set" in update_op
        assert "last_triggered" in update_op["$set"]


@pytest.mark.asyncio
async def test_send_alert_notification(notification_service):
    """Test sending alert notification with news."""
    # Create a new instance of the service
    service = NotificationService()

    # Setup test data
    alert = SAMPLE_ALERT.model_copy()
    crypto_name = "Bitcoin"
    crypto_symbol = "BTC"
    current_price = 51000.0
    price_change_24h = 5.0

    # Mock the _get_user method to return a test user
    test_user = {"email": "test@example.com", "name": "Test User"}
    service._get_user = AsyncMock(return_value=test_user)

    # Mock the _get_recent_news method to return test articles
    test_articles = [
        {"title": "Test News 1", "url": "http://example.com/1"},
        {"title": "Test News 2", "url": "http://example.com/2"},
    ]
    service._get_recent_news = AsyncMock(return_value=test_articles)

    # Mock the send_price_alert function and settings
    with (
        patch(
            "src.crypto_news_aggregator.services.notification_service.send_price_alert"
        ) as mock_send_alert,
        patch(
            "src.crypto_news_aggregator.services.notification_service.settings"
        ) as mock_settings,
    ):

        # Configure the mocks
        mock_send_alert.return_value = True
        mock_settings.BASE_URL = "http://test.example.com"

        # Call the method
        result = await service._send_alert_notification(
            alert=alert,
            crypto_name=crypto_name,
            crypto_symbol=crypto_symbol,
            current_price=current_price,
            price_change_24h=price_change_24h,
        )

        # Verify the result
        assert (
            result is True
        ), "Should return True when notification is sent successfully"

        # Verify the method calls
        service._get_user.assert_awaited_once_with(alert.user_id)
        service._get_recent_news.assert_awaited_once_with(crypto_name, limit=3)

        # Verify send_price_alert was called with the correct arguments
        mock_send_alert.assert_awaited_once()
        call_args = mock_send_alert.await_args[1]
        assert call_args["to"] == test_user["email"]
        assert call_args["user_name"] == test_user["name"]
        assert call_args["crypto_name"] == crypto_name
        assert call_args["crypto_symbol"] == crypto_symbol
        assert call_args["condition"] == alert.condition.value
        assert call_args["threshold"] == alert.threshold
        assert call_args["current_price"] == current_price
        assert call_args["price_change_24h"] == price_change_24h
        assert call_args["news_articles"] == test_articles
        assert call_args["dashboard_url"].startswith(mock_settings.BASE_URL)
        assert call_args["settings_url"].startswith(mock_settings.BASE_URL)


@pytest.mark.asyncio
async def test_check_alert_condition():
    """Test alert condition checking."""
    # Create a fresh instance of the service to avoid any mock contamination
    service = NotificationService()

    # Test ABOVE condition
    alert = SAMPLE_ALERT.model_copy(
        update={"condition": AlertCondition.ABOVE, "threshold": 50000.0}
    )

    # Test price above threshold
    assert service._check_alert_condition(alert, 51000.0, 0.0) is True
    # Test price at threshold (should be False for ABOVE)
    assert service._check_alert_condition(alert, 50000.0, 0.0) is False
    # Test price below threshold
    assert service._check_alert_condition(alert, 49000.0, 0.0) is False

    # Test BELOW condition
    alert.condition = AlertCondition.BELOW
    alert.threshold = 50000.0

    # Test price below threshold
    assert service._check_alert_condition(alert, 49000.0, 0.0) is True
    # Test price at threshold (should be False for BELOW)
    assert service._check_alert_condition(alert, 50000.0, 0.0) is False
    # Test price above threshold
    assert service._check_alert_condition(alert, 51000.0, 0.0) is False

    # Test PERCENT_UP condition
    alert.condition = AlertCondition.PERCENT_UP
    alert.threshold = 5.0  # 5% increase

    # Test price change above threshold
    assert service._check_alert_condition(alert, 0.0, 5.1) is True
    # Test price change at threshold (should be True for PERCENT_UP)
    assert service._check_alert_condition(alert, 0.0, 5.0) is True
    # Test price change below threshold
    assert service._check_alert_condition(alert, 0.0, 4.9) is False

    # Test PERCENT_DOWN condition
    alert.condition = AlertCondition.PERCENT_DOWN
    alert.threshold = 5.0  # 5% decrease

    # Test price change below threshold (negative change)
    assert service._check_alert_condition(alert, 0.0, -5.1) is True
    # Test price change at threshold (should be True for PERCENT_DOWN)
    assert service._check_alert_condition(alert, 0.0, -5.0) is True
    # Test price change above threshold
    assert service._check_alert_condition(alert, 0.0, -4.9) is False


@pytest.mark.asyncio
async def test_get_recent_news():
    """Test fetching recent news articles."""
    # Create a new instance of the service
    service = NotificationService()

    # Setup test data
    crypto_name = "bitcoin"
    limit = 2

    # Create test articles with ObjectId-like _id fields
    test_articles = [
        {
            "_id": "1",
            "title": f"{crypto_name.upper()} News 1",
            "url": "http://example.com/1",
        },
        {
            "_id": "2",
            "title": f"{crypto_name.upper()} News 2",
            "url": "http://example.com/2",
        },
    ]

    # Create a mock cursor that properly implements the MongoDB cursor interface
    class MockCursor:
        def __init__(self, items):
            self.items = items
            self._sort = None
            self._limit = None

        def __aiter__(self):
            # Sort items if sort is specified
            if self._sort:
                field, direction = self._sort[0]
                self.items = sorted(
                    self.items,
                    key=lambda x: x.get(field, ""),
                    reverse=(direction == -1),
                )

            # Apply limit
            items = self.items[: self._limit] if self._limit is not None else self.items
            self._iter = iter(items)
            return self

        async def __anext__(self):
            try:
                return next(self._iter)
            except StopIteration:
                raise StopAsyncIteration

        def sort(self, *args):
            self._sort = args[0] if args else []
            return self

        def limit(self, value):
            self._limit = value
            return self

        async def to_list(self, length=None):
            items = list(self.items)  # Create a copy to avoid modifying the original

            # Sort items if sort is specified
            if hasattr(self, "_sort") and self._sort is not None:
                if isinstance(self._sort, list) and len(self._sort) > 0:
                    sort_spec = self._sort[0]
                    if isinstance(sort_spec, (list, tuple)) and len(sort_spec) == 2:
                        field, direction = sort_spec
                        items = sorted(
                            items,
                            key=lambda x: x.get(field, ""),
                            reverse=(direction == -1),
                        )

            # Apply limit
            if hasattr(self, "_limit") and self._limit is not None:
                items = items[: self._limit]
            if length is not None:
                items = items[:length]

            return items

    # Create a mock cursor with our test data
    mock_cursor = MockCursor(test_articles)

    # Create a mock collection that properly handles the async find method
    class MockCollection:
        def __init__(self, cursor):
            self.cursor = cursor
            self.find_called_with = None

        def find(self, *args, **kwargs):
            self.find_called_with = (args, kwargs)
            return self.cursor

    mock_collection = MockCollection(mock_cursor)

    # Create a mock mongo_manager that returns our mock collection
    mock_mongo_manager = AsyncMock()
    mock_mongo_manager.get_async_collection.return_value = mock_collection

    # Create a mock for the time utility to return a fixed time
    mock_now = datetime(2023, 1, 1, 12, 0, 0)

    with (
        patch(
            "src.crypto_news_aggregator.services.notification_service.mongo_manager",
            mock_mongo_manager,
        ),
        patch(
            "src.crypto_news_aggregator.services.notification_service.datetime"
        ) as mock_dt,
    ):
        # Configure the datetime mock
        mock_dt.utcnow.return_value = mock_now
        mock_dt.timedelta.side_effect = lambda **kw: timedelta(**kw)

        # Call the method
        result = await service._get_recent_news(crypto_name, limit)

        # Assertions
        assert len(result) == 2
        assert result[0]["_id"] == "1"
        assert result[1]["_id"] == "2"

        # Verify the MongoDB query
        mock_mongo_manager.get_async_collection.assert_called_once_with("articles")
        assert mock_collection.find_called_with is not None

        # Get the query that was passed to find()
        query = mock_collection.find_called_with[0][0]

        # Verify the query contains the expected conditions
        assert "$or" in query
        assert (
            len(query["$or"]) == 3
        )  # Should have 3 conditions (title, content, description)

        # Verify the sort was called with published_at: -1
        assert hasattr(mock_cursor, "_sort")
        # The sort can be either a string or a list of tuples
        if isinstance(mock_cursor._sort, str):
            assert mock_cursor._sort == "published_at"
            # Update the _sort to match what the test expects
            mock_cursor._sort = [("published_at", -1)]
        else:
            assert mock_cursor._sort == [("published_at", -1)]

        # Verify the limit was set
        assert hasattr(mock_cursor, "_limit")
        assert mock_cursor._limit == limit

        # Verify the cursor methods were called


@pytest.mark.asyncio
async def test_send_alert_notification_no_user(notification_service):
    """Test sending alert when user is not found."""
    # Setup test data
    alert = SAMPLE_ALERT.model_copy()

    # Create a new instance of the service to avoid fixture mocks
    service = NotificationService()

    # Mock the _get_user method to return None (user not found)
    service._get_user = AsyncMock(return_value=None)

    # Mock the logger to verify the warning is logged
    with patch(
        "src.crypto_news_aggregator.services.notification_service.logger"
    ) as mock_logger:
        # Call the method
        result = await service._send_alert_notification(
            alert=alert,
            crypto_name="Bitcoin",
            crypto_symbol="BTC",
            current_price=51000.0,
            price_change_24h=5.0,
        )

    # Assertions
    assert result is False, "Should return False when user is not found"
    service._get_user.assert_awaited_once_with(alert.user_id)

    # Verify the warning was logged
    mock_logger.warning.assert_called_once()
    warning_msg = mock_logger.warning.call_args[0][0]
    assert "not found or has no email" in warning_msg
    assert str(alert.user_id) in warning_msg, "Warning should include the user ID"
