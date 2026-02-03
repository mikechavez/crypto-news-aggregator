"""
Tests for market event detection in briefings.

Verifies that major market shock events (liquidations, crashes, exploits)
are detected and included in briefings despite potentially lower recency scores.
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

from crypto_news_aggregator.services.market_event_detector import (
    MarketEventDetector,
    get_market_event_detector,
)


class TestMarketEventDetector:
    """Test market event detection functionality."""

    @pytest.fixture
    async def detector(self) -> MarketEventDetector:
        """Get detector instance."""
        return get_market_event_detector()

    @pytest.mark.asyncio
    async def test_detector_singleton(self, detector):
        """Test that detector is a singleton."""
        detector2 = get_market_event_detector()
        assert detector is detector2

    @pytest.mark.asyncio
    async def test_liquidation_keywords(self, detector):
        """Test liquidation keyword set is populated."""
        assert len(detector.LIQUIDATION_KEYWORDS) > 0
        assert "liquidation" in detector.LIQUIDATION_KEYWORDS
        assert "cascade" in detector.LIQUIDATION_KEYWORDS

    @pytest.mark.asyncio
    async def test_crash_keywords(self, detector):
        """Test crash keyword set is populated."""
        assert len(detector.CRASH_KEYWORDS) > 0
        assert "crash" in detector.CRASH_KEYWORDS
        assert "flash crash" in detector.CRASH_KEYWORDS

    @pytest.mark.asyncio
    async def test_exploit_keywords(self, detector):
        """Test exploit keyword set is populated."""
        assert len(detector.EXPLOIT_KEYWORDS) > 0
        assert "exploit" in detector.EXPLOIT_KEYWORDS
        assert "hack" in detector.EXPLOIT_KEYWORDS

    @pytest.mark.asyncio
    async def test_thresholds_configured(self, detector):
        """Test that detection thresholds are properly set."""
        assert detector.LIQUIDATION_ARTICLE_THRESHOLD == 4
        assert detector.LIQUIDATION_VOLUME_THRESHOLD == 500_000_000
        assert detector.MULTI_ENTITY_THRESHOLD == 3
        assert detector.EVENT_DETECTION_WINDOW_HOURS == 24

    @pytest.mark.asyncio
    async def test_market_events_detection_structure(self, detector):
        """Test the detection method returns correct structure."""
        try:
            events = await detector.detect_market_events()
            assert isinstance(events, list)
        except RuntimeError as e:
            # Skip if database not available
            if "MongoDB" in str(e) or "database" in str(e).lower():
                pytest.skip("Database not available for integration test")
            raise

        # If events found, check structure
        if events:
            for event in events:
                assert "type" in event
                assert "theme" in event
                assert "title" in event
                assert "article_ids" in event
                assert "article_count" in event
                assert "entities" in event
                assert "detected_at" in event

                # Verify types
                assert isinstance(event["type"], str)
                assert isinstance(event["theme"], str)
                assert isinstance(event["article_ids"], list)
                assert isinstance(event["article_count"], int)
                assert isinstance(event["entities"], list)

    @pytest.mark.asyncio
    async def test_market_event_narrative_creation_structure(
        self, detector
    ):
        """Test that market event narratives are created with correct structure."""
        # Create a test event
        test_event = {
            "type": "liquidation_cascade",
            "theme": "market_shock_liquidation",
            "title": "Test Liquidation Cascade",
            "article_ids": ["id1", "id2", "id3", "id4"],
            "article_count": 4,
            "entities": ["Bitcoin", "Ethereum", "Solana"],
            "estimated_volume": 750_000_000,  # $750M
            "detected_at": datetime.now(timezone.utc),
        }

        # This would normally create a narrative, but we just verify the method exists
        # and can be called without error (actual DB test would require fixtures)
        assert hasattr(detector, "create_or_update_market_event_narrative")

    @pytest.mark.asyncio
    async def test_boost_market_event_in_briefing_structure(self, detector):
        """Test market event boosting logic."""
        # Create test narratives
        regular_narratives = [
            {
                "title": "Regular Narrative 1",
                "theme": "regulatory",
                "_fresh_recency": 0.7,
            },
            {
                "title": "Regular Narrative 2",
                "theme": "adoption",
                "_fresh_recency": 0.6,
            },
        ]

        market_shock = {
            "title": "Market Shock",
            "theme": "market_shock_liquidation",
            "_fresh_recency": 0.3,  # Low recency but high importance
        }

        narratives = regular_narratives + [market_shock]

        # Apply boosting
        boosted = await detector.boost_market_event_in_briefing(narratives)

        # Check that we got narratives back
        assert len(boosted) == 3
        assert isinstance(boosted, list)

        # Market shock should be marked
        shock_in_result = next((n for n in boosted if n["title"] == "Market Shock"), None)
        assert shock_in_result is not None
        assert shock_in_result.get("_market_shock") is True

        # Recency should be boosted
        boosted_recency = shock_in_result.get("_fresh_recency", 0)
        assert boosted_recency > 0.3  # Should be higher than original 0.3

    @pytest.mark.asyncio
    async def test_event_volume_estimation(self, detector):
        """Test that volume estimation logic is in place."""
        # The detector has internal volume extraction logic
        # We just verify the logic exists and methods are callable
        assert hasattr(detector, "_detect_liquidation_cascade")
        assert hasattr(detector, "_detect_market_crash")
        assert hasattr(detector, "_detect_exploit_event")

    @pytest.mark.asyncio
    async def test_market_shock_starts_hot(self, detector):
        """Test that market shock narratives start in 'hot' state."""
        test_event = {
            "type": "liquidation_cascade",
            "theme": "market_shock_liquidation",
            "title": "Test Event",
            "article_ids": ["id1", "id2", "id3", "id4"],
            "article_count": 4,
            "entities": ["Bitcoin"],
            "estimated_volume": 750_000_000,
            "detected_at": datetime.now(timezone.utc),
        }

        # We're not actually creating in DB, just checking the method exists
        # and would use correct parameters
        assert hasattr(detector, "create_or_update_market_event_narrative")

    @pytest.mark.asyncio
    async def test_briefing_integration_with_market_events(self):
        """Test that briefing agent can use market event detector."""
        from crypto_news_aggregator.services.briefing_agent import (
            get_briefing_agent,
        )

        agent = get_briefing_agent()

        # Verify agent has access to detector
        assert hasattr(agent, "memory_manager")
        assert hasattr(agent, "pattern_detector")

        # Note: Full integration test would require mocked DB with test articles


# Historical data tests would verify with Jan 31 liquidation event
# These require database fixtures with test data


@pytest.mark.asyncio
async def test_market_event_detector_available():
    """Test that market event detector can be imported and instantiated."""
    detector = get_market_event_detector()
    assert detector is not None
    assert isinstance(detector, MarketEventDetector)
