"""
Integration tests for email tracking functionality.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from bson import ObjectId
from datetime import datetime, timedelta

from src.crypto_news_aggregator.models.email import EmailEventType
from src.crypto_news_aggregator.core.security import create_access_token

# Test data
TEST_USER_ID = str(ObjectId())
TEST_EMAIL = "test@example.com"
TEST_MESSAGE_ID = "test_message_id"
TEST_LINK_HASH = "abc123"
TEST_ORIGINAL_URL = "https://example.com"
TEST_UNSUBSCRIBE_TOKEN = "test_unsubscribe_token"

# Fixtures
@pytest.fixture
def auth_headers():
    """Generate authentication headers with a test token."""
    token = create_access_token(subject=TEST_USER_ID)
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def mock_db():
    """Mock the database for testing."""
    with patch('src.crypto_news_aggregator.api.v1.endpoints.emails.get_mongodb') as mock_get_db:
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        
        # Mock the email_tracking collection
        mock_db.email_tracking = AsyncMock()
        
        # Mock the users collection
        mock_db.users = AsyncMock()
        
        yield mock_db

# Tests
class TestEmailTrackingEndpoints:
    """Tests for email tracking endpoints."""
    
    async def test_track_email_open(self, client: TestClient, mock_db):
        """Test tracking an email open event."""
        # Mock the database response
        mock_db.email_tracking.update_one.return_value.modified_count = 1
        
        # Make the request
        response = client.get(
            f"/api/v1/emails/track/open/{TEST_MESSAGE_ID}",
            headers={"User-Agent": "test-agent"},
            allow_redirects=False
        )
        
        # Check the response
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/gif"
        
        # Check that the database was updated
        mock_db.email_tracking.update_one.assert_called_once()
        
    async def test_track_email_click(self, client: TestClient, mock_db):
        """Test tracking an email link click."""
        # Mock the database response
        mock_db.email_tracking.find_one.return_value = {
            "_id": ObjectId(),
            "message_id": TEST_MESSAGE_ID,
            "user_id": ObjectId(TEST_USER_ID),
            "metadata": {
                "links": {
                    TEST_LINK_HASH: TEST_ORIGINAL_URL
                }
            }
        }
        
        # Make the request
        response = client.get(
            f"/api/v1/emails/track/click/{TEST_MESSAGE_ID}/{TEST_LINK_HASH}",
            headers={"User-Agent": "test-agent"},
            allow_redirects=False
        )
        
        # Check the response
        assert response.status_code == 307  # Temporary redirect
        assert response.headers["location"] == TEST_ORIGINAL_URL
        
        # Check that the database was updated
        mock_db.email_tracking.update_one.assert_called_once()
        
    async def test_unsubscribe(self, client: TestClient, mock_db):
        """Test the unsubscribe endpoint."""
        # Mock the database response
        mock_db.users.update_one.return_value.modified_count = 1
        
        # Make the request
        response = client.get(
            f"/api/v1/emails/unsubscribe/{TEST_UNSUBSCRIBE_TOKEN}",
            allow_redirects=False
        )
        
        # Check the response
        assert response.status_code == 200
        assert "unsubscribe" in response.text.lower()
        
        # Check that the database was updated
        mock_db.users.update_one.assert_called_once()
        
    async def test_get_tracking_info(self, client: TestClient, mock_db, auth_headers):
        """Test getting tracking info for a message."""
        # Mock the database response
        test_tracking_data = {
            "_id": ObjectId(),
            "message_id": TEST_MESSAGE_ID,
            "user_id": ObjectId(TEST_USER_ID),
            "recipient_email": TEST_EMAIL,
            "subject": "Test Email",
            "events": [
                {
                    "event_type": EmailEventType.SENT.value,
                    "timestamp": datetime.utcnow() - timedelta(minutes=10)
                },
                {
                    "event_type": EmailEventType.OPENED.value,
                    "timestamp": datetime.utcnow() - timedelta(minutes=5),
                    "ip_address": "127.0.0.1",
                    "user_agent": "test-agent"
                }
            ],
            "metadata": {
                "template_name": "test_template",
                "links": {}
            }
        }
        mock_db.email_tracking.find_one.return_value = test_tracking_data
        
        # Make the request
        response = client.get(
            f"/api/v1/emails/tracking/{TEST_MESSAGE_ID}",
            headers=auth_headers
        )
        
        # Check the response
        assert response.status_code == 200
        data = response.json()
        assert data["message_id"] == TEST_MESSAGE_ID
        assert data["recipient_email"] == TEST_EMAIL
        assert len(data["events"]) == 2
        assert data["events"][0]["event_type"] == EmailEventType.SENT.value
        assert data["events"][1]["event_type"] == EmailEventType.OPENED.value
        
    async def test_get_user_tracking_info(self, client: TestClient, mock_db, auth_headers):
        """Test getting tracking info for a user."""
        # Mock the database response
        test_tracking_data = [
            {
                "_id": ObjectId(),
                "message_id": f"{TEST_MESSAGE_ID}_1",
                "subject": "Test Email 1",
                "sent_at": datetime.utcnow() - timedelta(hours=1),
                "events": [
                    {"event_type": EmailEventType.SENT.value, "timestamp": datetime.utcnow() - timedelta(hours=1)},
                    {"event_type": EmailEventType.OPENED.value, "timestamp": datetime.utcnow() - timedelta(minutes=55)}
                ]
            },
            {
                "_id": ObjectId(),
                "message_id": f"{TEST_MESSAGE_ID}_2",
                "subject": "Test Email 2",
                "sent_at": datetime.utcnow() - timedelta(hours=2),
                "events": [
                    {"event_type": EmailEventType.SENT.value, "timestamp": datetime.utcnow() - timedelta(hours=2)}
                ]
            }
        ]
        
        # Mock the cursor
        mock_cursor = AsyncMock()
        mock_cursor.to_list.return_value = test_tracking_data
        mock_db.email_tracking.find.return_value = mock_cursor
        
        # Make the request
        response = client.get(
            f"/api/v1/emails/tracking/user/{TEST_USER_ID}?limit=10&skip=0",
            headers=auth_headers
        )
        
        # Check the response
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["message_id"] == f"{TEST_MESSAGE_ID}_1"
        assert data[0]["open_count"] == 1
        assert data[1]["message_id"] == f"{TEST_MESSAGE_ID}_2"
        assert data[1]["open_count"] == 0
        
        # Check that the database was queried with the correct parameters
        mock_db.email_tracking.find.assert_called_once()
        args, _ = mock_db.email_tracking.find.call_args
        assert args[0]["user_id"] == ObjectId(TEST_USER_ID)
        
    async def test_unauthorized_access_to_tracking_info(self, client: TestClient, mock_db):
        """Test that unauthorized users cannot access tracking info."""
        # Make the request without authentication
        response = client.get(f"/api/v1/emails/tracking/{TEST_MESSAGE_ID}")
        
        # Check the response
        assert response.status_code == 401
        
    async def test_unauthorized_access_to_user_tracking_info(self, client: TestClient, mock_db):
        """Test that users cannot access other users' tracking info."""
        # Create a token for a different user
        other_user_id = str(ObjectId())
        token = create_access_token(data={"sub": other_user_id})
        headers = {"Authorization": f"Bearer {token}"}
        
        # Make the request
        response = client.get(
            f"/api/v1/emails/tracking/user/{TEST_USER_ID}",
            headers=headers
        )
        
        # Check the response
        assert response.status_code == 403
        
    async def test_admin_access_to_user_tracking_info(self, client: TestClient, mock_db):
        """Test that admins can access any user's tracking info."""
        # Create an admin token
        admin_token = create_access_token(data={"sub": "admin_user_id", "is_admin": True})
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Mock the database response
        mock_cursor = AsyncMock()
        mock_cursor.to_list.return_value = []
        mock_db.email_tracking.find.return_value = mock_cursor
        
        # Make the request
        response = client.get(
            f"/api/v1/emails/tracking/user/{TEST_USER_ID}",
            headers=headers
        )
        
        # Check the response
        assert response.status_code == 200
        assert response.json() == []
        
        # Check that the database was queried with the correct parameters
        mock_db.email_tracking.find.assert_called_once()
        args, _ = mock_db.email_tracking.find.call_args
        assert args[0]["user_id"] == ObjectId(TEST_USER_ID)
