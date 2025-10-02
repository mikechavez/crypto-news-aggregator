"""
Tests for narratives API endpoint.

Tests the /api/v1/narratives/active endpoint.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def sample_narratives():
    """Sample narrative data for testing."""
    return [
        {
            "_id": "narrative1",
            "theme": "Bitcoin ETF Approval",
            "entities": ["Bitcoin", "ETF", "SEC"],
            "story": "SEC reviews Bitcoin ETF applications from major institutions.",
            "article_count": 15,
            "updated_at": datetime(2025, 10, 1, 19, 30, 0, tzinfo=timezone.utc)
        },
        {
            "_id": "narrative2",
            "theme": "Ethereum Upgrade",
            "entities": ["Ethereum", "Dencun", "Layer2"],
            "story": "Ethereum's Dencun upgrade brings significant improvements to Layer 2 scaling.",
            "article_count": 12,
            "updated_at": datetime(2025, 10, 1, 19, 25, 0, tzinfo=timezone.utc)
        }
    ]


@pytest.mark.asyncio
async def test_get_active_narratives_success(sample_narratives):
    """Test successful retrieval of active narratives."""
    with patch("crypto_news_aggregator.api.v1.endpoints.narratives.get_active_narratives") as mock_get, \
         patch("crypto_news_aggregator.api.v1.endpoints.narratives.redis_client") as mock_redis:
        
        # Mock database response
        mock_get.return_value = sample_narratives
        
        # Mock Redis (disabled)
        mock_redis.enabled = False
        
        # Import after patching
        from crypto_news_aggregator.api.v1.endpoints.narratives import get_active_narratives_endpoint
        
        # Call endpoint
        result = await get_active_narratives_endpoint(limit=10)
        
        # Verify response
        assert len(result) == 2
        assert result[0].theme == "Bitcoin ETF Approval"
        assert len(result[0].entities) == 3
        assert result[0].article_count == 15


@pytest.mark.asyncio
async def test_get_active_narratives_empty():
    """Test endpoint with no narratives."""
    with patch("crypto_news_aggregator.api.v1.endpoints.narratives.get_active_narratives") as mock_get, \
         patch("crypto_news_aggregator.api.v1.endpoints.narratives.redis_client") as mock_redis:
        
        # Mock empty response
        mock_get.return_value = []
        mock_redis.enabled = False
        
        from crypto_news_aggregator.api.v1.endpoints.narratives import get_active_narratives_endpoint
        
        result = await get_active_narratives_endpoint(limit=10)
        
        assert result == []


@pytest.mark.asyncio
async def test_get_active_narratives_with_cache(sample_narratives):
    """Test endpoint with Redis cache hit."""
    import json
    
    with patch("crypto_news_aggregator.api.v1.endpoints.narratives.get_active_narratives") as mock_get, \
         patch("crypto_news_aggregator.api.v1.endpoints.narratives.redis_client") as mock_redis:
        
        # Mock Redis cache hit
        mock_redis.enabled = True
        cached_data = [
            {
                "theme": "Cached Narrative",
                "entities": ["Test"],
                "story": "Cached story",
                "article_count": 5,
                "updated_at": "2025-10-01T19:00:00+00:00"
            }
        ]
        mock_redis.get.return_value = json.dumps(cached_data)
        
        from crypto_news_aggregator.api.v1.endpoints.narratives import get_active_narratives_endpoint
        
        result = await get_active_narratives_endpoint(limit=10)
        
        # Should return cached data without calling database
        assert len(result) == 1
        assert result[0].theme == "Cached Narrative"
        mock_get.assert_not_called()


@pytest.mark.asyncio
async def test_get_active_narratives_limit_validation():
    """Test endpoint limit parameter validation."""
    with patch("crypto_news_aggregator.api.v1.endpoints.narratives.get_active_narratives") as mock_get, \
         patch("crypto_news_aggregator.api.v1.endpoints.narratives.redis_client") as mock_redis:
        
        mock_get.return_value = []
        mock_redis.enabled = False
        
        from crypto_news_aggregator.api.v1.endpoints.narratives import get_active_narratives_endpoint
        
        # Test with valid limit
        result = await get_active_narratives_endpoint(limit=5)
        mock_get.assert_called_once_with(limit=5)
        
        # Test with max limit
        mock_get.reset_mock()
        result = await get_active_narratives_endpoint(limit=20)
        mock_get.assert_called_once_with(limit=20)


@pytest.mark.asyncio
async def test_get_active_narratives_cache_write(sample_narratives):
    """Test endpoint writes to cache on database fetch."""
    with patch("crypto_news_aggregator.api.v1.endpoints.narratives.get_active_narratives") as mock_get, \
         patch("crypto_news_aggregator.api.v1.endpoints.narratives.redis_client") as mock_redis:
        
        # Mock database response
        mock_get.return_value = sample_narratives
        
        # Mock Redis (enabled, cache miss)
        mock_redis.enabled = True
        mock_redis.get.return_value = None
        mock_redis.set = AsyncMock()
        
        from crypto_news_aggregator.api.v1.endpoints.narratives import get_active_narratives_endpoint
        
        result = await get_active_narratives_endpoint(limit=10)
        
        # Should fetch from database and write to cache
        mock_get.assert_called_once()
        mock_redis.set.assert_called_once()
        
        # Verify cache key and TTL
        call_args = mock_redis.set.call_args
        assert "narratives:active:10" in call_args[0][0]
        assert call_args[1]["ex"] == 600  # 10 minutes


@pytest.mark.asyncio
async def test_get_active_narratives_error_handling():
    """Test endpoint error handling."""
    from fastapi import HTTPException
    
    with patch("crypto_news_aggregator.api.v1.endpoints.narratives.get_active_narratives") as mock_get, \
         patch("crypto_news_aggregator.api.v1.endpoints.narratives.redis_client") as mock_redis:
        
        # Mock database error
        mock_get.side_effect = Exception("Database error")
        mock_redis.enabled = False
        
        from crypto_news_aggregator.api.v1.endpoints.narratives import get_active_narratives_endpoint
        
        # Should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await get_active_narratives_endpoint(limit=10)
        
        assert exc_info.value.status_code == 500
        assert "Failed to fetch narratives" in str(exc_info.value.detail)
