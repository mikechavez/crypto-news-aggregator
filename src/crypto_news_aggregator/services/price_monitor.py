"""
Service for monitoring cryptocurrency prices and triggering alerts.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .price_service import price_service
from .notification_service import notification_service

logger = logging.getLogger(__name__)

class PriceMonitor:
    """Monitors cryptocurrency prices and triggers alerts."""
    
    def __init__(self, check_interval: int = 300):
        """Initialize the price monitor.
        
        Args:
            check_interval: How often to check prices, in seconds (default: 300s/5min)
        """
        self.check_interval = check_interval
        self.is_running = False
        
    async def start(self) -> None:
        """Start the price monitoring service."""
        if self.is_running:
            logger.warning("Price monitor is already running")
            return
            
        self.is_running = True
        logger.info("Starting price monitor")
        
        # Initial price fetch to populate history
        await price_service.get_market_data()
        
        # Start the monitoring loop
        while self.is_running:
            try:
                await self.check_prices()
            except Exception as e:
                logger.error(f"Error in price monitoring loop: {e}")
                
            # Wait for the next check interval
            await asyncio.sleep(self.check_interval)
    
    async def stop(self) -> None:
        """Stop the price monitoring service."""
        self.is_running = False
        logger.info("Stopping price monitor")
    
    async def check_prices(self) -> None:
        """Check prices and trigger alerts if conditions are met."""
        try:
            # Get the latest market data
            market_data = await price_service.get_market_data()
            if not market_data or 'current_price' not in market_data:
                logger.warning("No price data available")
                return
                
            current_price = market_data['current_price']
            price_change_24h = market_data.get('price_change_percentage_24h', 0)
            
            logger.debug(
                f"Checking prices - BTC: ${current_price:,.2f} "
                f"({price_change_24h:+.2f}% 24h)"
            )
            
            # Process alerts for Bitcoin
            result = await notification_service.process_price_alert(
                crypto_id='bitcoin',
                crypto_name='Bitcoin',
                crypto_symbol='BTC',
                current_price=current_price,
                price_change_24h=price_change_24h
            )
            
            logger.info(
                f"Processed {result['alerts_processed']} alerts: "
                f"{result['alerts_triggered']} triggered, "
                f"{result['notifications_sent']} notifications sent"
            )
            
        except Exception as e:
            logger.error(f"Error checking prices: {e}")
            raise

# Singleton instance
price_monitor = PriceMonitor()

# For testing
def run_monitor():
    """Run the price monitor (for testing purposes)."""
    import asyncio
    import signal
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Enable debug logging for our package
    logging.getLogger("crypto_news_aggregator").setLevel(logging.DEBUG)
    
    # Create event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Handle graceful shutdown
    def shutdown():
        logger.info("Shutting down...")
        loop.create_task(price_monitor.stop())
        
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown)
    
    try:
        # Start the monitor
        logger.info("Starting price monitor (press Ctrl+C to stop)")
        loop.run_until_complete(price_monitor.start())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.exception("Error in price monitor:")
    finally:
        # Cleanup
        pending = asyncio.all_tasks(loop=loop)
        for task in pending:
            task.cancel()
        
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        
        loop.close()
        logger.info("Price monitor stopped")

if __name__ == "__main__":
    run_monitor()
