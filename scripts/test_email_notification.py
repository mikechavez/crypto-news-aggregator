import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

from src.crypto_news_aggregator.core.config import settings
from src.crypto_news_aggregator.services.email_service import EmailService


async def test_email_notification():
    """Test sending a price alert email."""
    email_service = EmailService()

    test_data = {
        "to": settings.ALERT_EMAIL or "test@example.com",
        "user_id": "test_user_123",
        "user_name": "Test User",
        "crypto_name": "Bitcoin",
        "crypto_symbol": "BTC",
        "condition": "above",
        "threshold": 50000.0,
        "current_price": 52000.0,
        "price_change_24h": 5.2,
        "news_articles": [
            {
                "title": "Bitcoin Reaches New All-Time High",
                "source": "Crypto News",
                "url": "https://example.com/bitcoin-news",
                "published_at": "2023-01-01T12:00:00Z",
                "snippet": "Bitcoin has reached a new all-time high of $52,000, surpassing the previous record.",
            },
            {
                "title": "Institutional Investors Flock to Bitcoin",
                "source": "Blockchain Daily",
                "url": "https://example.com/institutional-investors",
                "published_at": "2023-01-01T10:30:00Z",
                "snippet": "Major financial institutions are increasing their Bitcoin holdings as adoption grows.",
            },
        ],
        "dashboard_url": "http://localhost:8000/dashboard",
        "settings_url": "http://localhost:8000/settings",
    }

    try:
        # Send test email with tracking disabled
        success = await email_service.send_price_alert(track=False, **test_data)
        if success:
            print("✅ Test email sent successfully!")
            print(f"Check {test_data['to']} for the test email.")
        else:
            print("❌ Failed to send test email")
    except Exception as e:
        print(f"❌ Error sending test email: {e}")
        raise


if __name__ == "__main__":
    # Check if we have the required SMTP settings
    required_vars = [
        "SMTP_SERVER",
        "SMTP_PORT",
        "SMTP_USERNAME",
        "SMTP_PASSWORD",
        "ALERT_EMAIL",
    ]
    missing_vars = [var for var in required_vars if not getattr(settings, var, None)]

    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nPlease set these variables in your .env file or environment.")
        sys.exit(1)

    # Debug: Show SMTP settings being used
    print("\n📧 SMTP Configuration:")
    print(f"SMTP Server: {settings.SMTP_SERVER}")
    print(f"SMTP Port: {settings.SMTP_PORT}")
    print(f"SMTP Username: {settings.SMTP_USERNAME}")
    print(f"Alert Email: {settings.ALERT_EMAIL}")
    print("\nSending test email...")

    asyncio.run(test_email_notification())
