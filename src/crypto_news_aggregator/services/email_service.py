"""
Email service for sending alerts and notifications.
"""
import logging
from typing import Any, Dict, List, Optional, Union
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

from ..core.config import settings
from ..utils.template_renderer import template_renderer

logger = logging.getLogger(__name__)

class EmailService:
    """Service for sending email notifications."""
    
    def __init__(self):
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.sender_email = settings.EMAIL_FROM
    
    async def send_email(
        self,
        to: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> bool:
        """
        Send an email.
        
        Args:
            to: Recipient email address
            subject: Email subject
            html_content: HTML content of the email
            text_content: Plain text content (optional, will be auto-generated if not provided)
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        if not text_content:
            # Simple HTML to text conversion
            import re
            text_content = re.sub(r'<[^>]*>', ' ', html_content)
            text_content = re.sub(r'\s+', ' ', text_content).strip()
        
        # Create message container
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.sender_email
        msg['To'] = to
        
        # Attach parts
        part1 = MIMEText(text_content, 'plain')
        part2 = MIMEText(html_content, 'html')
        
        msg.attach(part1)
        msg.attach(part2)
        
        try:
            # Send the email
            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                if self.smtp_username and self.smtp_password:
                    server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email sent to {to} with subject: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to}: {e}", exc_info=True)
            return False

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
        dashboard_url: Optional[str] = None,
        settings_url: Optional[str] = None,
    ) -> bool:
        """
        Send a price alert email.
        
        Args:
            to: Recipient email address
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
        if not hasattr(settings, 'BASE_URL'):
            settings.BASE_URL = 'http://localhost:8000'
            
        if dashboard_url is None:
            dashboard_url = f"{settings.BASE_URL}/dashboard"
        if settings_url is None:
            settings_url = f"{settings.BASE_URL}/settings"
        
        # Render the email template
        html_content = await template_renderer.render_template(
            'emails/price_alert.html',
            {
                'user_name': user_name,
                'crypto_name': crypto_name,
                'crypto_symbol': crypto_symbol,
                'condition': condition,
                'threshold': threshold,
                'current_price': current_price,
                'price_change_24h': price_change_24h,
                'dashboard_url': dashboard_url,
                'settings_url': settings_url,
                'trigger_time': datetime.utcnow().isoformat(),
            }
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
) -> bool:
    """
    Send an email alert using the global email service.
    
    Args:
        to: Recipient email address
        subject: Email subject
        html_content: HTML content of the email
        text_content: Plain text content (optional)
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    return await email_service.send_email(
        to=to,
        subject=subject,
        html_content=html_content,
        text_content=text_content,
    )


async def send_price_alert(
    to: str,
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
    return await email_service.send_price_alert(
        to=to,
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
