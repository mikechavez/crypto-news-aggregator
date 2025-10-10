"""
Tests for signals API endpoints.
"""

import pytest
import pytest_asyncio
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from crypto_news_aggregator.main import app
from crypto_news_aggregator.db.mongodb import mongo_manager
from crypto_news_aggregator.db.operations.signal_scores import upsert_signal_score
from crypto_news_aggregator.core.config import get_settings


def get_test_client():
    """Helper to create AsyncClient with proper transport."""
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest_asyncio.fixture
async def test_signal_data():
    """Create test signal score data."""
    db = await mongo_manager.get_async_database()
    collection = db.signal_scores
    
    # Clean up existing test data
    await collection.delete_many({"entity": {"$in": ["$BTC", "$ETH", "Bitcoin"]}})
    
    # Create test signal scores with multi-timeframe data
    await upsert_signal_score(
        entity="$BTC",
        entity_type="ticker",
        score=8.5,
        velocity=12.3,
        source_count=15,
        sentiment={"avg": 0.7, "min": -0.2, "max": 1.0, "divergence": 0.3},
        first_seen=datetime.now(timezone.utc),
        # Multi-timeframe fields
        score_24h=9.2,
        score_7d=8.5,
        score_30d=7.1,
        velocity_24h=15.0,
        velocity_7d=12.3,
        velocity_30d=8.5,
    )
    
    await upsert_signal_score(
        entity="$ETH",
        entity_type="ticker",
        score=6.2,
        velocity=8.1,
        source_count=10,
        sentiment={"avg": 0.4, "min": -0.1, "max": 0.9, "divergence": 0.25},
        first_seen=datetime.now(timezone.utc),
        # Multi-timeframe fields - ETH is stronger in 30d
        score_24h=5.5,
        score_7d=6.2,
        score_30d=8.8,
        velocity_24h=6.0,
        velocity_7d=8.1,
        velocity_30d=11.5,
    )
    
    await upsert_signal_score(
        entity="Bitcoin",
        entity_type="project",
        score=7.8,
        velocity=10.5,
        source_count=12,
        sentiment={"avg": 0.6, "min": 0.0, "max": 1.0, "divergence": 0.28},
        first_seen=datetime.now(timezone.utc),
        # Multi-timeframe fields
        score_24h=7.0,
        score_7d=7.8,
        score_30d=7.5,
        velocity_24h=9.0,
        velocity_7d=10.5,
        velocity_30d=9.8,
    )
    
    yield
    
    # Clean up after tests
    await collection.delete_many({"entity": {"$in": ["$BTC", "$ETH", "Bitcoin"]}})


@pytest.mark.asyncio
async def test_get_trending_signals_default(test_signal_data):
    """Test getting trending signals with default parameters."""
    settings = get_settings()
    
    async with get_test_client() as client:
        response = await client.get(
            f"{settings.API_V1_STR}/signals/trending",
            headers={"X-API-Key": settings.API_KEY}
        )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "count" in data
    assert "filters" in data
    assert "signals" in data
    
    # Should return signals sorted by score
    assert data["count"] > 0
    assert len(data["signals"]) <= 50  # Default limit
    
    # Check first signal has highest score
    if len(data["signals"]) > 1:
        assert data["signals"][0]["signal_score"] >= data["signals"][1]["signal_score"]


@pytest.mark.asyncio
async def test_get_trending_signals_with_limit(test_signal_data):
    """Test getting trending signals with custom limit."""
    settings = get_settings()
    
    async with get_test_client() as client:
        response = await client.get(
            f"{settings.API_V1_STR}/signals/trending?limit=2",
            headers={"X-API-Key": settings.API_KEY}
        )
    
    assert response.status_code == 200
    data = response.json()
    
    assert len(data["signals"]) <= 2
    assert data["filters"]["limit"] == 2


