"""
Tests for signals API endpoints.
"""

import pytest
from datetime import datetime, timezone
from httpx import AsyncClient
from crypto_news_aggregator.main import app
from crypto_news_aggregator.db.mongodb import mongo_manager
from crypto_news_aggregator.db.operations.signal_scores import upsert_signal_score
from crypto_news_aggregator.core.config import get_settings


@pytest.fixture
async def test_signal_data():
    """Create test signal score data."""
    db = await mongo_manager.get_async_database()
    collection = db.signal_scores
    
    # Clean up existing test data
    await collection.delete_many({"entity": {"$in": ["$BTC", "$ETH", "Bitcoin"]}})
    
    # Create test signal scores
    await upsert_signal_score(
        entity="$BTC",
        entity_type="ticker",
        score=8.5,
        velocity=12.3,
        source_count=15,
        sentiment={"avg": 0.7, "min": -0.2, "max": 1.0, "divergence": 0.3},
        first_seen=datetime.now(timezone.utc),
    )
    
    await upsert_signal_score(
        entity="$ETH",
        entity_type="ticker",
        score=6.2,
        velocity=8.1,
        source_count=10,
        sentiment={"avg": 0.4, "min": -0.1, "max": 0.9, "divergence": 0.25},
        first_seen=datetime.now(timezone.utc),
    )
    
    await upsert_signal_score(
        entity="Bitcoin",
        entity_type="project",
        score=7.8,
        velocity=10.5,
        source_count=12,
        sentiment={"avg": 0.6, "min": 0.0, "max": 1.0, "divergence": 0.28},
        first_seen=datetime.now(timezone.utc),
    )
    
    yield
    
    # Clean up after tests
    await collection.delete_many({"entity": {"$in": ["$BTC", "$ETH", "Bitcoin"]}})


@pytest.mark.asyncio
async def test_get_trending_signals_default(test_signal_data):
    """Test getting trending signals with default parameters."""
    settings = get_settings()
    
    async with AsyncClient(app=app, base_url="http://test") as client:
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
    assert len(data["signals"]) <= 10  # Default limit
    
    # Check first signal has highest score
    if len(data["signals"]) > 1:
        assert data["signals"][0]["signal_score"] >= data["signals"][1]["signal_score"]


@pytest.mark.asyncio
async def test_get_trending_signals_with_limit(test_signal_data):
    """Test getting trending signals with custom limit."""
    settings = get_settings()
    
    async with AsyncClient(app=app, base_url="http://test") as client:
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
    
    async with AsyncClient(app=app, base_url="http://test") as client:
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
    
    async with AsyncClient(app=app, base_url="http://test") as client:
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
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            f"{settings.API_V1_STR}/signals/trending?entity_type=invalid",
            headers={"X-API-Key": settings.API_KEY}
        )
    
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_trending_signals_response_structure(test_signal_data):
    """Test the structure of the response."""
    settings = get_settings()
    
    async with AsyncClient(app=app, base_url="http://test") as client:
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
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            f"{settings.API_V1_STR}/signals/trending"
        )
    
    # Should return 403 Forbidden without API key
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_trending_signals_caching(test_signal_data):
    """Test that results are cached."""
    settings = get_settings()
    
    async with AsyncClient(app=app, base_url="http://test") as client:
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
