"""
Background task for monitoring cryptocurrency prices and triggering alerts.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from ..services.price_service import price_service
from ..services.notification_service import notification_service
from ..services.news_correlator import NewsCorrelator
from ..core.config import get_settings

logger = logging.getLogger(__name__)

class PriceMonitor:
    """Monitor cryptocurrency prices and trigger alerts on significant movements."""
    
    def __init__(self):
        self.is_running = False
        self.task: Optional[asyncio.Task] = None
        self.last_alert_time: Dict[str, datetime] = {}
        self.last_checked_price: Dict[str, float] = {}
        self.min_alert_interval = timedelta(minutes=30)  # Minimum time between alerts for the same coin
    
    async def start(self):
        """Start the price monitoring service."""
        settings = get_settings()
        if self.is_running:
            logger.warning("Price monitor is already running")
            return
            
        self.is_running = True
        logger.info("Starting price monitor")
        
        while self.is_running:
            try:
                await self._check_prices()
            except Exception as e:
                logger.error(f"Error in price monitor: {e}", exc_info=True)
            
            # Wait for the next check interval
            await asyncio.sleep(settings.PRICE_CHECK_INTERVAL)
    
    async def stop(self):
        """Stop the price monitoring service."""
        logger.info("Stopping price monitor")
        self.is_running = False
        if self.task and not self.task.done():
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                logger.info("Price monitor task has been cancelled.")
    
    async def _check_prices(self):
        """Check prices and trigger alerts if needed."""
        settings = get_settings()
        symbol = 'bitcoin'  # Hardcoded for now
        price_data = await price_service.get_bitcoin_price()
        current_price = price_data.get('price')

        if current_price is None:
            logger.warning("Could not retrieve current price for bitcoin.")
            return

        last_price = self.last_checked_price.get(symbol)
        self.last_checked_price[symbol] = current_price

        if last_price is None:
            logger.info(f"First price check for {symbol}: ${current_price}")
            return

        should_alert, change_pct = await price_service.should_trigger_alert(
            current_price=current_price,
            last_alert_price=last_price,
            threshold=settings.PRICE_CHANGE_THRESHOLD
        )

        if should_alert and self._should_alert(symbol):
            movement = {
                'symbol': symbol,
                'current_price': current_price,
                'change_pct': change_pct
            }
            await self._handle_price_movement(movement)
    
    def _should_alert(self, symbol: str) -> bool:
        """Check if we should send an alert for this symbol."""
        now = datetime.utcnow()
        last_alert = self.last_alert_time.get(symbol)
        
        if last_alert and (now - last_alert) < self.min_alert_interval:
            logger.debug(f"Skipping alert for {symbol}: too soon since last alert")
            return False
            
        self.last_alert_time[symbol] = now
        return True
    
    async def _handle_price_movement(self, movement: Dict[str, Any]):
        """
        Handle a significant price movement by processing alerts.
        
        Args:
            movement: Dictionary containing price movement details
        """
        symbol = movement['symbol']
        current_price = movement['current_price']
        change_pct = movement['change_pct']
        
        logger.info(
            f"Significant price movement detected: {symbol} "
            f"{change_pct}% to ${current_price}"
        )
        
        try:
            # Get market data for context
            market_data = await price_service.get_market_data()
            
            # Get cryptocurrency details
            crypto_id = symbol.lower()  # This should be the CoinGecko ID (e.g., 'bitcoin')
            crypto_name = symbol.capitalize()  # This should be replaced with actual name from CoinGecko
            
            # Get relevant news articles for this price movement
            news_correlator = NewsCorrelator()
            relevant_articles = await news_correlator.get_relevant_news(
                price_change_percent=abs(change_pct),  # Use absolute value for correlation
                max_articles=3
            )
            
            logger.info(f"Found {len(relevant_articles)} relevant articles for price movement")
            
            # Process alerts with news context
            stats = await notification_service.process_price_alert(
                crypto_id=crypto_id,
                crypto_name=crypto_name,
                crypto_symbol=symbol.upper(),
                current_price=current_price,
                price_change_24h=change_pct,
                context_articles=relevant_articles
            )
            
            logger.info(
                f"Processed {stats['alerts_processed']} alerts for {symbol}. "
                f"Triggered: {stats['alerts_triggered']}, "
                f"Notifications sent: {stats['notifications_sent']}, "
                f"Errors: {stats['errors']}"
            )
            
        except Exception as e:
            logger.error(f"Error processing price movement for {symbol}: {e}", exc_info=True)

# Global instance
price_monitor = PriceMonitor()

async def start_price_monitor():
    """Start the price monitoring service."""
    await price_monitor.start()

async def stop_price_monitor():
    """Stop the price monitoring service."""
    await price_monitor.stop()
