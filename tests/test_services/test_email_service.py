"""
Tests for the email service.
"""
import pytest
import re
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import HTTPException
from bson import ObjectId
from datetime import datetime, timedelta

from src.crypto_news_aggregator.services.email_service import EmailService, email_service
from src.crypto_news_aggregator.models.email import EmailEventType
from src.crypto_news_aggregator.core.config import get_settings

# Test data
TEST_USER_ID = "507f1f77bcf86cd799439011"
TEST_EMAIL = "test@example.com"
TEST_SUBJECT = "Test Email"
TEST_HTML_CONTENT = "<html><body><h1>Test</h1><a href='https://example.com'>Link</a></body></html>"
TEST_TEXT_CONTENT = "Test email content"

# Mock the database
@pytest.fixture
def mock_db():
    with patch('src.crypto_news_aggregator.services.email_service.get_mongodb') as mock_get_db:
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        mock_db.email_tracking = AsyncMock()
        mock_db.users = AsyncMock()
        yield mock_db

# Test the email service
class TestEmailService:
    """Tests for the EmailService class."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.service = EmailService()
        self.service.tracking_enabled = True  # Enable tracking for tests
        
    def test_generate_message_id(self):
        """Test that message IDs are generated correctly."""
        message_id = self.service._generate_message_id(TEST_EMAIL)
        assert isinstance(message_id, str)
        assert len(message_id) == 64  # SHA-256 produces 64-character hex string
        
    def test_hash_url(self):
        """Test that URLs are hashed correctly."""
        url = "https://example.com/test"
        hashed = self.service._hash_url(url)
        assert isinstance(hashed, str)
        assert len(hashed) == 32  # MD5 produces 32-character hex string
        
    def test_add_tracking_pixel(self):
        """Test that tracking pixels are added to HTML content."""
        message_id = "test_message_id"
        result = self.service._add_tracking_pixel(TEST_HTML_CONTENT, message_id)
        
        # Check that the tracking pixel was added
        assert f"track/open/{message_id}" in result
        assert "<img" in result
        
    def test_track_links(self):
        """Test that links are tracked correctly."""
        message_id = "test_message_id"
        result, link_mapping = self.service._track_links(TEST_HTML_CONTENT, message_id)
        
        # Check that the link was replaced with a tracking URL
        assert "track/click/" in result
        assert "example.com" not in result  # Original URL should be replaced
        
        # Check that the link mapping was created
        assert len(link_mapping) == 1
        assert any("example.com" in url for url in link_mapping.values())
        
    @pytest.mark.asyncio
    async def test_save_tracking_data(self, mock_db):
        """Test that tracking data is saved to the database."""
        message_id = "test_message_id"
        link_mapping = {"abc123": "https://example.com"}
        
        await self.service._save_tracking_data(
            message_id=message_id,
            user_id=TEST_USER_ID,
            recipient_email=TEST_EMAIL,
            subject=TEST_SUBJECT,
            template_name="test_template",
            link_mapping=link_mapping,
            metadata={"test": "test"}
        )
        
        # Check that insert_one was called with the correct data
        args, _ = mock_db.email_tracking.insert_one.call_args
        assert len(args) == 1
        assert args[0]["message_id"] == message_id
        assert args[0]["user_id"] == ObjectId(TEST_USER_ID)
        assert args[0]["recipient_email"] == TEST_EMAIL
        assert args[0]["subject"] == TEST_SUBJECT
        assert args[0]["metadata"]["test"] == "test"
        assert args[0]["metadata"]["links"] == link_mapping
        
    @pytest.mark.asyncio
    async def test_record_email_event(self, mock_db):
        """Test that email events are recorded correctly."""
        message_id = "test_message_id"
        event_type = EmailEventType.OPENED
        details = {"test": "test"}
        
        # Mock the update result
        mock_db.email_tracking.update_one.return_value.modified_count = 1
        
        result = await self.service._record_email_event(
            message_id=message_id,
            event_type=event_type,
            details=details,
            ip_address="127.0.0.1",
            user_agent="test"
        )
        
        # Check that the event was recorded
        assert result is True
        mock_db.email_tracking.update_one.assert_called_once()
        
    @pytest.mark.asyncio
    @patch('smtplib.SMTP_SSL')
    async def test_send_email_success(self, mock_smtp, mock_db):
        """Test sending an email successfully."""
        # Mock the SMTP server
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        # Mock the database
        mock_db.email_tracking.insert_one.return_value = None
        
        # Send the email
        success, message_id = await self.service.send_email(
            to=TEST_EMAIL,
            subject=TEST_SUBJECT,
            html_content=TEST_HTML_CONTENT,
            user_id=TEST_USER_ID,
            template_name="test_template"
        )
        
        # Check that the email was sent
        assert success is True
        assert message_id is not None
        
        # Check that the SMTP server was called
        settings = get_settings()
        mock_smtp.assert_called_once_with(settings.SMTP_SERVER, settings.SMTP_PORT)
        mock_server.login.assert_called_once()
        mock_server.send_message.assert_called_once()
        
        # Check that tracking data was saved
        mock_db.email_tracking.insert_one.assert_called_once()
        
    @pytest.mark.asyncio
    @patch('smtplib.SMTP_SSL')
    async def test_send_email_failure(self, mock_smtp):
        """Test handling of email sending failure."""
        # Mock the SMTP server to raise an exception
        mock_smtp.return_value.__enter__.side_effect = Exception("SMTP Error")
        
        # Send the email
        success, message_id = await self.service.send_email(
            to=TEST_EMAIL,
            subject=TEST_SUBJECT,
            html_content=TEST_HTML_CONTENT,
            user_id=TEST_USER_ID
        )
        
        # Check that the email sending failed
        assert success is False
        assert message_id is None
        
    @pytest.mark.asyncio
    async def test_send_price_alert(self, mock_db):
        """Test sending a price alert email."""
        # Mock the template renderer
        with patch('src.crypto_news_aggregator.services.email_service.template_renderer') as mock_renderer:
            mock_renderer.render_template.return_value = TEST_HTML_CONTENT
            
            # Mock the send_email method
            with patch.object(self.service, 'send_email', new_callable=AsyncMock) as mock_send_email:
                mock_send_email.return_value = (True, "test_message_id")
                
                # Send a price alert
                result = await self.service.send_price_alert(
                    to=TEST_EMAIL,
                    user_id=TEST_USER_ID,
                    user_name="Test User",
                    crypto_name="Bitcoin",
                    crypto_symbol="BTC",
                    condition="ABOVE",
                    threshold=50000,
                    current_price=51000,
                    price_change_24h=5.5
                )
                
                # Check that the email was sent
                assert result is True
                mock_send_email.assert_called_once()
                
                # Check the email content
                _, kwargs = mock_send_email.call_args
                assert kwargs["to"] == TEST_EMAIL
                assert "Bitcoin" in kwargs["subject"]
                assert "51000" in kwargs["text_content"]
                assert kwargs["user_id"] == TEST_USER_ID
                assert kwargs["template_name"] == "price_alert"
                assert kwargs["metadata"]["crypto_name"] == "Bitcoin"
                assert kwargs["metadata"]["crypto_symbol"] == "BTC"
