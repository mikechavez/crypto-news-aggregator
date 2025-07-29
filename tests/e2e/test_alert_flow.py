import logging
logging.basicConfig(level=logging.INFO, force=True)
import os
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../../.env'), override=True)

from crypto_news_aggregator.core.config import Settings
print("DEBUG E2E Settings fields:", Settings().model_dump())

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from crypto_news_aggregator.main import app
from crypto_news_aggregator.services.user_service import UserService
from crypto_news_aggregator.services.alert_service import AlertService
from crypto_news_aggregator.models.alert import AlertCreate, AlertCondition
from crypto_news_aggregator.models.user import UserCreate, UserInDB

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

@pytest_asyncio.fixture
async def test_user(client) -> UserInDB:
    user_service = UserService()
    user_data = UserCreate(email="test.e2e@example.com", password="password123", username="testuser")
    user = await user_service.create_user(user_data)
    yield user
    # The user and alerts will be cleaned up by the test database logic

@pytest_asyncio.fixture
async def test_alert(test_user):
    alert_service = AlertService()
    alert_data = AlertCreate(
        user_id=test_user.id, 
        crypto_id="bitcoin", 
        condition=AlertCondition.PERCENT_DOWN, 
        threshold=5,
        initial_price=60000  # Set a baseline price for the test
    )
    alert = await alert_service.create_alert(alert_data)
    yield alert

@pytest.mark.asyncio
@patch('crypto_news_aggregator.services.price_service.price_service.get_bitcoin_price', new_callable=AsyncMock)
@patch('crypto_news_aggregator.services.news_correlator.news_correlator.get_relevant_news', new_callable=AsyncMock)
@patch('crypto_news_aggregator.services.email_service.email_service.send_price_alert', new_callable=AsyncMock)
async def test_btc_price_alert_flow(
    mock_send_price_alert: AsyncMock,
    mock_get_relevant_news: AsyncMock,
    mock_get_bitcoin_price: AsyncMock,
    client: TestClient,
    test_user: UserInDB,
    test_alert: dict
):
    """
    Tests the end-to-end flow for a BTC price alert.
    """
    # 1. Mock external services
    # Simulate a price drop that should trigger the alert
    mock_get_bitcoin_price.return_value = {"price": 55000, "change_24h": -8.33}
    mock_get_relevant_news.return_value = [
        {"title": "BTC Dips Below 60k Amid Market Jitters", "url": "http://example.com/news1"}
    ]
    mock_send_price_alert.return_value = True

    # 2. Add a test-only endpoint to trigger the check
    from crypto_news_aggregator.services.alert_notification_service import alert_notification_service
    app.get("/test-trigger-alerts")(
        alert_notification_service.check_and_send_alerts
    )

    # 3. Trigger the check via the test endpoint
    response = client.get("/test-trigger-alerts")
    assert response.status_code == 200
    processed_count, sent_count = response.json()

    # 4. Assertions
    assert processed_count >= 1
    assert sent_count == 1

    mock_send_price_alert.assert_called_once()
    call_args = mock_send_price_alert.call_args.kwargs
    assert call_args['to'] == test_user.email
    assert call_args['crypto_symbol'] == "BTC"
    assert call_args['current_price'] == 55000
    assert len(call_args['news_articles']) == 1
    assert call_args['news_articles'][0]['title'] == "BTC Dips Below 60k Amid Market Jitters"
