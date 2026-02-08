"""
Background tasks for price alert notifications.
"""

import logging
from datetime import timedelta
from typing import Tuple

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="check_price_alerts")
def check_price_alerts() -> Tuple[int, int]:
    """
    Celery task to check price alerts and send notifications.

    This task is triggered periodically by Celery Beat.

    NOTE: This is currently a no-op task. The price API is not integrated yet.
    Once price data is available, this task will:
    - Fetch current prices for tracked cryptocurrencies
    - Compare against alert thresholds
    - Send notifications via email

    Returns:
        Tuple[int, int]: Number of alerts processed, number of notifications sent
    """
    logger.info("Price alert check completed (no-op until price API integrated)")
    return 0, 0


def get_beat_schedule() -> dict:
    """
    Get the Celery Beat schedule configuration for alert tasks.

    Returns:
        dict: Celery Beat schedule configuration
    """
    return {
        "check-price-alerts-every-5-minutes": {
            "task": "check_price_alerts",
            "schedule": timedelta(minutes=5),  # Check every 5 minutes
            "options": {
                "expires": 240,  # Expire task after 4 minutes
                "time_limit": 240,  # Hard time limit of 4 minutes
            },
        },
    }
