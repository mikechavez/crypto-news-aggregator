"""
Tests for cost tracking service.
"""

import pytest
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from crypto_news_aggregator.services.cost_tracker import CostTracker


@pytest.fixture
async def db():
    """Create test database connection."""
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.test_cost_tracking
    yield db
    # Cleanup
    await db.api_costs.delete_many({})
    client.close()


@pytest.fixture
async def tracker(db):
    """Create cost tracker instance."""
    return CostTracker(db)


class TestCostCalculation:
    """Test cost calculation logic."""

    def test_haiku_pricing(self, tracker):
        """Test Haiku model pricing."""
        cost = tracker.calculate_cost(
            "claude-3-5-haiku-20241022",
            input_tokens=1000,
            output_tokens=1000
        )
        # 1K input @ $0.80/1M = $0.0008
        # 1K output @ $4.00/1M = $0.004
        # Total = $0.0048
        assert cost == pytest.approx(0.0048, abs=0.0001)

    def test_sonnet_pricing(self, tracker):
        """Test Sonnet model pricing."""
        cost = tracker.calculate_cost(
            "claude-3-5-sonnet-20241022",
            input_tokens=1000,
            output_tokens=1000
        )
        # 1K input @ $3.00/1M = $0.003
        # 1K output @ $15.00/1M = $0.015
        # Total = $0.018
        assert cost == pytest.approx(0.018, abs=0.0001)

    def test_opus_pricing(self, tracker):
        """Test Opus model pricing."""
        cost = tracker.calculate_cost(
            "claude-opus-4-5-20251101",
            input_tokens=1000,
            output_tokens=1000
        )
        # 1K input @ $15.00/1M = $0.015
        # 1K output @ $75.00/1M = $0.075
        # Total = $0.090
        assert cost == pytest.approx(0.090, abs=0.0001)

    def test_unknown_model_defaults_to_haiku(self, tracker):
        """Unknown models default to Haiku pricing."""
        cost = tracker.calculate_cost(
            "unknown-model",
            input_tokens=1000,
            output_tokens=1000
        )
        # Should use Haiku pricing
        assert cost == pytest.approx(0.0048, abs=0.0001)


@pytest.mark.asyncio
class TestCostTracking:
    """Test cost tracking to database."""

    async def test_track_call_writes_to_db(self, tracker, db):
        """Test that track_call writes to database."""
        cost = await tracker.track_call(
            operation="entity_extraction",
            model="claude-3-5-haiku-20241022",
            input_tokens=500,
            output_tokens=200,
            cached=False
        )

        # Verify cost calculation
        assert cost > 0

        # Verify database write
        doc = await db.api_costs.find_one({"operation": "entity_extraction"})
        assert doc is not None
        assert doc["model"] == "claude-3-5-haiku-20241022"
        assert doc["input_tokens"] == 500
        assert doc["output_tokens"] == 200
        assert doc["cost"] == pytest.approx(cost, abs=0.0001)
        assert doc["cached"] is False

    async def test_cache_hit_has_zero_cost(self, tracker, db):
        """Test that cache hits have zero cost."""
        cost = await tracker.track_call(
            operation="entity_extraction",
            model="claude-3-5-haiku-20241022",
            input_tokens=500,
            output_tokens=200,
            cached=True,
            cache_key="test_cache_key"
        )

        # Cache hits are free
        assert cost == 0.0

        # Verify database write
        doc = await db.api_costs.find_one({"cache_key": "test_cache_key"})
        assert doc is not None
        assert doc["cost"] == 0.0
        assert doc["cached"] is True

    async def test_get_daily_cost(self, tracker, db):
        """Test daily cost aggregation."""
        # Track two calls
        await tracker.track_call(
            "test_op", "claude-3-5-haiku-20241022",
            1000, 1000, cached=False
        )
        await tracker.track_call(
            "test_op", "claude-3-5-haiku-20241022",
            1000, 1000, cached=False
        )

        daily_cost = await tracker.get_daily_cost(days=1)

        # Should be 2 × $0.0048 = $0.0096
        assert daily_cost == pytest.approx(0.0096, abs=0.0001)

    async def test_get_monthly_cost(self, tracker, db):
        """Test monthly cost aggregation."""
        # Track a call
        await tracker.track_call(
            "test_op", "claude-3-5-haiku-20241022",
            1000, 1000, cached=False
        )

        monthly_cost = await tracker.get_monthly_cost()

        # Should be $0.0048
        assert monthly_cost == pytest.approx(0.0048, abs=0.0001)
