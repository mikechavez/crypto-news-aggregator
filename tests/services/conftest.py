"""
Pytest configuration and fixtures for notification service tests.
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock
from typing import Dict, Any, AsyncGenerator
import pytest
from bson import ObjectId

from src.crypto_news_aggregator.models.alert import AlertInDB, AlertCondition

@pytest.fixture
def mock_mongo_manager():
    """Mock MongoDB manager for testing."""
    class MockMongoManager:
        def __init__(self):
            self.collections = {}
            
        async def get_async_collection(self, name: str):
            if name not in self.collections:
                self.collections[name] = AsyncMock()
            return self.collections[name]
            
    return MockMongoManager()

@pytest.fixture
def sample_alert():
    """Sample alert for testing."""
    return AlertInDB(
        id=str(ObjectId()),
        user_id=str(ObjectId()),
        crypto_id="bitcoin",
        condition=AlertCondition.ABOVE,
        threshold=50000.0,
        is_active=True,
    )

@pytest.fixture
def sample_news_articles():
    """Sample news articles for testing."""
    return [
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
def mock_user():
    """Mock user data for testing."""
    return {
        "_id": ObjectId(),
        "email": "test@example.com",
        "name": "Test User"
    }

@pytest.fixture
def notification_service(mock_mongo_manager):
    """Notification service with mocked dependencies."""
    from src.crypto_news_aggregator.services.notification_service import NotificationService
    
    # Create the service
    service = NotificationService()
    
    # Patch the mongo_manager
    import src.crypto_news_aggregator.services.notification_service as notification_module
    original_mongo_manager = notification_module.mongo_manager
    notification_module.mongo_manager = mock_mongo_manager
    
    yield service
    
    # Restore the original mongo_manager
    notification_module.mongo_manager = original_mongo_manager

@pytest.fixture
def mock_send_price_alert():
    """Mock for the send_price_alert function."""
    with patch('src.crypto_news_aggregator.services.notification_service.send_price_alert', new_callable=AsyncMock) as mock:
        mock.return_value = True
        yield mock

# Import patch at the module level
from unittest.mock import patch
