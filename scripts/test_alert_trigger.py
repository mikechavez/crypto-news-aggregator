"""
Test script to trigger a price alert with a small threshold (0.05%) and verify
email delivery with news articles.
"""
import asyncio
import logging
import os
import sys
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from uuid import uuid4

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.crypto_news_aggregator.services.price_service import price_service
from src.crypto_news_aggregator.services.news_correlator import NewsCorrelator
from src.crypto_news_aggregator.services.notification_service import notification_service
from src.crypto_news_aggregator.models.alert import AlertInDB
from src.crypto_news_aggregator.models.user import UserInDB, UserBase, UserSubscriptionPreferences, UserTrackingSettings
from src.crypto_news_aggregator.core.config import settings
from src.crypto_news_aggregator.db.mongodb import mongo_manager, initialize_mongodb
from src.crypto_news_aggregator.db.session import get_session
from sqlalchemy.ext.asyncio import AsyncSession

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create a timestamp for consistent usage
now = datetime.now(timezone.utc)

# Test user data
TEST_USER = UserInDB(
    _id=str(ObjectId()),
    username="testuser",
    email="test@example.com",
    first_name="Test",
    last_name="User",
    is_active=True,
    is_superuser=False,
    email_verified=True,
    hashed_password="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # hashed 'secret'
    subscription_preferences=UserSubscriptionPreferences(),
    tracking_settings=UserTrackingSettings(),
    created_at=now,
    updated_at=now,
    timezone="UTC",
    locale="en-US"
)

# Test alert data
try:
    TEST_ALERT = AlertInDB(
        _id=str(ObjectId()),
        user_id=TEST_USER.id,
        user_email=TEST_USER.email,
        user_name=f"{TEST_USER.first_name} {TEST_USER.last_name}",
        crypto_id="bitcoin",
        crypto_name="Bitcoin",
        crypto_symbol="BTC",
        condition="percent_up",  # Using a valid AlertCondition
        threshold=0.05,  # 0.05% threshold for testing
        threshold_percent=0.05,
        is_active=True,
        cooldown_minutes=5,
        status="active",
        created_at=now,
        updated_at=now,
        last_triggered=None,
        last_triggered_price=None
    )
except Exception as e:
    logger.error(f"Error creating test alert: {e}")
    raise

async def init_db():
    """Initialize the database connection."""
    logger.info("Initializing MongoDB connection...")
    await initialize_mongodb()
    # Get a database session
    async for session in get_session():
        return session

async def test_alert_trigger():
    """Test triggering an alert with a small price change."""
    logger.info("Starting alert trigger test...")
    
    # Initialize database
    db = await init_db()
    
    # Get current BTC price
    btc_data = await price_service.get_bitcoin_price()
    current_price = btc_data['price']
    logger.info(f"Current BTC price: ${current_price:,.2f} (24h change: {btc_data['change_24h']:.2f}%)")
    
    # Simulate a small price increase (0.06%)
    new_price = current_price * 1.0006  # 0.06% increase
    logger.info(f"Simulating price change: 0.06% to ${new_price:,.2f}")
    
    # Get relevant news articles
    news_correlator = NewsCorrelator()
    relevant_articles = await news_correlator.get_relevant_news("bitcoin", 0.06)
    logger.info(f"Found {len(relevant_articles)} relevant articles:")
    
    # Process the alert with the database session
    logger.info("Processing alert...")
    stats = await notification_service.process_price_alert(
        db=db,
        crypto_id=TEST_ALERT.crypto_id,
        crypto_name=TEST_ALERT.crypto_name,
        crypto_symbol=TEST_ALERT.crypto_symbol,
        current_price=new_price,
        price_change_24h=0.06,  # Using 0.06% as the price change for testing
        context_articles=relevant_articles
    )
    
    logger.info(f"Alert processing complete. Stats: {stats}")
    
    # Log detailed stats
    logger.info(f"Alerts processed: {stats.get('alerts_processed', 0)}")
    logger.info(f"Alerts triggered: {stats.get('alerts_triggered', 0)}")
    logger.info(f"Notifications sent: {stats.get('notifications_sent', 0)}")
    logger.info(f"Errors: {stats.get('errors', 0)}")
    
    if stats.get('notifications_sent', 0) > 0:
        logger.info("✅ Test successful! Email notification was sent with news articles.")
    else:
        logger.warning("⚠️  No notifications were sent. Check the logs for details.")
    
    # Clean up
    if hasattr(db, 'close') and callable(db.close):
        await db.close()
    await price_service.close()
    
    return stats

if __name__ == "__main__":
    asyncio.run(test_alert_trigger())
