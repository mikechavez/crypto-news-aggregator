"""
Test script for the alert notification system.
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta
import os
import sys
from unittest.mock import patch, MagicMock, AsyncMock

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging before any other imports
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Mock settings before importing other modules
class MockSettings:
    BASE_URL = "http://localhost:8000"
    SMTP_SERVER = "smtp.example.com"
    SMTP_PORT = 587
    SMTP_USERNAME = "test@example.com"
    SMTP_PASSWORD = "testpassword"
    EMAIL_FROM = "noreply@example.com"
    MIN_ALERT_INTERVAL_MINUTES = 15
    MONGODB_URI = "mongodb://localhost:27017/test_crypto_news_aggregator"

# Patch the settings before importing other modules
import sys

# Mock the settings module before importing other modules
sys.modules['src.crypto_news_aggregator.core.config'] = MagicMock()
sys.modules['src.crypto_news_aggregator.core.config'].settings = MockSettings()

# Import the alert notification service after patching settings
from src.crypto_news_aggregator.db.mongodb import MongoManager, mongo_manager
from src.crypto_news_aggregator.services.alert_service import alert_service
from src.crypto_news_aggregator.models.alert import AlertInDB, AlertCreate, AlertStatus
from src.crypto_news_aggregator.services.alert_notification_service import AlertNotificationService
from src.crypto_news_aggregator.services.price_service import price_service

# Test configuration
TEST_DB_NAME = "test_crypto_news_aggregator"
TEST_ALERT = {
    "user_id": "test_user_123",
    "user_email": "test@example.com",
    "user_name": "Test User",
    "crypto_id": "bitcoin",
    "crypto_name": "Bitcoin",
    "crypto_symbol": "BTC",
    "target_price": 50000.0,
    "threshold_percent": 1.0,
    "status": "active",
    "last_triggered": None,
    "last_triggered_price": None,
    "created_at": datetime.now(timezone.utc),
    "updated_at": datetime.now(timezone.utc)
}

# Mock email service
class MockEmailService:
    def __init__(self):
        self.sent_alerts = []
        self.send_price_alert = AsyncMock(return_value=True)
        
    async def send_price_alert(self, *args, **kwargs):
        self.sent_alerts.append({
            'args': args,
            'kwargs': kwargs
        })
        return True

async def create_test_alert() -> AlertInDB:
    """Create a test alert for demonstration purposes."""
    from bson import ObjectId
    
    # Create a test alert directly in the database
    db = await mongo_manager.get_async_database()
    alerts_collection = db.alerts
    
    test_alert = {
        "_id": ObjectId(),
        "user_id": "test_user_123",
        "user_email": "test@example.com",
        "user_name": "Test User",
        "crypto_id": "bitcoin",
        "crypto_name": "Bitcoin",
        "crypto_symbol": "BTC",
        "condition": "percent_up",
        "threshold": 1.0,
        "threshold_percent": 1.0,
        "is_active": True,
        "cooldown_minutes": 5,
        "status": "active",
        "last_triggered": None,
        "last_triggered_price": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    # Insert the alert directly into the database
    result = await alerts_collection.insert_one(test_alert)
    logger.info(f"Created test alert: {result.inserted_id}")
    
    # Return the alert as an AlertInDB object
    test_alert['id'] = str(test_alert.pop('_id'))
    return AlertInDB(**test_alert)

async def setup_test_environment():
    """Set up the test environment with MongoDB connection and test data."""
    logger.info("Setting up test environment...")
    
    # Initialize MongoDB connection
    mongo_manager.settings = MockSettings()
    mongo_manager.mongodb_uri = MockSettings.MONGODB_URI
    
    # Force reconnection to ensure clean state
    if not await mongo_manager.initialize(force_reconnect=True):
        raise RuntimeError("Failed to initialize MongoDB connection")
    
    logger.info("MongoDB connection initialized")
    
    # Get async client and database
    client = await mongo_manager.get_async_client()
    db = client.get_database()
    
    # Test the connection using async command
    try:
        # Use the admin database to run the ping command
        await client.admin.command('ping')
        logger.info("Successfully pinged MongoDB server")
    except Exception as e:
        logger.error(f"Failed to ping MongoDB: {e}")
        raise
    
    # Create a test alert
    try:
        alert = await create_test_alert()
        logger.info(f"Created test alert: {alert.id}")
        return alert, db
    except Exception as e:
        logger.error(f"Failed to create test alert: {e}")
        raise

async def cleanup_test_environment():
    """Clean up test environment and close connections."""
    logger.info("Cleaning up test environment...")
    
    # Clean up any test data
    try:
        if hasattr(mongo_manager, 'mongodb_uri'):
            # Get the database name from the URI
            db_name = mongo_manager.mongodb_uri.split('/')[-1].split('?')[0]
            if db_name and db_name != 'admin' and not db_name.startswith('local'):
                try:
                    # Get a fresh client to avoid any closed connection issues
                    client = await mongo_manager.get_async_client()
                    try:
                        # List all collections and drop them
                        db = client[db_name]
                        collections = await db.list_collection_names()
                        for collection_name in collections:
                            try:
                                await db[collection_name].drop()
                                logger.debug(f"Dropped collection: {collection_name}")
                            except Exception as e:
                                logger.warning(f"Error dropping collection {collection_name}: {e}")
                        
                        # Drop the test database
                        await client.drop_database(db_name)
                        logger.info(f"Dropped test database: {db_name}")
                    except Exception as e:
                        logger.error(f"Error cleaning up test database {db_name}: {e}")
                    finally:
                        # Ensure client is closed
                        if client:
                            client.close()
                except Exception as e:
                    logger.error(f"Error getting MongoDB client for cleanup: {e}")
    except Exception as e:
        logger.error(f"Error during test environment cleanup: {e}")
    
    # Close the MongoDB connection
    try:
        if hasattr(mongo_manager, '_async_client') and mongo_manager._async_client:
            try:
                # Close the MongoDB manager
                await mongo_manager.close()
                logger.info("MongoDB connection closed")
            except Exception as e:
                logger.error(f"Error closing MongoDB connection: {e}")
    except Exception as e:
        logger.error(f"Error accessing MongoDB manager during cleanup: {e}")

async def test_alert_notification(alert: AlertInDB):
    """Test the alert notification service with different price changes."""
    logger.info(f"Using test alert: {alert.id}")
    
    # Initialize the alert notification service with a mock email service
    alert_service = AlertNotificationService()
    mock_email_service = MockEmailService()
    
    # Patch the email service in the alert notification service
    with (
        patch('src.crypto_news_aggregator.services.alert_notification_service.email_service', mock_email_service),
        patch.object(alert_service, '_get_relevant_news', return_value=[])  # Mock _get_relevant_news to return empty list
    ):
        # Set initial price and last_triggered_price for the alert
        initial_price = 50000.0
        
        # Update the alert in the database with the initial price
        from src.crypto_news_aggregator.services.alert_service import alert_service as alert_svc
        from src.crypto_news_aggregator.models.alert import AlertUpdate
        
        # Verify initial alert state
        logger.info(f"Initial alert state - last_triggered_price: {alert.last_triggered_price}")
        
        # Create an update object with the new price
        update_data = AlertUpdate(last_triggered_price=initial_price)
        
        # Update the alert using the service method
        logger.info(f"Updating alert {alert.id} with initial price: {initial_price}")
        updated_alert = await alert_svc.update_alert(
            alert_id=str(alert.id),
            user_id=alert.user_id,  # Include the user_id from the alert
            alert_update=update_data
        )
        
        if updated_alert is None:
            logger.error("Failed to update alert in the database")
            raise AssertionError("Failed to update alert in the database")
        else:
            logger.info(f"Alert updated successfully: {updated_alert}")
        
        # Refresh the alert from the database to ensure we have the latest version
        alert = await alert_svc.get_alert(str(alert.id))
        if alert is None:
            logger.error("Failed to retrieve updated alert from the database")
            raise AssertionError("Failed to retrieve updated alert from the database")
        
        # Verify the update was successful
        if alert.last_triggered_price != initial_price:
            logger.error(f"Alert update failed. Expected last_triggered_price={initial_price}, got {alert.last_triggered_price}")
            raise AssertionError(f"Alert update failed. Expected last_triggered_price={initial_price}, got {alert.last_triggered_price}")
            
        logger.info(f"Verified alert update - last_triggered_price: {alert.last_triggered_price}")
        logger.debug(f"Full alert object after update: {alert.dict()}")
        
        # Test 1: Small price change (should not trigger alert)
        logger.info("Testing price change below threshold...")
        
        # Mock the price service to return a small price change
        with patch('src.crypto_news_aggregator.services.alert_notification_service.price_service.get_bitcoin_price') as mock_get_price:
            mock_get_price.return_value = {
                'price': 50499.0,  # Just below 1% threshold (50500 would be 1%)
                'change_24h': 0.5
            }
            
            # Check alerts
            processed, sent = await alert_service.check_and_send_alerts()
            assert sent == 0, "Alert should not be triggered for small price change"
            
            logger.info("✅ Test passed: Alert correctly not triggered for small price change")
        
        # Test 2: Large price change (should trigger alert)
        logger.info("Testing price change above threshold...")
        
        # Set a new baseline price
        new_baseline_price = 50000.0
        logger.info(f"Setting new baseline price: {new_baseline_price}")
        
        # Update the last_triggered_price in the database to simulate a new price point
        update_data = AlertUpdate(last_triggered_price=new_baseline_price)
        
        # Update the alert
        updated_alert = await alert_svc.update_alert(
            alert_id=str(alert.id),
            user_id=alert.user_id,
            alert_update=update_data
        )
        
        if updated_alert is None:
            logger.error("Failed to update alert in the database for large price change test")
            raise AssertionError("Failed to update alert for large price change test")
        
        logger.info(f"Alert updated successfully for large price change test: {updated_alert}")
        
        # Refresh the alert from the database
        alert = await alert_svc.get_alert(str(alert.id))
        if alert is None:
            logger.error("Failed to retrieve updated alert from the database")
            raise AssertionError("Failed to retrieve updated alert from the database")
        
        # Verify the update was successful
        if alert.last_triggered_price != new_baseline_price:
            logger.error(f"Alert update failed. Expected last_triggered_price={new_baseline_price}, got {alert.last_triggered_price}")
            raise AssertionError(f"Alert update failed. Expected last_triggered_price={new_baseline_price}, got {alert.last_triggered_price}")
            
        logger.info(f"Verified alert update - last_triggered_price: {alert.last_triggered_price}")
        logger.debug(f"Full alert object before large price change test: {alert.dict()}")
        
        # Test large price increase (should trigger alert)
        await price_service.update_price("bitcoin", 51000.0)  # 2% increase
        
        # Process alerts - we only care about our specific test alert
        # Clear any previous sent emails to isolate this test
        mock_email_service.sent_emails = []
        
        # Get our specific alert to verify its state
        updated_alert = await alert_service.get_alert(str(alert.id))
        assert updated_alert is not None, "Test alert should exist"
        
        # Process alerts
        processed, sent = await alert_notification_service.check_and_send_alerts()
        
        # Verify our specific alert was triggered
        updated_alert = await alert_service.get_alert(str(alert.id))
        assert updated_alert is not None, "Test alert should still exist after processing"
        
        # Check if our specific alert was triggered by looking at the mock email service
        test_alert_emails = [
            email for email in mock_email_service.sent_emails 
            if email.get("to") == "test@example.com"
        ]
        
        assert len(test_alert_emails) > 0, "Test alert email should have been sent"
        assert "2.00%" in test_alert_emails[0]["html"], "Email should contain the price change"
        
        # Verify the alert was updated with the last triggered price
        assert updated_alert.last_triggered_price == 51000.0, "Alert should be updated with last triggered price"
        
        logger.info("✅ Test passed: Alert correctly triggered for 2.00% change")
            
        # Test 3: Verify alert cooldown
        logger.info("Testing alert cooldown...")
        mock_email_service.sent_emails = []  # Reset sent emails
        
        # Check alerts again - should be in cooldown
        processed, sent = await alert_notification_service.check_and_send_alerts()
        assert sent == 0, "Alert should not be sent during cooldown period"
        assert len(mock_email_service.sent_emails) == 0
        
        logger.info("✅ Test passed: Alert cooldown respected")

async def main():
    logger.info("Starting alert notification test...")
    
    # Setup test environment
    await setup_test_environment()
    
    try:
        # Create a test alert
        alert = await create_test_alert()
        
        if not alert:
            raise ValueError("Failed to create test alert")
            
        logger.info(f"Created test alert: {alert.id}")
        
        # Test alert notification service with mock email service
        await test_alert_notification(alert)
        
        logger.info("✅ All tests completed successfully!")
        return 0
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return 1
        
    finally:
        # Cleanup test environment
        await cleanup_test_environment()
        logger.info("Test completed")

if __name__ == "__main__":
    # Configure asyncio to be more verbose about unhandled exceptions
    import asyncio
    import sys
    
    # Set up logging to show all messages
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )
    
    # Create and configure the event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Run the main function and exit with the appropriate status code
        exit_code = loop.run_until_complete(main())
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        sys.exit(1)
        
    finally:
        # Ensure all tasks are properly cancelled
        pending = asyncio.all_tasks(loop=loop)
        if pending:
            logger.warning(f"Cancelling {len(pending)} pending tasks")
            for task in pending:
                task.cancel()
                try:
                    loop.run_until_complete(task)
                except (asyncio.CancelledError, RuntimeError):
                    pass
        
        # Close the event loop
        try:
            if not loop.is_closed():
                loop.run_until_complete(loop.shutdown_asyncgens())
                loop.close()
        except Exception as e:
            logger.error(f"Error during loop cleanup: {e}")
            
        # Ensure the event loop is closed
        if not loop.is_closed():
            loop.close()
