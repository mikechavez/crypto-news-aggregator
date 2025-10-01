"""
Service for sending price alert notifications with relevant news context.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from functools import lru_cache

from ..models.alert import AlertInDB, AlertStatus, AlertUpdate
from ..services.price_service import get_price_service
from ..services.alert_service import AlertService, get_alert_service
from ..services.email_service import get_email_service
from ..core.config import get_settings

logger = logging.getLogger(__name__)


class AlertNotificationService:
    """Service for managing and sending price alert notifications."""

    def __init__(self, alert_service: AlertService):
        self.price_service = get_price_service()
        self.alert_service = alert_service
        settings = get_settings()
        self.min_alert_interval = timedelta(
            minutes=getattr(settings, "MIN_ALERT_INTERVAL_MINUTES", 15)
        )

    async def check_and_send_alerts(self) -> Tuple[int, int]:
        """
        Check all active alerts and send notifications for triggered ones.

        Returns:
            Tuple[int, int]: Number of alerts processed, number of notifications sent
        """
        try:
            # Get all active alerts
            active_alerts = await self.alert_service.get_active_alerts()
            logger.info(
                f"[PIPELINE] Found {len(active_alerts)} active alerts to process"
            )

            sent_count = 0
            processed_count = 0

            for alert in active_alerts:
                try:
                    logger.info(f"[PIPELINE] Processing alert: {alert}")
                    processed_count += 1

                    # Check if alert is ready to be sent (respecting cooldown)
                    if not self._is_alert_ready(alert):
                        logger.info(
                            f"[PIPELINE] Alert {alert.id} not ready due to cooldown."
                        )
                        continue

                    # Get current price data
                    price_data = await self.price_service.get_bitcoin_price()
                    logger.info(f"[PIPELINE] Current price data: {price_data}")
                    if not price_data or "price" not in price_data:
                        logger.error("[PIPELINE] Failed to get current price data")
                        continue

                    current_price = price_data["price"]
                    change_24h = price_data.get("change_24h", 0)

                    # Check if alert condition is met
                    logger.info(
                        f"[PIPELINE] Checking alert condition for alert {alert.id} at price {current_price}"
                    )
                    should_alert, change_percent = await self._check_alert_condition(
                        alert, current_price
                    )
                    logger.info(
                        f"[PIPELINE] Alert condition for alert {alert.id}: should_alert={should_alert}, change_percent={change_percent}"
                    )

                    if should_alert:
                        # Get relevant news articles based on the price change
                        news_articles = await self._get_relevant_news(
                            price_change_percent=change_percent
                        )
                        logger.info(
                            f"[PIPELINE] News articles for alert {alert.id}: {news_articles}"
                        )

                        # Send notification with the relevant news
                        logger.info(
                            f"[PIPELINE] Sending notification for alert {alert.id}"
                        )
                        email_service = get_email_service()
                        success, _ = await email_service.send_price_alert(
                            to=alert.user_email,
                            user_name=alert.user_name or "there",
                            crypto_name="Bitcoin",
                            crypto_symbol="BTC",
                            condition=f"Price moved {'up' if change_percent > 0 else 'down'} by {abs(change_percent):.2f}%",
                            threshold=alert.threshold_percent,
                            current_price=current_price,
                            price_change_24h=change_24h,
                            news_articles=news_articles,
                            dashboard_url=f"{settings.BASE_URL}/dashboard",
                            settings_url=f"{settings.BASE_URL}/settings/alerts",
                        )
                        logger.info(
                            f"[PIPELINE] Notification send result for alert {alert.id}: {success}"
                        )

                        if success:
                            sent_count += 1
                            # Update alert with last triggered time
                            await self._update_alert_after_notification(
                                alert, current_price
                            )

                except Exception as e:
                    logger.error(
                        f"[PIPELINE] Error processing alert {alert.id}: {e}",
                        exc_info=True,
                    )

            logger.info(
                f"[PIPELINE] Processed {processed_count} alerts, sent {sent_count} notifications"
            )
            return processed_count, sent_count

        except Exception as e:
            logger.error(f"Error in check_and_send_alerts: {e}", exc_info=True)
            return 0, 0

    def _is_alert_ready(self, alert: AlertInDB) -> bool:
        """Check if an alert is ready to be sent (respecting cooldown)."""
        if not alert.last_triggered:
            return True

        time_since_last = datetime.now(timezone.utc) - alert.last_triggered
        return time_since_last >= self.min_alert_interval

    async def _check_alert_condition(
        self, alert: AlertInDB, current_price: float
    ) -> Tuple[bool, float]:
        """
        Check if an alert's condition is met.

        Returns:
            Tuple[bool, float]: (should_alert, change_percent)
        """
        logger.info(f"[DEBUG] Checking alert {alert.id}")
        logger.info(
            f"[DEBUG] Alert details: condition={alert.condition}, threshold={alert.threshold}%, threshold_percent={alert.threshold_percent}%"
        )
        logger.info(
            f"[DEBUG] Price data: last_triggered_price={alert.last_triggered_price}, current_price={current_price}"
        )

        if not alert.last_triggered_price:
            # First time checking this alert, set baseline price
            logger.info(
                f"[DEBUG] No last_triggered_price for alert {alert.id}, setting baseline"
            )
            return False, 0.0

        # Calculate price change since last alert
        change_amount = current_price - alert.last_triggered_price
        change_percent = (change_amount / alert.last_triggered_price) * 100

        # Log detailed calculation
        logger.info(
            f"[DEBUG] Change calculation: {current_price} - {alert.last_triggered_price} = {change_amount} ({change_percent:.2f}%)"
        )

        # Check if the change meets the threshold based on alert condition
        threshold = alert.threshold_percent
        logger.info(
            f"[DEBUG] Checking condition: {alert.condition}, change={change_percent:.2f}% vs threshold={threshold}%"
        )

        should_trigger = False

        # Check the specific alert condition
        if alert.condition == "percent_up" and change_percent >= threshold:
            should_trigger = True
            logger.info(
                f"[DEBUG] Condition met: Price increased by {change_percent:.2f}% >= {threshold}%"
            )
        elif alert.condition == "percent_down" and change_percent <= -threshold:
            should_trigger = True
            logger.info(
                f"[DEBUG] Condition met: Price decreased by {abs(change_percent):.2f}% >= {threshold}%"
            )
        elif alert.condition == "above" and current_price >= alert.threshold:
            should_trigger = True
            logger.info(
                f"[DEBUG] Condition met: Price {current_price} >= {alert.threshold}"
            )
        elif alert.condition == "below" and current_price <= alert.threshold:
            should_trigger = True
            logger.info(
                f"[DEBUG] Condition met: Price {current_price} <= {alert.threshold}"
            )

        if should_trigger:
            logger.info(
                f"[ALERT] Alert {alert.id} TRIGGERED: {alert.condition} condition met with {change_percent:.2f}% change"
            )
            return True, change_percent

        logger.info(f"[DEBUG] Alert {alert.id} NOT TRIGGERED: Condition not met")
        return False, change_percent

    async def _get_relevant_news(
        self, price_change_percent: float, limit: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Get relevant news articles for the alert based on price movement.

        Args:
            price_change_percent: The percentage change in price
            limit: Maximum number of articles to return

        Returns:
            List of relevant article summaries
        """
        from .news_correlator import news_correlator

        try:
            # Get relevant news articles based on price movement
            articles = await news_correlator.get_relevant_news(
                price_change_percent=price_change_percent,
                max_articles=limit,
                min_relevance=0.4,  # Only include fairly relevant articles
            )

            logger.debug(f"Found {len(articles)} relevant news articles")
            return articles

        except Exception as e:
            logger.error(f"Error getting relevant news: {e}", exc_info=True)
            return []

    async def _send_alert_notification(
        self,
        alert: AlertInDB,
        current_price: float,
        change_percent: float,
        change_24h: float,
        news_articles: List[Dict[str, Any]],
    ) -> bool:
        """Send a price alert notification."""
        try:
            # Format the condition for display
            direction = "up" if change_percent > 0 else "down"
            condition = f"Price moved {direction} by {abs(change_percent):.2f}%"

            # Prepare template context
            context = {
                "user_name": alert.user_name or "there",
                "crypto_name": "Bitcoin",
                "crypto_symbol": "BTC",
                "condition": condition,
                "threshold": alert.threshold_percent,
                "current_price": current_price,
                "price_change_24h": change_24h,
                "news_articles": news_articles,
                "dashboard_url": f"{settings.BASE_URL}/dashboard",
                "settings_url": f"{settings.BASE_URL}/settings/alerts",
            }

            # Send the email
            email_service = get_email_service()
            success, _ = await email_service.send_price_alert(
                to=alert.user_email,
                user_name=alert.user_name or "there",
                crypto_name="Bitcoin",
                crypto_symbol="BTC",
                condition=condition,
                threshold=alert.threshold_percent,
                current_price=current_price,
                price_change_24h=change_24h,
                news_articles=news_articles,
                dashboard_url=f"{settings.BASE_URL}/dashboard",
                settings_url=f"{settings.BASE_URL}/settings/alerts",
            )

            if success:
                logger.info(f"Sent price alert to {alert.user_email}")
            else:
                logger.error(f"Failed to send price alert to {alert.user_email}")

            return success

        except Exception as e:
            logger.error(f"Error sending alert notification: {e}", exc_info=True)
            return False

    async def _update_alert_after_notification(
        self, alert: AlertInDB, current_price: float
    ) -> None:
        """Update alert after sending a notification."""
        try:
            # Update the alert using the service with direct parameters
            await self.alert_service.update_alert(
                alert_id=str(alert.id),
                user_id=alert.user_id,
                last_triggered=datetime.now(timezone.utc),
                last_triggered_price=current_price,
                status=AlertStatus.ACTIVE,
            )
        except Exception as e:
            logger.error(f"Error updating alert {alert.id}: {e}", exc_info=True)


# Factory function for dependency injection
@lru_cache()
def get_alert_notification_service() -> AlertNotificationService:
    alert_service = get_alert_service()
    return AlertNotificationService(alert_service=alert_service)
