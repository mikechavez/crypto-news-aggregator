"""
Email service for sending alerts and notifications with tracking capabilities.
"""
import logging
import uuid
import hashlib
import json
import re
from typing import Any, Dict, List, Optional, Union, Tuple
import smtplib
import urllib.parse
from email.header import Header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from datetime import datetime
from urllib.parse import urlencode, urljoin

from bson import ObjectId

from ..core.config import settings
from ..utils.template_renderer import template_renderer
from ..db.mongodb import get_database
from ..models.user import UserInDB, UserTrackingSettings
from ..db.mongodb_models import EmailTracking, EmailEvent, EmailEventType

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
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.sender_email = settings.EMAIL_FROM
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
        <div style="display:none;">
            <img src="{self.tracking_pixel_url.format(message_id=message_id)}" 
                 alt="" width="1" height="1" style="border:none;width:1px;height:1px;" />
        </div>
        """
        # Add tracking pixel before the closing body tag
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
            # Skip mailto: and other non-http links
            if not original_url.startswith(('http://', 'https://')):
                continue
                
            # Create a hash of the URL for tracking
            link_hash = self._hash_url(original_url)
            tracking_url = self.tracking_click_url.format(
                message_id=message_id,
                link_hash=link_hash
            )
            
            # Store the mapping
            link_mapping[link_hash] = original_url
            
            # Update the href to use the tracking URL
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
    ) -> None:
        """Save initial tracking data to the database."""
        if not self.tracking_enabled:
            return
            
        db = await get_database()
        tracking_data = {
            "message_id": message_id,
            "user_id": ObjectId(user_id),
            "recipient_email": recipient_email,
            "subject": subject,
            "template_name": template_name,
            "sent_at": datetime.utcnow(),
            "events": [{
                "event_type": EmailEventType.SENT,
                "timestamp": datetime.utcnow(),
                "details": {"status": "queued"}
            }],
            "metadata": {
                "links": link_mapping,
                "tracking_enabled": True,
                **(metadata or {})
            }
        }
        
        await db.email_tracking.insert_one(tracking_data)
    
    async def _record_email_event(
        self,
        message_id: str,
        event_type: EmailEventType,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """Record an email event (open, click, etc.) in the database."""
        if not self.tracking_enabled:
            return False
            
        db = await get_database()
        event = {
            "event_type": event_type,
            "timestamp": datetime.utcnow(),
            "details": details or {},
        }
        
        if ip_address:
            event["ip_address"] = ip_address
        if user_agent:
            event["user_agent"] = user_agent
        
        result = await db.email_tracking.update_one(
            {"message_id": message_id},
            {
                "$push": {"events": event},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        return result.modified_count > 0

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
        """
        Send an email with optional tracking.
        
        Args:
            to: Recipient email address
            subject: Email subject
            html_content: HTML content of the email
            text_content: Plain text content (optional, will be auto-generated if not provided)
            user_id: ID of the user receiving the email (required for tracking)
            template_name: Name of the email template (for tracking)
            metadata: Additional metadata to store with the email
            track: Whether to enable tracking for this email
            
        Returns:
            Tuple of (success: bool, message_id: Optional[str])
        """
        if not text_content:
            # Simple HTML to text conversion
            text_content = re.sub(r'<[^>]*>', ' ', html_content)
            text_content = re.sub(r'\s+', ' ', text_content).strip()
        
        # Generate a unique message ID for tracking
        message_id = await self._generate_message_id(to)
        
        # Process HTML content for tracking if enabled
        link_mapping = {}
        if track and self.tracking_enabled and user_id:
            # Add tracking pixel
            html_content = self._add_tracking_pixel(html_content, message_id)
            
            # Process links for click tracking
            html_content, link_mapping = self._track_links(html_content, message_id)
            
            # Save tracking data to database
            await self._save_tracking_data(
                message_id=message_id,
                user_id=user_id,
                recipient_email=to,
                subject=subject,
                template_name=template_name or "custom",
                link_mapping=link_mapping,
                metadata=metadata
            )
        
        # Create message container
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.sender_email
        msg['To'] = to
        msg['Message-ID'] = f"<{message_id}@{settings.EMAIL_DOMAIN or 'cryptonewsaggregator.com'}>"
        
        # Add List-Unsubscribe header if tracking is enabled
        if track and self.tracking_enabled and user_id:
            unsubscribe_token = hashlib.sha256(f"{user_id}-{to}-{message_id}".encode()).hexdigest()
            unsubscribe_url = self.unsubscribe_url.format(token=unsubscribe_token)
            msg.add_header('List-Unsubscribe', f'<{unsubscribe_url}>', method='POST')
        
        # Attach parts
        part1 = MIMEText(text_content, 'plain', 'utf-8')
        part2 = MIMEText(html_content, 'html', 'utf-8')
        
        msg.attach(part1)
        msg.attach(part2)
        
        try:
            # Send the email
            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                if self.smtp_username and self.smtp_password:
                    server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email sent to {to} with subject: {subject}")
            
            # Record the sent event
            if track and self.tracking_enabled and user_id:
                await self._record_email_event(
                    message_id=message_id,
                    event_type=EmailEventType.DELIVERED,
                    details={"status": "sent"}
                )
            
            return True, message_id
            
        except Exception as e:
            logger.error(f"Failed to send email to {to}: {e}", exc_info=True)
            
            # Record the failure
            if track and self.tracking_enabled and user_id:
                await self._record_email_event(
                    message_id=message_id,
                    event_type=EmailEventType.BOUNCED,
                    details={"error": str(e), "status": "failed"}
                )
            
            return False, None

    async def send_price_alert(
        self,
        to: str,
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
    ) -> bool:
        """
        Send a price alert email with optional news context.
        
        Args:
            to: Recipient email address
            user_name: Name of the user
            crypto_name: Name of the cryptocurrency
            crypto_symbol: Symbol of the cryptocurrency (e.g., BTC)
            condition: Alert condition that was triggered
            threshold: Price or percentage threshold
            current_price: Current price of the cryptocurrency
            price_change_24h: 24-hour price change percentage
            news_articles: List of relevant news articles (optional)
            dashboard_url: URL to the user's dashboard (optional)
            settings_url: URL to the user's settings (optional)
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        if not hasattr(settings, 'BASE_URL'):
            settings.BASE_URL = 'http://localhost:8000'
            
        if dashboard_url is None:
            dashboard_url = f"{settings.BASE_URL}/dashboard"
        if settings_url is None:
            settings_url = f"{settings.BASE_URL}/settings"
        
        # Prepare news context if available
        news_context = []
        if news_articles:
            for article in news_articles[:3]:  # Limit to 3 most relevant articles
                news_context.append({
                    'title': article.get('title', 'No title'),
                    'source': article.get('source', {}).get('name', 'Unknown source'),
                    'url': article.get('url', '#'),
                    'published_at': article.get('published_at', ''),
                    'snippet': article.get('description', '')[:200] + '...' if article.get('description') else ''
                })

        # Render the email template
        context = {
            'user_name': user_name,
            'crypto_name': crypto_name,
            'crypto_symbol': crypto_symbol.upper(),
            'condition': condition,
            'threshold': threshold,
            'current_price': current_price,
            'price_change_24h': price_change_24h,
            'dashboard_url': dashboard_url or '#',
            'settings_url': settings_url or '#',
            'current_year': datetime.now().year,
            'has_news': bool(news_articles),
            'news_articles': news_context,
        }
        
        html_content = await template_renderer.render_template(
            'emails/price_alert.html',
            context
        )
        
        # Create a subject line
        direction = "above" if condition in ["above", "percent_up"] else "below"
        subject = f"🔔 {crypto_symbol.upper()} Price Alert: {direction.upper()} {threshold}%"
        
        return await self.send_email(to, subject, html_content)

