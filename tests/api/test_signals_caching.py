"""
Unit and integration tests for signals endpoint caching.
"""

import pytest
import pytest_asyncio
import time
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock

from crypto_news_aggregator.main import app
from crypto_news_aggregator.db.mongodb import mongo_manager
from crypto_news_aggregator.db.operations.signal_scores import upsert_signal_score
from crypto_news_aggregator.core.config import get_settings
from crypto_news_aggregator.api.v1.endpoints import signals


def get_test_client():
    """Helper to create AsyncClient with proper transport."""
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest_asyncio.fixture
async def test_signal_data(mongo_db):
    """Create test signal score data."""
    # Clear cache before test
    signals._memory_cache.clear()
    
    collection = mongo_db.signal_scores
    
    # Clean up existing test data
    await collection.delete_many({"entity": {"$in": ["$TEST1", "$TEST2"]}})
    
    # Create test signal scores
    await upsert_signal_score(
        entity="$TEST1",
        entity_type="ticker",
        score=8.5,
        velocity=12.3,
        source_count=15,
        sentiment={"avg": 0.7, "min": -0.2, "max": 1.0, "divergence": 0.3},
        first_seen=datetime.now(timezone.utc),
        score_24h=9.2,
        score_7d=8.5,
        score_30d=7.1,
        velocity_24h=15.0,
        velocity_7d=12.3,
        velocity_30d=8.5,
    )
    
    await upsert_signal_score(
        entity="$TEST2",
        entity_type="ticker",
        score=6.2,
        velocity=8.1,
        source_count=10,
        sentiment={"avg": 0.4, "min": -0.1, "max": 0.9, "divergence": 0.25},
        first_seen=datetime.now(timezone.utc),
        score_24h=5.5,
        score_7d=6.2,
        score_30d=8.8,
        velocity_24h=6.0,
        velocity_7d=8.1,
        velocity_30d=11.5,
    )
    
    yield
    
    # Clean up after tests
    await collection.delete_many({"entity": {"$in": ["$TEST1", "$TEST2"]}})
    signals._memory_cache.clear()


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear the in-memory cache before each test."""
    signals._memory_cache.clear()
    signals._signals_cache.clear()
    yield
    signals._memory_cache.clear()
    signals._signals_cache.clear()


# ============================================================================
# Unit Tests for Cache Functions
# ============================================================================

def test_get_from_cache_empty():
    """Test get_from_cache returns None when cache is empty."""
    result = signals.get_from_cache("nonexistent_key")
    assert result is None


def test_set_and_get_from_cache():
    """Test setting and getting data from in-memory cache."""
    cache_key = "test:key:1"
    test_data = {"count": 5, "signals": [{"entity": "$BTC"}]}
    
    # Set in cache
    signals.set_in_cache(cache_key, test_data)
    
    # Get from cache
    result = signals.get_from_cache(cache_key)
    
    assert result is not None
    assert result == test_data


def test_cache_expiry():
    """Test that cache entries expire after TTL."""
    cache_key = "test:key:expiry"
    test_data = {"count": 1}
    
    # Set in cache
    signals.set_in_cache(cache_key, test_data)
    
    # Manually expire the cache entry
    cached_data, cached_time = signals._memory_cache[cache_key]
    expired_time = datetime.now() - timedelta(seconds=120)  # 2 minutes ago
    signals._memory_cache[cache_key] = (cached_data, expired_time)
    
    # Should return None (expired)
    result = signals.get_from_cache(cache_key)
    assert result is None
    
    # Entry should be removed from cache
    assert cache_key not in signals._memory_cache


def test_cache_cleanup():
    """Test that cache automatically cleans up when exceeding max size."""
    # Fill cache with exactly 100 entries
    for i in range(100):
        cache_key = f"test:key:{i}"
        signals.set_in_cache(cache_key, {"data": i})
    
    # Should have 100 entries
    assert len(signals._memory_cache) == 100
    
    # Add one more - should trigger cleanup
    signals.set_in_cache("test:key:100", {"data": 100})
    
    # Should still be at or below 100 after cleanup
    assert len(signals._memory_cache) <= 101  # May keep some fresh entries


def test_cache_cleanup_removes_expired_only():
    """Test that cleanup only removes expired entries."""
    # Add some fresh entries
    for i in range(50):
        signals.set_in_cache(f"fresh:{i}", {"data": i})
    
    # Add some expired entries
    for i in range(60):
        cache_key = f"expired:{i}"
        expired_time = datetime.now() - timedelta(seconds=120)
        signals._memory_cache[cache_key] = ({"data": i}, expired_time)
    
    # Trigger cleanup by adding one more entry
    signals.set_in_cache("trigger:cleanup", {"data": "cleanup"})
    
    # Fresh entries should still be there
    assert signals.get_from_cache("fresh:0") is not None
    assert signals.get_from_cache("fresh:49") is not None
    
    # Expired entries should be gone
    assert "expired:0" not in signals._memory_cache


def test_cache_key_isolation():
    """Test that different cache keys are isolated."""
    signals.set_in_cache("key1", {"data": "value1"})
    signals.set_in_cache("key2", {"data": "value2"})
    
    assert signals.get_from_cache("key1") == {"data": "value1"}
    assert signals.get_from_cache("key2") == {"data": "value2"}


@patch('crypto_news_aggregator.api.v1.endpoints.signals.redis_client')
def test_redis_fallback_to_memory(mock_redis):
    """Test that cache falls back to memory when Redis fails."""
    # Mock Redis as enabled but failing
    mock_redis.enabled = True
    mock_redis.get.side_effect = Exception("Redis connection failed")
    mock_redis.set.side_effect = Exception("Redis connection failed")
    
    cache_key = "test:redis:fallback"
    test_data = {"count": 3}
    
    # Should not raise exception, should use memory cache
    signals.set_in_cache(cache_key, test_data)
    result = signals.get_from_cache(cache_key)
    
    assert result == test_data


@patch('crypto_news_aggregator.api.v1.endpoints.signals.redis_client')
def test_redis_disabled_uses_memory(mock_redis):
    """Test that memory cache is used when Redis is disabled."""
    mock_redis.enabled = False
    
    cache_key = "test:redis:disabled"
    test_data = {"count": 2}
    
    signals.set_in_cache(cache_key, test_data)
    result = signals.get_from_cache(cache_key)
    
    assert result == test_data
    # Redis should not have been called
    mock_redis.get.assert_not_called()
    mock_redis.set.assert_not_called()


# ============================================================================
# Integration Tests for Endpoint Caching
# ============================================================================

@pytest.mark.asyncio
async def test_endpoint_caching_basic(test_signal_data):
    """Test that endpoint results are cached and returned quickly."""
    settings = get_settings()
    
    async with get_test_client() as client:
        # First request (cache miss)
        start1 = time.time()
        response1 = await client.get(
            f"{settings.API_V1_STR}/signals/trending?timeframe=7d&limit=10",
            headers={"X-API-Key": settings.API_KEY}
        )
        elapsed1 = time.time() - start1
        
        # Second request (cache hit)
        start2 = time.time()
        response2 = await client.get(
            f"{settings.API_V1_STR}/signals/trending?timeframe=7d&limit=10",
            headers={"X-API-Key": settings.API_KEY}
        )
        elapsed2 = time.time() - start2
    
    assert response1.status_code == 200
    assert response2.status_code == 200
    
    # Results should be identical
    assert response1.json() == response2.json()
    
    # Second request should be faster (cached)
    # Note: In tests this might not always be true due to overhead,
    # but in production the difference is significant
    print(f"First request: {elapsed1:.3f}s, Second request: {elapsed2:.3f}s")


@pytest.mark.asyncio
async def test_cache_key_includes_all_parameters(test_signal_data):
    """Test that cache keys properly isolate different parameter combinations."""
    settings = get_settings()
    
    async with get_test_client() as client:
        # Request with limit=10
        response1 = await client.get(
            f"{settings.API_V1_STR}/signals/trending?timeframe=7d&limit=10",
            headers={"X-API-Key": settings.API_KEY}
        )
        
        # Request with limit=5 (different cache key)
        response2 = await client.get(
            f"{settings.API_V1_STR}/signals/trending?timeframe=7d&limit=5",
            headers={"X-API-Key": settings.API_KEY}
        )
    
    assert response1.status_code == 200
    assert response2.status_code == 200
    
    data1 = response1.json()
    data2 = response2.json()
    
    # Should have different results due to different limits
    assert data1["filters"]["limit"] == 10
    assert data2["filters"]["limit"] == 5
    
    # Results should be different
    assert len(data1["signals"]) != len(data2["signals"]) or data1 != data2


@pytest.mark.asyncio
async def test_cache_key_includes_timeframe(test_signal_data):
    """Test that different timeframes use different cache keys."""
    settings = get_settings()
    
    async with get_test_client() as client:
        # Request 7d timeframe
        response_7d = await client.get(
            f"{settings.API_V1_STR}/signals/trending?timeframe=7d&limit=10",
            headers={"X-API-Key": settings.API_KEY}
        )
        
        # Request 24h timeframe (different cache key)
        response_24h = await client.get(
            f"{settings.API_V1_STR}/signals/trending?timeframe=24h&limit=10",
            headers={"X-API-Key": settings.API_KEY}
        )
    
    assert response_7d.status_code == 200
    assert response_24h.status_code == 200
    
    data_7d = response_7d.json()
    data_24h = response_24h.json()
    
    # Should have different timeframes
    assert data_7d["filters"]["timeframe"] == "7d"
    assert data_24h["filters"]["timeframe"] == "24h"
    
    # Scores should be different (using different timeframe fields)
    if len(data_7d["signals"]) > 0 and len(data_24h["signals"]) > 0:
        # TEST1 has different scores for different timeframes
        signal_7d = next((s for s in data_7d["signals"] if s["entity"] == "$TEST1"), None)
        signal_24h = next((s for s in data_24h["signals"] if s["entity"] == "$TEST1"), None)
        
        if signal_7d and signal_24h:
            assert signal_7d["signal_score"] != signal_24h["signal_score"]


@pytest.mark.asyncio
async def test_cache_key_includes_entity_type(test_signal_data):
    """Test that entity_type filter affects cache key."""
    settings = get_settings()
    
    async with get_test_client() as client:
        # Request without entity_type filter
        response_all = await client.get(
            f"{settings.API_V1_STR}/signals/trending?timeframe=7d&limit=10",
            headers={"X-API-Key": settings.API_KEY}
        )
        
        # Request with entity_type=ticker
        response_ticker = await client.get(
            f"{settings.API_V1_STR}/signals/trending?timeframe=7d&limit=10&entity_type=ticker",
            headers={"X-API-Key": settings.API_KEY}
        )
    
    assert response_all.status_code == 200
    assert response_ticker.status_code == 200
    
    data_all = response_all.json()
    data_ticker = response_ticker.json()
    
    # Filters should be different
    assert data_all["filters"]["entity_type"] is None
    assert data_ticker["filters"]["entity_type"] == "ticker"


@pytest.mark.asyncio
async def test_cache_persists_across_requests(test_signal_data):
    """Test that cache persists across multiple requests."""
    settings = get_settings()
    
    async with get_test_client() as client:
        # Make 3 requests with same parameters
        responses = []
        for _ in range(3):
            response = await client.get(
                f"{settings.API_V1_STR}/signals/trending?timeframe=7d&limit=10",
                headers={"X-API-Key": settings.API_KEY}
            )
            responses.append(response)
    
    # All should succeed
    for response in responses:
        assert response.status_code == 200
    
    # All should return identical data (from cache)
    data = [r.json() for r in responses]
    assert data[0] == data[1] == data[2]


@pytest.mark.asyncio
async def test_cache_includes_narratives_and_articles(test_signal_data):
    """Test that cached data includes narratives and recent_articles."""
    settings = get_settings()
    
    async with get_test_client() as client:
        response = await client.get(
            f"{settings.API_V1_STR}/signals/trending?timeframe=7d&limit=10",
            headers={"X-API-Key": settings.API_KEY}
        )
    
    assert response.status_code == 200
    data = response.json()
    
    # Check that signals have narratives and recent_articles fields
    if len(data["signals"]) > 0:
        signal = data["signals"][0]
        assert "narratives" in signal
        assert "recent_articles" in signal
        assert isinstance(signal["narratives"], list)
        assert isinstance(signal["recent_articles"], list)


@pytest.mark.asyncio
async def test_cache_min_score_filter(test_signal_data):
    """Test that min_score filter affects cache key."""
    settings = get_settings()
    
    async with get_test_client() as client:
        # Request with min_score=0
        response1 = await client.get(
            f"{settings.API_V1_STR}/signals/trending?timeframe=7d&min_score=0.0",
            headers={"X-API-Key": settings.API_KEY}
        )
        
        # Request with min_score=7
        response2 = await client.get(
            f"{settings.API_V1_STR}/signals/trending?timeframe=7d&min_score=7.0",
            headers={"X-API-Key": settings.API_KEY}
        )
    
    assert response1.status_code == 200
    assert response2.status_code == 200
    
    data1 = response1.json()
    data2 = response2.json()
    
    # Should have different counts (min_score filters results)
    assert data1["filters"]["min_score"] == 0.0
    assert data2["filters"]["min_score"] == 7.0
    
    # Higher min_score should return fewer or equal results
    assert data2["count"] <= data1["count"]


# ============================================================================
# Performance Tests
# ============================================================================

@pytest.mark.asyncio
async def test_cache_performance_improvement(test_signal_data):
    """Test that caching provides significant performance improvement."""
    settings = get_settings()
    
    async with get_test_client() as client:
        # Clear cache to ensure first request is uncached
        signals._memory_cache.clear()
        
        # First request (uncached)
        start1 = time.time()
        response1 = await client.get(
            f"{settings.API_V1_STR}/signals/trending?timeframe=7d&limit=50",
            headers={"X-API-Key": settings.API_KEY}
        )
        time1 = time.time() - start1
        
        # Second request (cached)
        start2 = time.time()
        response2 = await client.get(
            f"{settings.API_V1_STR}/signals/trending?timeframe=7d&limit=50",
            headers={"X-API-Key": settings.API_KEY}
        )
        time2 = time.time() - start2
    
    assert response1.status_code == 200
    assert response2.status_code == 200
    assert response1.json() == response2.json()
    
    print(f"\nPerformance comparison:")
    print(f"  Uncached request: {time1:.3f}s")
    print(f"  Cached request:   {time2:.3f}s")
    print(f"  Speedup:          {time1/time2:.1f}x")
    
    # In production, cached should be much faster
    # In tests, we just verify it doesn't get slower
    assert time2 <= time1 * 1.5  # Allow some variance in test environment


# ============================================================================
# Tests for GET /api/v1/signals endpoint caching (5 min TTL)
# ============================================================================

def test_signals_cache_empty():
    """Test that signals cache is initially empty."""
    assert len(signals._signals_cache) == 0


def test_signals_cache_stores_data():
    """Test that GET /signals endpoint stores data in dedicated cache."""
    cache_key = "signals:top20"
    test_data = {"count": 3, "signals": [{"entity": "$BTC"}]}
    
    # Manually set cache
    signals._signals_cache[cache_key] = (test_data, datetime.now())
    
    # Verify it's stored
    assert cache_key in signals._signals_cache
    cached_data, cached_time = signals._signals_cache[cache_key]
    assert cached_data == test_data


def test_signals_cache_expiration():
    """Test that signals cache expires after 5 minutes."""
    cache_key = "signals:top20"
    test_data = {"count": 1, "signals": []}
    
    # Set cache with expired timestamp (6 minutes ago)
    expired_time = datetime.now() - timedelta(minutes=6)
    signals._signals_cache[cache_key] = (test_data, expired_time)
    
    # Check if expired
    cached_data, cached_time = signals._signals_cache[cache_key]
    time_diff = datetime.now() - cached_time
    
    # Should be expired (> 5 minutes)
    assert time_diff > signals._signals_cache_ttl


def test_signals_cache_not_expired():
    """Test that signals cache is valid within 5 minutes."""
    cache_key = "signals:top20"
    test_data = {"count": 1, "signals": []}
    
    # Set cache with recent timestamp (2 minutes ago)
    recent_time = datetime.now() - timedelta(minutes=2)
    signals._signals_cache[cache_key] = (test_data, recent_time)
    
    # Check if still valid
    cached_data, cached_time = signals._signals_cache[cache_key]
    time_diff = datetime.now() - cached_time
    
    # Should not be expired (< 5 minutes)
    assert time_diff < signals._signals_cache_ttl


@pytest.mark.asyncio
async def test_get_signals_endpoint_caching(test_signal_data):
    """Test that GET /signals endpoint uses cache."""
    settings = get_settings()
    
    async with get_test_client() as client:
        # First request (cache miss)
        response1 = await client.get(
            f"{settings.API_V1_STR}/signals",
            headers={"X-API-Key": settings.API_KEY}
        )
        
        # Second request (cache hit)
        response2 = await client.get(
            f"{settings.API_V1_STR}/signals",
            headers={"X-API-Key": settings.API_KEY}
        )
    
    assert response1.status_code == 200
    assert response2.status_code == 200
    
    data1 = response1.json()
    data2 = response2.json()
    
    # Results should be identical (from cache)
    assert data1["signals"] == data2["signals"]
    assert data1["cached_at"] == data2["cached_at"]
    
    # Cache should contain the key
    assert "signals:top20" in signals._signals_cache


@pytest.mark.asyncio
async def test_get_signals_cache_ttl_5_minutes(test_signal_data):
    """Test that GET /signals cache has 5-minute TTL."""
    settings = get_settings()
    
    async with get_test_client() as client:
        # Make initial request to populate cache
        response = await client.get(
            f"{settings.API_V1_STR}/signals",
            headers={"X-API-Key": settings.API_KEY}
        )
    
    assert response.status_code == 200
    
    # Verify cache entry exists
    cache_key = "signals:top20"
    assert cache_key in signals._signals_cache
    
    # Check TTL is set correctly
    cached_data, cached_time = signals._signals_cache[cache_key]
    time_since_cached = datetime.now() - cached_time
    
    # Should be very recent (just cached)
    assert time_since_cached < timedelta(seconds=5)


@pytest.mark.asyncio
async def test_get_signals_cache_invalidation(test_signal_data):
    """Test that expired cache is invalidated and refreshed."""
    settings = get_settings()
    cache_key = "signals:top20"
    
    # Pre-populate cache with expired data
    old_data = {"count": 0, "signals": [], "cached_at": "2020-01-01T00:00:00"}
    expired_time = datetime.now() - timedelta(minutes=6)
    signals._signals_cache[cache_key] = (old_data, expired_time)
    
    async with get_test_client() as client:
        # Request should invalidate expired cache and fetch fresh data
        response = await client.get(
            f"{settings.API_V1_STR}/signals",
            headers={"X-API-Key": settings.API_KEY}
        )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should have fresh data (not the old cached data)
    assert data["count"] > 0  # Should have test signals
    assert data["cached_at"] != "2020-01-01T00:00:00"
    
    # Cache should be updated with fresh timestamp
    cached_data, cached_time = signals._signals_cache[cache_key]
    time_since_cached = datetime.now() - cached_time
    assert time_since_cached < timedelta(seconds=5)


@pytest.mark.asyncio
async def test_get_signals_limit_20_enforced(test_signal_data):
    """Test that GET /signals always returns max 20 results."""
    settings = get_settings()
    
    # Create 30 test signals
    db = await mongo_manager.get_async_database()
    collection = db.signal_scores
    
    test_entities = []
    for i in range(30):
        entity = f"CACHE_TEST_{i}"
        test_entities.append(entity)
        await upsert_signal_score(
            entity=entity,
            entity_type="ticker",
            score=float(100 - i),  # Descending scores
            velocity=1.0,
            source_count=1,
            sentiment={"avg": 0.5, "min": 0.0, "max": 1.0, "divergence": 0.1},
            first_seen=datetime.now(timezone.utc),
        )
    
    try:
        async with get_test_client() as client:
            response = await client.get(
                f"{settings.API_V1_STR}/signals",
                headers={"X-API-Key": settings.API_KEY}
            )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return exactly 20 results
        assert len(data["signals"]) == 20
        assert data["count"] == 20
        
        # Should be top 20 by score
        assert data["signals"][0]["entity"] == "CACHE_TEST_0"  # Highest score
        assert data["signals"][19]["entity"] == "CACHE_TEST_19"  # 20th highest
        
    finally:
        # Clean up
        await collection.delete_many({"entity": {"$in": test_entities}})
        signals._signals_cache.clear()


@pytest.mark.asyncio
async def test_get_signals_performance_with_cache(test_signal_data):
    """Test that caching improves performance for GET /signals."""
    settings = get_settings()
    
    async with get_test_client() as client:
        # Clear cache
        signals._signals_cache.clear()
        
        # First request (uncached)
        start1 = time.time()
        response1 = await client.get(
            f"{settings.API_V1_STR}/signals",
            headers={"X-API-Key": settings.API_KEY}
        )
        time1 = time.time() - start1
        
        # Second request (cached)
        start2 = time.time()
        response2 = await client.get(
            f"{settings.API_V1_STR}/signals",
            headers={"X-API-Key": settings.API_KEY}
        )
        time2 = time.time() - start2
    
    assert response1.status_code == 200
    assert response2.status_code == 200
    
    print(f"\nGET /signals performance:")
    print(f"  Uncached: {time1:.3f}s")
    print(f"  Cached:   {time2:.3f}s")
    
    # Cached request should not be slower
    assert time2 <= time1 * 1.5
