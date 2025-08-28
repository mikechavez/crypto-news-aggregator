import asyncio
import logging
import sys
import os

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from sqlalchemy.ext.asyncio import AsyncSession

from src.crypto_news_aggregator.db.session import get_session
from src.crypto_news_aggregator.db.operations import users as user_ops
from src.crypto_news_aggregator.db.operations import alert as alert_ops
from src.crypto_news_aggregator.models.alert import AlertCreate, AlertCondition
from src.crypto_news_aggregator.models.user_sql import UserCreateSQL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def setup_test_alert():
    """Create a test alert for testing purposes."""
    async for db in get_session():
        try:
            # First, ensure a user exists to associate the alert with.
            user_email = "test@example.com"
            user = await user_ops.get_user_by_email(db, email=user_email)
            if not user:
                logger.info(f"User {user_email} not found, creating a new one.")
                user_in_create = UserCreateSQL(email=user_email, username='testuser', password='password')
                user = await user_ops.create_user(db, user_in=user_in_create)

            # Now, create the alert
            alert_in = AlertCreate(
                user_id=user.id,
                crypto_id="bitcoin",
                condition=AlertCondition.PERCENT_UP,
                threshold=0.1,  # A small threshold for easy triggering
                is_active=True
            )
            await alert_ops.add_alert(db, alert_in=alert_in)
            logger.info(f"Successfully created a test alert for {user.email} on {alert_in.crypto_id}.")

        finally:
            # The session is automatically closed by the context manager
            pass

if __name__ == "__main__":
    asyncio.run(setup_test_alert())
