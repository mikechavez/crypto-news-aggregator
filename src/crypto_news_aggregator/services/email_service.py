"""
Email service for sending alerts and notifications with tracking capabilities.
"""
import logging
import uuid
import hashlib
import json
import re
import smtplib
import urllib.parse
from datetime import datetime
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional, Tuple

from bson import ObjectId

from ..core.config import get_settings
from ..db.mongodb import get_mongodb
from ..models.email import EmailEvent, EmailEventType, EmailTracking
from ..utils.template_renderer import template_renderer

logger = logging.getLogger(__name__)


class EmailService:
    """
    Service for sending and tracking email notifications with support for:
    - Open tracking (via 1x1 pixel images)
    - Click tracking (via link rewriting)
    - Email delivery status
    - Unsubscribe functionality
    - User preferences
    """

    def __init__(self):
        settings = get_settings()
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.sender_email = settings.EMAIL_FROM or self.smtp_username
        self.base_url = settings.BASE_URL.rstrip('/')
        self.tracking_enabled = getattr(settings, 'EMAIL_TRACKING_ENABLED', True)
        self.tracking_pixel_url = f"{self.base_url}/api/v1/emails/track/open/{{message_id}}"
        self.tracking_click_url = f"{self.base_url}/api/v1/emails/track/click/{{message_id}}/{{link_hash}}"
        self.unsubscribe_url = f"{self.base_url}/api/v1/emails/unsubscribe/{{token}}"

    async def _generate_message_id(self, recipient: str) -> str:
        """Generate a unique message ID for tracking purposes."""
        unique_str = f"{recipient}-{datetime.utcnow().timestamp()}-{uuid.uuid4()}"
        return hashlib.sha256(unique_str.encode()).hexdigest()

    def _hash_url(self, url: str) -> str:
        """Generate a hash for a URL."""
        return hashlib.md5(url.encode()).hexdigest()

    def _add_tracking_pixel(self, html_content: str, message_id: str) -> str:
        """Add tracking pixel to the email HTML."""
        tracking_pixel = f"""
        <div style=\"display:none;\">
            <img src=\"{self.tracking_pixel_url.format(message_id=message_id)}\" 
                 alt=\"\" width=\"1\" height=\"1\" style=\"border:none;width:1px;height:1px;\" />
        </div>
        """
        if "</body>" in html_content:
            return html_content.replace("</body>", f"{tracking_pixel}</body>")
        return html_content + tracking_pixel

    def _track_links(self, html_content: str, message_id: str) -> Tuple[str, Dict[str, str]]:
        """
        Replace all links in the HTML with tracking links.
        Returns the modified HTML and a mapping of original URLs to tracking URLs.
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html_content, 'html.parser')
        link_mapping = {}

        for a_tag in soup.find_all('a', href=True):
            original_url = a_tag['href']
            if not original_url.startswith(('http://', 'https://')):
                continue

            link_hash = self._hash_url(original_url)
            tracking_url = self.tracking_click_url.format(
                message_id=message_id,
                link_hash=link_hash
            )

            link_mapping[link_hash] = original_url
            a_tag['href'] = tracking_url

        return str(soup), link_mapping

    async def _save_tracking_data(
        self,
        message_id: str,
        user_id: str,
        recipient_email: str,
        subject: str,
        template_name: str,
        link_mapping: Dict[str, str],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Save initial tracking data to the database."""
        db = await get_mongodb()
        tracking_doc = EmailTracking(
            message_id=message_id,
            user_id=ObjectId(user_id),
            recipient_email=recipient_email,
            subject=subject,
            template_name=template_name,
            sent_at=datetime.utcnow(),
            link_mapping=link_mapping,
            metadata=metadata or {},
        )
        await db.email_tracking.insert_one(tracking_doc.model_dump(by_alias=True))

    async def _record_email_event(
        self,
        message_id: str,
        event_type: EmailEventType,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Record an email event (open, click, etc.) in the database."""
        db = await get_mongodb()
        event = EmailEvent(
            event_type=event_type,
            timestamp=datetime.utcnow(),
            ip_address=ip_address,
            user_agent=user_agent,
            details=details or {},
        )
        await db.email_tracking.update_one(
            {"message_id": message_id},
            {"$push": {"events": event.model_dump()}}
        )

    async def send_email(
        self,
        to: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        user_id: Optional[str] = None,
        template_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        track: bool = True
    ) -> Tuple[bool, Optional[str]]:
        print(f"\n📤 Preparing to send email to: {to}")
        print(f"📝 Subject: {subject}")
        print(f"🔧 Tracking enabled: {track}")
        """Send an email with optional tracking."""
        if not text_content:
            text_content = re.sub(r'<[^>]*>', ' ', html_content)
            text_content = re.sub(r'\s+', ' ', text_content).strip()

        message_id = await self._generate_message_id(to)
        link_mapping = {}
        
        if track and self.tracking_enabled and user_id:
            print("🔍 Adding email tracking...")
            html_content = self._add_tracking_pixel(html_content, message_id)
            html_content, link_mapping = self._track_links(html_content, message_id)

        msg = MIMEMultipart('alternative')
        msg['Subject'] = Header(subject, 'utf-8')
        msg['From'] = self.sender_email
        msg['To'] = to
        msg['Message-ID'] = f"<{message_id}>"

        part1 = MIMEText(text_content, 'plain', 'utf-8')
        part2 = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(part1)
        msg.attach(part2)

        try:
            print(f"🔗 Connecting to SMTP server: {self.smtp_server}:{self.smtp_port}")
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30) as server:
                print("🔐 Starting TLS...")
                server.starttls()
                print(f"🔑 Authenticating as {self.smtp_username}...")
                server.login(self.smtp_username, self.smtp_password)
                print(f"🚀 Sending email to {to}...")
                server.send_message(msg)
                print("✅ Email sent successfully!")

            if track and self.tracking_enabled and user_id:
                try:
                    await self._save_tracking_data(
                        message_id=message_id,
                        user_id=user_id,
                        recipient_email=to,
                        subject=subject,
                        template_name=template_name or "custom",
                        link_mapping=link_mapping,
                        metadata=metadata
                    )
                    await self._record_email_event(
                        message_id=message_id,
                        event_type=EmailEventType.DELIVERED,
                        details={"status": "sent"}
                    )
                except Exception as e:
                    logger.warning(f"Failed to save email tracking data for message {message_id}: {e}")
            return True, message_id
            
        except smtplib.SMTPException as e:
            error_msg = f"SMTP Error: {str(e)}"
            print(f"❌ {error_msg}")
            logger.error(error_msg)
            if track and self.tracking_enabled and user_id:
                await self._record_email_event(
                    message_id=message_id,
                    event_type=EmailEventType.BOUNCED,
                    details={"error": str(e), "status": "failed"}
                )
            return False, None
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            print(f"❌ {error_msg}")
            logger.error(error_msg, exc_info=True)
            return False, None

    async def send_price_alert(
        self,
        to: str,
        user_id: str,
        user_name: str,
        crypto_name: str,
        crypto_symbol: str,
        condition: str,
        threshold: float,
        current_price: float,
        price_change_24h: float,
        news_articles: Optional[List[Dict[str, Any]]] = None,
        dashboard_url: Optional[str] = None,
        settings_url: Optional[str] = None,
        track: bool = True,
    ) -> bool:
        """Sends a price alert email to the user."""
        settings = get_settings()
        if not hasattr(settings, 'BASE_URL'):
            settings.BASE_URL = 'http://localhost:8000'

        if dashboard_url is None:
            dashboard_url = f"{settings.BASE_URL}/dashboard"
        if settings_url is None:
            settings_url = f"{settings.BASE_URL}/settings/alerts"

        # Prepare news context for the email
        news_context = []
        if news_articles:
            for article in news_articles[:3]:  # Limit to 3 most recent articles
                news_context.append(f"- {article.get('title', 'No title')}: {article.get('url', '#')}")

        # Render the email template
        html_content = await template_renderer.render_template(
            "emails/price_alert.html",
            {
                "user_name": user_name,
                "crypto_name": crypto_name,
                "crypto_symbol": crypto_symbol,
                "condition": condition,
                "threshold": threshold,
                "current_price": current_price,
                "price_change_24h": price_change_24h,
                "news_context": "\n".join(news_context) if news_context else "No recent news available.",
                "dashboard_url": dashboard_url,
                "settings_url": settings_url,
                "has_news": bool(news_articles)
            }
        )

        # Send the email
        subject = f"{crypto_name} Price Alert: {condition} ${threshold:,.2f}"
        success, _ = await self.send_email(
            to=to,
            subject=subject,
            html_content=html_content,
            user_id=user_id,
            template_name="price_alert",
            metadata={"crypto_name": crypto_name, "condition": condition},
            track=track  # Pass the track parameter to control tracking
        )
        return success


# Global instance
email_service = EmailService()



