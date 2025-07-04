"""
Email service for sending alerts and notifications.
"""
import logging
from typing import List, Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from ..core.config import settings

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
        text_content=text_content
    )