# Global instance
email_service = EmailService()


async def send_email_alert(
    to: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None,
    user_id: Optional[str] = None,
    template_name: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    track: bool = True
) -> Tuple[bool, Optional[str]]:
    """
    Send an email alert using the global email service.
    
    Args:
        to: Recipient email address
        subject: Email subject
        html_content: HTML content of the email
        text_content: Plain text content (optional)
        user_id: ID of the user receiving the email (required for tracking)
        template_name: Name of the email template (for tracking)
        metadata: Additional metadata to store with the email
        track: Whether to enable tracking for this email
        
    Returns:
        Tuple of (success: bool, message_id: Optional[str])
    """
    return await email_service.send_email(
        to=to,
        subject=subject,
        html_content=html_content,
        text_content=text_content,
        user_id=user_id,
        template_name=template_name,
        metadata=metadata,
        track=track
    )


async def send_price_alert(
    to: str,
    user_id: str,
    user_name: str,
    crypto_name: str,
    crypto_symbol: str,
    condition: str,
    threshold: float,
    current_price: float,
    price_change_24h: float,
    dashboard_url: Optional[str] = None,
    settings_url: Optional[str] = None,
) -> bool:
    """
    Send a price alert email using the global email service.
    
    Args:
        to: Recipient email address
        user_id: ID of the user receiving the alert (required for tracking)
        user_name: Name of the user
        crypto_name: Name of the cryptocurrency
        crypto_symbol: Symbol of the cryptocurrency (e.g., BTC)
        condition: Alert condition that was triggered
        threshold: Price or percentage threshold
        current_price: Current price of the cryptocurrency
        price_change_24h: 24-hour price change percentage
        dashboard_url: URL to the user's dashboard (optional)
        settings_url: URL to the user's settings (optional)
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    # Render the email template
    html_content = template_renderer.render_template(
        "emails/price_alert.html",
        user_name=user_name,
        crypto_name=crypto_name,
        crypto_symbol=crypto_symbol,
        condition=condition,
        threshold=threshold,
        current_price=current_price,
        price_change_24h=price_change_24h,
        dashboard_url=dashboard_url,
        settings_url=settings_url,
    )
    
    # Generate plain text version
    text_content = f"""
    {user_name},
    
    Your price alert for {crypto_name} ({crypto_symbol}) has been triggered!
    
    Condition: {condition}
    Threshold: {threshold}
    Current Price: {current_price}
    24h Change: {price_change_24h}%
    """
    
    if dashboard_url:
        text_content += f"\nView your dashboard: {dashboard_url}"
    
    # Send the email with tracking
    success, _ = await email_service.send_email(
        to=to,
        subject=f"{crypto_symbol} Price Alert: {condition} {threshold}",
        html_content=html_content,
        text_content=text_content.strip(),
        user_id=user_id,
        template_name="price_alert",
        metadata={
            "crypto_name": crypto_name,
            "crypto_symbol": crypto_symbol,
            "condition": condition,
            "threshold": threshold,
            "current_price": current_price,
            "price_change_24h": price_change_24h
        },
        track=True
    )
    
    return success
