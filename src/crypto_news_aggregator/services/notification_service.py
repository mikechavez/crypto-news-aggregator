"""
Notification service for handling different types of alerts and notifications.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from bson import ObjectId

from ..models.alert import AlertInDB, AlertCondition
from ..services.alert_service import alert_service
from ..services.email_service import send_price_alert
from ..db.mongodb import mongo_manager
from ..core.config import settings

logger = logging.getLogger(__name__)

class NotificationService:
    """Service for handling alert notifications."""
    
    async def process_price_alert(
        self,
        crypto_id: str,
        crypto_name: str,
        crypto_symbol: str,
        current_price: float,
        price_change_24h: float,
    ) -> Dict[str, Any]:
        """
        Process price alerts for a given cryptocurrency.
        
        Args:
            crypto_id: Cryptocurrency ID (e.g., 'bitcoin')
            crypto_name: Cryptocurrency name (e.g., 'Bitcoin')
            crypto_symbol: Cryptocurrency symbol (e.g., 'BTC')
            current_price: Current price of the cryptocurrency
            price_change_24h: 24-hour price change percentage
            
        Returns:
            Dict with processing statistics
        """
        logger.info(f"Processing price alerts for {crypto_name} ({crypto_symbol}): ${current_price:.2f} ({price_change_24h:+.2f}%)")
        
        # Find all active alerts for this cryptocurrency
        collection = await mongo_manager.get_async_collection('alerts')
        query = {
            'crypto_id': crypto_id,
            'is_active': True,
            '$or': [
                {'last_triggered': {'$exists': False}},
                {'last_triggered': {'$lt': datetime.utcnow() - timedelta(minutes=5)}}  # Cooldown period
            ]
        }
        
        alerts = []
        async for alert in collection.find(query):
            alerts.append(AlertInDB(**alert))
        
        if not alerts:
            return {
                'crypto_id': crypto_id,
                'alerts_processed': 0,
                'alerts_triggered': 0,
                'notifications_sent': 0,
                'errors': 0
            }
        
        # Process each alert
        stats = {
            'crypto_id': crypto_id,
            'alerts_processed': len(alerts),
            'alerts_triggered': 0,
            'notifications_sent': 0,
            'errors': 0
        }
        
        for alert in alerts:
            try:
                # Check if the alert condition is met
                should_trigger = self._check_alert_condition(
                    alert=alert,
                    current_price=current_price,
                    price_change_24h=price_change_24h
                )
                
                if should_trigger:
                    stats['alerts_triggered'] += 1
                    
                    # Send notification
                    success = await self._send_alert_notification(
                        alert=alert,
                        crypto_name=crypto_name,
                        crypto_symbol=crypto_symbol,
                        current_price=current_price,
                        price_change_24h=price_change_24h
                    )
                    
                    if success:
                        stats['notifications_sent'] += 1
                        
                        # Update last_triggered timestamp
                        await collection.update_one(
                            {'_id': ObjectId(alert.id)},
                            {'$set': {'last_triggered': datetime.utcnow()}}
                        )
                    else:
                        stats['errors'] += 1
                        
            except Exception as e:
                logger.error(f"Error processing alert {alert.id}: {str(e)}", exc_info=True)
                stats['errors'] += 1
        
        return stats
    
    def _check_alert_condition(
        self,
        alert: AlertInDB,
        current_price: float,
        price_change_24h: float
    ) -> bool:
        """Check if an alert condition is met."""
        if alert.condition == AlertCondition.ABOVE:
            return current_price > alert.threshold
        elif alert.condition == AlertCondition.BELOW:
            return current_price < alert.threshold
        elif alert.condition == AlertCondition.PERCENT_UP:
            return price_change_24h >= alert.threshold
        elif alert.condition == AlertCondition.PERCENT_DOWN:
            return price_change_24h <= -abs(alert.threshold)
        return False
    
    async def _send_alert_notification(
        self,
        alert: AlertInDB,
        crypto_name: str,
        crypto_symbol: str,
        current_price: float,
        price_change_24h: float,
    ) -> bool:
        """Send a notification for a triggered alert."""
        try:
            # Get user details (in a real app, this would come from a user service)
            user = await self._get_user(alert.user_id)
            if not user or not user.get('email'):
                logger.warning(f"User {alert.user_id} not found or has no email")
                return False
            
            # Generate dashboard URL
            dashboard_url = f"{settings.BASE_URL}/dashboard"
            settings_url = f"{settings.BASE_URL}/settings/alerts"
            
            # Send email notification
            return await send_price_alert(
                to=user['email'],
                user_name=user.get('name', 'there'),
                crypto_name=crypto_name,
                crypto_symbol=crypto_symbol,
                condition=alert.condition.value,
                threshold=alert.threshold,
                current_price=current_price,
                price_change_24h=price_change_24h,
                dashboard_url=dashboard_url,
                settings_url=settings_url
            )
            
        except Exception as e:
            logger.error(f"Error sending alert notification: {str(e)}", exc_info=True)
            return False
    
    async def _get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user details from the database."""
        try:
            users = await mongo_manager.get_async_collection('users')
            user = await users.find_one({'_id': ObjectId(user_id)})
            return user
        except Exception as e:
            logger.error(f"Error fetching user {user_id}: {str(e)}")
            return None

# Singleton instance
notification_service = NotificationService()
