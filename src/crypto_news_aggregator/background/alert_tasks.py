"""
Background tasks for price alert notifications.
"""
import logging
from datetime import timedelta
from typing import Tuple

from ..services.notification_service import get_notification_service
from ..services.price_service import price_service
from ..db.session import get_session
from ..core.config import get_settings

logger = logging.getLogger(__name__)

async def check_price_alerts() -> Tuple[int, int]:
    """
    Task to check price alerts and send notifications.
    
    This task is triggered periodically by the asyncio worker.
    
    Returns:
        Tuple[int, int]: Number of alerts processed, number of notifications sent
    """
    logger.info("Starting price alert check")
    
    try:
        # Get the latest price for Bitcoin
        market_data = await price_service.get_market_data('bitcoin')
        if not market_data or 'current_price' not in market_data:
            logger.warning("Could not retrieve market data for price alert check.")
            return 0, 0

        current_price = market_data['current_price']
        price_change_24h = market_data.get('price_change_percentage_24h', 0)

        # Process alerts
        notification_service = get_notification_service()
        processed_total = 0
        sent_total = 0

        async for db in get_session():
            stats = await notification_service.process_price_alert(
                db=db,
                crypto_id='bitcoin',
                crypto_name='Bitcoin',
                crypto_symbol='BTC',
                current_price=current_price,
                price_change_24h=price_change_24h
            )
            processed_total += stats.get('alerts_processed', 0)
            sent_total += stats.get('notifications_sent', 0)

        logger.info(f"Price alert check completed. Processed: {processed_total}, Sent: {sent_total}")
        return processed_total, sent_total
        
    except Exception as e:
        logger.error(f"Error in check_price_alerts task: {e}", exc_info=True)
        return 0, 0
