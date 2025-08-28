"""
Notification service for handling different types of alerts and notifications.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List

from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Alert
from ..db.operations.alert import get_active_alerts, update_alert_last_triggered
from ..services.email_service import email_service
from ..core.config import get_settings

logger = logging.getLogger(__name__)

class NotificationService:
    """Service for handling alert notifications."""
    
    async def process_price_alert(
        self,
        db: AsyncSession,
        crypto_id: str,
        crypto_name: str,
        crypto_symbol: str,
        current_price: float,
        price_change_24h: float,
        context_articles: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, int]:
        """
        Process price alerts for a given cryptocurrency.
        
        Args:
            db: Database session
            crypto_id: Cryptocurrency ID (e.g., 'bitcoin')
            crypto_name: Cryptocurrency name (e.g., 'Bitcoin')
            crypto_symbol: Cryptocurrency symbol (e.g., 'BTC')
            current_price: Current price of the cryptocurrency
            price_change_24h: 24-hour price change percentage
            context_articles: List of relevant articles for context (optional)
            
        Returns:
            Dict with processing statistics
        """
        logger.info(f"Processing price alerts for {crypto_name} ({crypto_symbol}): ${current_price:.2f} ({price_change_24h:+.2f}%)")
        
        # Get all active alerts for this cryptocurrency
        alerts = await get_active_alerts(db)
        alerts = [alert for alert in alerts if alert.symbol.upper() == crypto_symbol.upper()]
        
        stats = {
            'alerts_processed': 0,
            'alerts_triggered': 0,
            'notifications_sent': 0,
            'errors': 0
        }
            
        for alert in alerts:
            try:
                stats['alerts_processed'] += 1
                
                # Check if alert conditions are met
                if self._should_trigger_alert(alert, price_change_24h):
                    stats['alerts_triggered'] += 1
                    
                    # Send notification
                    try:
                        # Only include articles if the price change is significant
                        articles_to_include = context_articles if abs(price_change_24h) >= 1.0 else []
                        
                        await self._send_alert_notification(
                            alert=alert,
                            crypto_name=crypto_name,
                            crypto_symbol=crypto_symbol,
                            current_price=current_price,
                            price_change_24h=price_change_24h,
                            context_articles=articles_to_include
                        )
                        stats['notifications_sent'] += 1
                        
                        # Update last triggered time
                        await update_alert_last_triggered(db, alert.id)
                        
                    except Exception as e:
                        logger.error(f"Failed to send notification for alert {alert.id}: {e}")
                        stats['errors'] += 1
                        
            except Exception as e:
                logger.error(f"Error processing alert {alert.id}: {e}")
                stats['errors'] += 1
                continue
        
        return stats
    
    def _should_trigger_alert(self, alert: Alert, price_change_24h: float) -> bool:
        """
        Check if an alert should be triggered based on price change and alert conditions.
        
        Args:
            alert: The alert to check
            price_change_24h: 24-hour price change percentage
            
        Returns:
            bool: True if the alert should be triggered, False otherwise
        """
        # Check if price change meets the threshold
        if abs(price_change_24h) < alert.threshold_percentage:
            return False
            
        # Check direction
        if alert.direction == 'up' and price_change_24h <= 0:
            return False
        if alert.direction == 'down' and price_change_24h >= 0:
            return False
            
        # Check cooldown (1 hour)
        if alert.last_triggered:
            time_since_last = datetime.now(timezone.utc) - alert.last_triggered
            if time_since_last < timedelta(minutes=60):
                logger.debug(f"Alert {alert.id} is in cooldown. Last triggered {time_since_last.total_seconds() / 60:.2f} minutes ago.")
                return False  # Cooldown period
                
        return True
    
    async def _send_alert_notification(
        self,
        alert: Alert,
        crypto_name: str,
        crypto_symbol: str,
        current_price: float,
        price_change_24h: float,
        context_articles: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """
        Send an alert notification to the user with optional context articles.
        
        Args:
            alert: The alert that was triggered
            crypto_name: Name of the cryptocurrency
            crypto_symbol: Symbol of the cryptocurrency
            current_price: Current price
            price_change_24h: 24-hour price change percentage
            context_articles: List of relevant articles (optional)
        """
        # Determine the condition text based on alert direction
        if alert.direction == 'up':
            change_text = f"rose above ${alert.threshold_percentage:,.2f}"
        else:  # 'down'
            change_text = f"fell below ${alert.threshold_percentage:,.2f}"
        
        # Prepare article data for the email
        articles_data = []
        if context_articles:
            for article in context_articles:
                articles_data.append({
                    'title': article.get('title', 'No title'),
                    'source': article.get('source', 'Unknown source'),
                    'url': article.get('url', ''),
                    'published_at': article.get('published_at', ''),
                    'relevance_score': article.get('relevance_score', 0),
                    'snippet': article.get('snippet', '')
                })
        
        settings = get_settings()
        # Send the email using the email_service instance
        await email_service.send_price_alert(
            to=alert.user.email,
            user_id=str(alert.user_id),
            user_name=alert.user.username or 'User',
            crypto_name=crypto_name,
            crypto_symbol=crypto_symbol,
            condition=alert.direction,  # 'up' or 'down'
            threshold=alert.threshold_percentage,
            current_price=current_price,
            price_change_24h=price_change_24h,
            news_articles=articles_data[:5],  # Limit to top 5 articles
            dashboard_url=f"{settings.BASE_URL.rstrip('/')}/dashboard",
            settings_url=f"{settings.BASE_URL.rstrip('/')}/settings/alerts"
        )
        
        logger.info(f"Sent price alert email to {alert.user.email} for {crypto_symbol} {change_text}")

# Singleton instance
notification_service = NotificationService()
