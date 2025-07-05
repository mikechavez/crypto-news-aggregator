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
        """
        Handle a significant price movement by sending an email alert.
        
        Args:
            movement: Dictionary containing price movement details
        """
        logger.info(
            f"Significant price movement detected: {movement['symbol']} "
            f"{movement['change_pct']}% to ${movement['current_price']}"
        )
        
        try:
            # Get market data for context
            market_data = await price_service.get_market_data()
            
            # Get recent price history for the chart
            price_history = price_service.get_recent_price_history(hours=24)  # Last 24 hours
            
            # Get relevant news articles (last 6 hours)
            from datetime import datetime, timedelta
            from ..services.article_service import article_service
            
            articles = await article_service.search_articles(
                query="Bitcoin price",
                start_date=datetime.utcnow() - timedelta(hours=6),
                limit=3
            )
            
            # Prepare template context
            context = {
                'current_price': movement['current_price'],
                'change_pct': movement['change_pct'],
                'direction': movement['direction'],
                'change_24h': market_data.get('price_change_percentage_24h', 0),
                'market_cap': market_data.get('market_cap', 0),
                'volume_24h': market_data.get('total_volume', 0),
                'price_history': [{
                    'timestamp': entry['timestamp'],
                    'price': entry['price'],
                    'change_24h': entry.get('price_change_percentage_24h', 0)
                } for entry in price_history[-10:]],  # Last 10 price points
                'articles': [{
                    'title': article.title,
                    'url': article.url,
                    'source': article.source.get('name', 'Unknown'),
                    'published_at': article.published_at,
                    'summary': article.description or ''
                } for article in articles[0]] if articles and articles[0] else [],
                'unsubscribe_url': f"{settings.BASE_URL}/unsubscribe?email={settings.ALERT_EMAIL}",
                'current_year': datetime.utcnow().year
            }
            
            # Render email template
            from jinja2 import Environment, FileSystemLoader, select_autoescape
            import os
            
            env = Environment(
                loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), '..', 'templates')),
                autoescape=select_autoescape(['html', 'xml'])
            )
            env.filters['datetimeformat'] = lambda value, format: value.strftime(format)
            
            template = env.get_template('price_alert.html')
            html_content = template.render(**context)
            
            # Prepare subject line
            direction_emoji = '📈' if movement['direction'] == 'up' else '📉'
            subject = (
                f"{direction_emoji} Bitcoin Price Alert: "
                f"{movement['symbol']} {movement['direction'].title()} "
                f"{abs(movement['change_pct']):.1f}% to ${movement['current_price']:,.2f}"
            )
            
            # Send email alert
            await send_email_alert(
                to=settings.ALERT_EMAIL,
                subject=subject,
                html_content=html_content
            )
            logger.info(f"Sent price alert email for {movement['symbol']}")
            
        except Exception as e:
            logger.error(f"Failed to send price alert email: {e}", exc_info=True)
            # Fallback to simple email if template rendering fails
            try:
                await send_email_alert(
                    to=settings.ALERT_EMAIL,
                    subject=f"Bitcoin Price Alert: {movement['symbol']} {movement['direction'].title()}",
                    html_content=(
                        f"<h2>{movement['symbol']} Price Alert</h2>"
                        f"<p>Price changed by {movement['change_pct']:.2f}% "
                        f"to ${movement['current_price']:,.2f}</p>"
                    )
                )
            except Exception as fallback_error:
                logger.error(f"Fallback email also failed: {fallback_error}", exc_info=True)

# Global instance
price_monitor = PriceMonitor()

async def start_price_monitor():
    """Start the price monitoring service."""
    await price_monitor.start()

async def stop_price_monitor():
    """Stop the price monitoring service."""
    await price_monitor.stop()
