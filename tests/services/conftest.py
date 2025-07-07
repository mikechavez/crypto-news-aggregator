"""
Pytest configuration and fixtures for notification service tests.
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, AsyncGenerator, Optional
import pytest
from bson import ObjectId
from decimal import Decimal
from datetime import datetime, timezone

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
        user_email="test@example.com",
        user_name="Test User",
        crypto_id="bitcoin",
        crypto_name="Bitcoin",
        crypto_symbol="BTC",
        condition=AlertCondition.ABOVE,
        threshold=50000.0,
        threshold_percent=1.0,
        is_active=True,
        cooldown_minutes=60,
        status="active",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
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
def mock_price_service():
    """Mock price service for testing."""
    class MockPriceService:
        def __init__(self):
            self.cache = {}
            
        async def get_crypto_price(self, crypto_id: str) -> Optional[Decimal]:
            """Mock get_crypto_price method."""
            return self.cache.get(crypto_id, Decimal('50000.0'))
            
        async def get_crypto_price_change_24h(self, crypto_id: str) -> float:
            """Mock get_crypto_price_change_24h method."""
            return 5.0  # 5% change by default
            
        async def get_crypto_details(self, crypto_id: str) -> Optional[Dict[str, Any]]:
            """Mock get_crypto_details method."""
            return {
                'id': crypto_id,
                'name': 'Bitcoin' if crypto_id == 'bitcoin' else 'Ethereum',
                'symbol': 'BTC' if crypto_id == 'bitcoin' else 'ETH',
                'current_price': Decimal('50000.0'),
                'price_change_24h': 5.0,
                'last_updated': datetime.utcnow()
            }
    
    return MockPriceService()

@pytest.fixture
def notification_service(mock_mongo_manager, mock_price_service):
    """Notification service with mocked dependencies."""
    from src.crypto_news_aggregator.services.notification_service import NotificationService
    from src.crypto_news_aggregator.services import price_service as price_service_module
    
    # Create the service
    service = NotificationService()
    
    # Patch the mongo_manager and price_service
    import src.crypto_news_aggregator.services.notification_service as notification_module
    original_mongo_manager = notification_module.mongo_manager
    original_price_service = price_service_module.price_service
    
    notification_module.mongo_manager = mock_mongo_manager
    price_service_module.price_service = mock_price_service
    
    yield service
    
    # Restore the original dependencies
    notification_module.mongo_manager = original_mongo_manager
    price_service_module.price_service = original_price_service

@pytest.fixture
def mock_send_price_alert():
    """Mock for the send_price_alert function."""
    with patch('src.crypto_news_aggregator.services.notification_service.send_price_alert', new_callable=AsyncMock) as mock:
        mock.return_value = True
        yield mock

# Import patch at the module level
# datetime is already imported at the top
