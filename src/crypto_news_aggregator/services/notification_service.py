"""
Notification service for handling different types of alerts and notifications.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Alert
from ..db.operations.alert import get_active_alerts, update_alert_last_triggered
from ..services.email_service import send_price_alert
from ..core.config import settings

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
                        await self._send_alert_notification(
                            alert=alert,
                            crypto_name=crypto_name,
                            crypto_symbol=crypto_symbol,
                            current_price=current_price,
                            price_change_24h=price_change_24h
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
            time_since_last = datetime.utcnow() - alert.last_triggered
            if time_since_last < timedelta(hours=1):
                return False
                
        return True
    
    async def _send_alert_notification(
        self,
        alert: Alert,
        crypto_name: str,
        crypto_symbol: str,
        current_price: float,
        price_change_24h: float
    ) -> None:
        """
        Send an alert notification to the user.
        
        Args:
            alert: The alert that was triggered
            crypto_name: Name of the cryptocurrency
            crypto_symbol: Symbol of the cryptocurrency
            current_price: Current price
            price_change_24h: 24-hour price change percentage
        """
        if not alert.user or not alert.user.email:
            logger.warning(f"Alert {alert.id} has no associated user or email")
            return
            
        # Determine direction text
        if price_change_24h > 0:
            change_text = f"📈 {abs(price_change_24h):.2f}% increase"
        else:
            change_text = f"📉 {abs(price_change_24h):.2f}% decrease"
            
        # Prepare template context
        context = {
            "username": alert.user.username,
            "crypto_name": crypto_name,
            "crypto_symbol": crypto_symbol,
            "current_price": f"${current_price:,.2f}",
            "price_change_24h": f"{price_change_24h:+.2f}%",
            "change_text": change_text,
            "alert_threshold": f"{alert.threshold_percentage}% {alert.direction}",
            "unsubscribe_link": f"{settings.BASE_URL}/alerts/{alert.id}/unsubscribe"
        }
        
        # Send email
        await send_price_alert(
            to_email=alert.user.email,
            subject=f"🚨 {crypto_symbol} Price Alert: {change_text}",
            template_name="price_alert.html",
            context=context
        )
        
        logger.info(f"Sent price alert email to {alert.user.email} for {crypto_symbol} {change_text}")

# Singleton instance
notification_service = NotificationService()