@pytest.mark.asyncio
async def test_get_trending_signals_with_min_score(test_signal_data):
    """Test getting trending signals with minimum score filter."""
    settings = get_settings()
    
    async with get_test_client() as client:
        response = await client.get(
            f"{settings.API_V1_STR}/signals/trending?min_score=7.0",
            headers={"X-API-Key": settings.API_KEY}
        )
    
    assert response.status_code == 200
    data = response.json()
    
    # All returned signals should have score >= 7.0
    for signal in data["signals"]:
        assert signal["signal_score"] >= 7.0
    
    assert data["filters"]["min_score"] == 7.0


@pytest.mark.asyncio
async def test_get_trending_signals_filter_by_type(test_signal_data):
    """Test filtering signals by entity type."""
    settings = get_settings()
    
    async with get_test_client() as client:
        response = await client.get(
            f"{settings.API_V1_STR}/signals/trending?entity_type=ticker",
            headers={"X-API-Key": settings.API_KEY}
        )
    
    assert response.status_code == 200
    data = response.json()
    
    # All returned signals should be tickers
    for signal in data["signals"]:
        assert signal["entity_type"] == "ticker"
    
    assert data["filters"]["entity_type"] == "ticker"


@pytest.mark.asyncio
async def test_get_trending_signals_invalid_entity_type(test_signal_data):
    """Test error handling for invalid entity type."""
    settings = get_settings()
    
    async with get_test_client() as client:
        response = await client.get(
            f"{settings.API_V1_STR}/signals/trending?entity_type=invalid",
            headers={"X-API-Key": settings.API_KEY}
        )
    
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_trending_signals_response_structure(test_signal_data):
    """Test the structure of the response."""
    settings = get_settings()
    
    async with get_test_client() as client:
        response = await client.get(
            f"{settings.API_V1_STR}/signals/trending",
            headers={"X-API-Key": settings.API_KEY}
        )
    
    assert response.status_code == 200
    data = response.json()
    
    # Check top-level structure
    assert "count" in data
    assert "filters" in data
    assert "signals" in data
    
    # Check filters structure
    assert "limit" in data["filters"]
    assert "min_score" in data["filters"]
    assert "entity_type" in data["filters"]
    
    # Check signal structure
    if data["signals"]:
        signal = data["signals"][0]
        assert "entity" in signal
        assert "entity_type" in signal
        assert "signal_score" in signal
        assert "velocity" in signal
        assert "source_count" in signal
        assert "sentiment" in signal
        assert "first_seen" in signal
        assert "last_updated" in signal
        
        # Check sentiment structure
        assert "avg" in signal["sentiment"]
        assert "min" in signal["sentiment"]
        assert "max" in signal["sentiment"]
        assert "divergence" in signal["sentiment"]


@pytest.mark.asyncio
async def test_get_trending_signals_no_api_key():
    """Test that endpoint requires API key."""
    settings = get_settings()
    
    async with get_test_client() as client:
        response = await client.get(
            f"{settings.API_V1_STR}/signals/trending"
        )
    
    # Should return 403 Forbidden without API key
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_trending_signals_caching(test_signal_data):
    """Test that results are cached."""
    settings = get_settings()
    
    async with get_test_client() as client:
        # First request
        response1 = await client.get(
            f"{settings.API_V1_STR}/signals/trending",
            headers={"X-API-Key": settings.API_KEY}
        )
        
        # Second request (should be cached)
        response2 = await client.get(
            f"{settings.API_V1_STR}/signals/trending",
            headers={"X-API-Key": settings.API_KEY}
        )
    
    assert response1.status_code == 200
    assert response2.status_code == 200
    
    # Results should be identical (from cache)
    assert response1.json() == response2.json()


