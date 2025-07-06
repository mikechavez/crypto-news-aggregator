import asyncio
import os
import sys
from pathlib import Path

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
        "user_name": "Test User",
        "crypto_name": "Bitcoin",
        "crypto_symbol": "BTC",
        "condition": "above",
        "threshold": 50000.0,
        "current_price": 52000.0,
        "price_change_24h": 5.2,
        "dashboard_url": "http://localhost:8000/dashboard",
        "settings_url": "http://localhost:8000/settings"
    }
    
    try:
        success = await email_service.send_price_alert(**test_data)
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
    required_vars = ["SMTP_SERVER", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD"]
    missing_vars = [var for var in required_vars if not getattr(settings, var, None)]
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nPlease set these variables in your .env file or environment.")
        sys.exit(1)
    
    asyncio.run(test_email_notification())
