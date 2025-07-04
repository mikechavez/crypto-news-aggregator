"""
Background task for monitoring cryptocurrency prices.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from ..services.price_service import price_service
from ..core.config import settings
from ..services.email_service import send_email_alert  # We'll create this next

logger = logging.getLogger(__name__)

class PriceMonitor:
    """Monitor cryptocurrency prices and trigger alerts on significant movements."""
    
    def __init__(self):
        self.is_running = False
        self.last_alert_time: Dict[str, datetime] = {}
        self.min_alert_interval = timedelta(minutes=30)  # Minimum time between alerts for the same coin
    
    async def start(self):
        """Start the price monitoring service."""
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
    
    async def _check_prices(self):
        """Check prices and trigger alerts if needed."""
        # Check for significant price movements
        movement = await price_service.check_price_movement()
        
        if movement and self._should_alert(movement['symbol']):
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
        """Handle a significant price movement."""
        logger.info(
            f"Significant price movement detected: {movement['symbol']} "
            f"{movement['change_pct']}% to ${movement['current_price']}"
        )
        
        # Prepare alert details
        subject = (
            f"🚨 {movement['symbol']} Price {'Up' if movement['direction'] == 'up' else 'Down'} "
            f"{abs(movement['change_pct'])}% to ${movement['current_price']}"
        )
        
        # Get recent price history for context
        history = price_service.get_recent_price_history(hours=4)
        price_history = "\n".join(
            f"{entry['timestamp'].strftime('%H:%M')}: ${entry['price']:.2f}" 
            for entry in history[-10:]  # Last 10 price points
        )
        
        # TODO: Get relevant news articles
        # articles = await news_service.get_relevant_articles(movement['symbol'])
        
        # Format the email body
        body = f"""
        <h2>{movement['symbol']} Price Alert</h2>
        <p><strong>Current Price:</strong> ${movement['current_price']:,.2f}</p>
        <p><strong>Change:</strong> {movement['change_pct']:.2f}%</p>
        
        <h3>Recent Price History</h3>
        <pre>{price_history}</pre>
        
        <h3>Relevant News</h3>
        <p>News article integration coming soon...</p>
        """
        
        # Send email alert
        try:
            await send_email_alert(
                to=settings.ALERT_EMAIL,
                subject=subject,
                html_content=body
            )
            logger.info(f"Sent price alert email for {movement['symbol']}")
        except Exception as e:
            logger.error(f"Failed to send price alert email: {e}", exc_info=True)

# Global instance
price_monitor = PriceMonitor()

async def start_price_monitor():
    """Start the price monitoring service."""
    await price_monitor.start()

async def stop_price_monitor():
    """Stop the price monitoring service."""
    await price_monitor.stop()