@pytest.mark.asyncio
async def test_get_trending_signals_24h_timeframe(test_signal_data):
    """Test getting trending signals for 24h timeframe."""
    settings = get_settings()
    
    async with get_test_client() as client:
        response = await client.get(
            f"{settings.API_V1_STR}/signals/trending?timeframe=24h",
            headers={"X-API-Key": settings.API_KEY}
        )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["filters"]["timeframe"] == "24h"
    assert data["count"] > 0
    
    # BTC should rank first in 24h (score_24h=9.2)
    if len(data["signals"]) > 0:
        assert data["signals"][0]["entity"] == "$BTC"
        assert data["signals"][0]["signal_score"] == 9.2
        assert data["signals"][0]["velocity"] == 15.0


@pytest.mark.asyncio
async def test_get_trending_signals_7d_timeframe(test_signal_data):
    """Test getting trending signals for 7d timeframe (default)."""
    settings = get_settings()
    
    async with get_test_client() as client:
        response = await client.get(
            f"{settings.API_V1_STR}/signals/trending?timeframe=7d",
            headers={"X-API-Key": settings.API_KEY}
        )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["filters"]["timeframe"] == "7d"
    assert data["count"] > 0
    
    # BTC should rank first in 7d (score_7d=8.5)
    if len(data["signals"]) > 0:
        assert data["signals"][0]["entity"] == "$BTC"
        assert data["signals"][0]["signal_score"] == 8.5
        assert data["signals"][0]["velocity"] == 12.3


@pytest.mark.asyncio
async def test_get_trending_signals_30d_timeframe(test_signal_data):
    """Test getting trending signals for 30d timeframe."""
    settings = get_settings()
    
    async with get_test_client() as client:
        response = await client.get(
            f"{settings.API_V1_STR}/signals/trending?timeframe=30d",
            headers={"X-API-Key": settings.API_KEY}
        )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["filters"]["timeframe"] == "30d"
    assert data["count"] > 0
    
    # ETH should rank first in 30d (score_30d=8.8)
    if len(data["signals"]) > 0:
        assert data["signals"][0]["entity"] == "$ETH"
        assert data["signals"][0]["signal_score"] == 8.8
        assert data["signals"][0]["velocity"] == 11.5


@pytest.mark.asyncio
async def test_get_trending_signals_invalid_timeframe(test_signal_data):
    """Test error handling for invalid timeframe."""
    settings = get_settings()
    
    async with get_test_client() as client:
        response = await client.get(
            f"{settings.API_V1_STR}/signals/trending?timeframe=1h",
            headers={"X-API-Key": settings.API_KEY}
        )
    
    assert response.status_code == 400
    assert "timeframe must be one of" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_trending_signals_timeframe_ranking_differs(test_signal_data):
    """Test that different timeframes produce different rankings."""
    settings = get_settings()
    
    async with get_test_client() as client:
        # Get 24h rankings
        response_24h = await client.get(
            f"{settings.API_V1_STR}/signals/trending?timeframe=24h",
            headers={"X-API-Key": settings.API_KEY}
        )
        
        # Get 30d rankings
        response_30d = await client.get(
            f"{settings.API_V1_STR}/signals/trending?timeframe=30d",
            headers={"X-API-Key": settings.API_KEY}
        )
    
    assert response_24h.status_code == 200
    assert response_30d.status_code == 200
    
    data_24h = response_24h.json()
    data_30d = response_30d.json()
    
    # Rankings should differ: BTC leads in 24h, ETH leads in 30d
    assert data_24h["signals"][0]["entity"] == "$BTC"
    assert data_30d["signals"][0]["entity"] == "$ETH"


@pytest.mark.asyncio
async def test_get_trending_signals_default_timeframe_is_7d(test_signal_data):
    """Test that default timeframe is 7d."""
    settings = get_settings()
    
    async with get_test_client() as client:
        response = await client.get(
            f"{settings.API_V1_STR}/signals/trending",
            headers={"X-API-Key": settings.API_KEY}
        )
    
    assert response.status_code == 200
    data = response.json()
    
    # Default should be 7d
    assert data["filters"]["timeframe"] == "7d"
