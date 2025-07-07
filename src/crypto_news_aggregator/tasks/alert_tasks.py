"""
Background tasks for price alert notifications.
"""
import logging
from datetime import timedelta
from typing import Tuple

from celery import shared_task
from celery.schedules import crontab

from ..services.alert_notification_service import alert_notification_service
from ..core.config import settings

logger = logging.getLogger(__name__)

@shared_task(name="check_price_alerts")
def check_price_alerts() -> Tuple[int, int]:
    """
    Celery task to check price alerts and send notifications.
    
    This task is triggered periodically by Celery Beat.
    
    Returns:
        Tuple[int, int]: Number of alerts processed, number of notifications sent
    """
    logger.info("Starting price alert check")
    
    try:
        # Process alerts and get stats
        processed, sent = alert_notification_service.check_and_send_alerts()
        logger.info(f"Price alert check completed. Processed: {processed}, Sent: {sent}")
        return processed, sent
        
    except Exception as e:
        logger.error(f"Error in check_price_alerts task: {e}", exc_info=True)
        return 0, 0

def get_beat_schedule() -> dict:
    """
    Get the Celery Beat schedule configuration for alert tasks.
    
    Returns:
        dict: Celery Beat schedule configuration
    """
    return {
        'check-price-alerts-every-5-minutes': {
            'task': 'check_price_alerts',
            'schedule': timedelta(minutes=5),  # Check every 5 minutes
            'options': {
                'expires': 240,  # Expire task after 4 minutes
                'time_limit': 240,  # Hard time limit of 4 minutes
            },
        },
    }
