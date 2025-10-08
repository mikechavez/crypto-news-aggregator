"""
Integration tests for multi-timeframe signal scoring.

Tests the full workflow from entity mentions to stored signal scores.
"""

import pytest
from datetime import datetime, timezone, timedelta
from crypto_news_aggregator.services.signal_service import calculate_signal_score
from crypto_news_aggregator.db.operations.signal_scores import (
    upsert_signal_score,
    get_entity_signal,
)


@pytest.mark.asyncio
async def test_multi_timeframe_storage_and_retrieval(mongo_db):
    """Test storing and retrieving multi-timeframe signal scores."""
    collection = mongo_db.entity_mentions
    await collection.delete_many({"entity": "TEST_STORAGE"})
    
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    
    # Create test mentions
    for i in range(30):
        await collection.insert_one({
            "entity": "TEST_STORAGE",
            "entity_type": "ticker",
            "article_id": f"art_{i}",
            "sentiment": "positive",
            "is_primary": True,
            "source": f"source_{i % 3}",
            "created_at": now - timedelta(hours=12),
            "metadata": {},
        })
    
    # Calculate scores for all timeframes
    signal_24h = await calculate_signal_score("TEST_STORAGE", timeframe_hours=24)
    signal_7d = await calculate_signal_score("TEST_STORAGE", timeframe_hours=168)
    signal_30d = await calculate_signal_score("TEST_STORAGE", timeframe_hours=720)
    
    # Store with all timeframes
    await upsert_signal_score(
        entity="TEST_STORAGE",
        entity_type="ticker",
        score=signal_24h["score"],
        velocity=signal_24h["velocity"],
        source_count=signal_24h["source_count"],
        sentiment=signal_24h["sentiment"],
        score_24h=signal_24h["score"],
        score_7d=signal_7d["score"],
        score_30d=signal_30d["score"],
        velocity_24h=signal_24h["velocity"],
        velocity_7d=signal_7d["velocity"],
        velocity_30d=signal_30d["velocity"],
        mentions_24h=signal_24h.get("mentions", 0),
        mentions_7d=signal_7d.get("mentions", 0),
        mentions_30d=signal_30d.get("mentions", 0),
        recency_24h=signal_24h.get("recency_factor", 0.0),
        recency_7d=signal_7d.get("recency_factor", 0.0),
        recency_30d=signal_30d.get("recency_factor", 0.0),
    )
    
    # Retrieve and verify
    stored = await get_entity_signal("TEST_STORAGE")
    
    assert stored is not None
    assert "score_24h" in stored
    assert "score_7d" in stored
    assert "score_30d" in stored
    assert "velocity_24h" in stored
    assert "velocity_7d" in stored
    assert "velocity_30d" in stored
    assert "mentions_24h" in stored
    assert "mentions_7d" in stored
    assert "mentions_30d" in stored
    
    # Verify values match
    assert stored["score_24h"] == signal_24h["score"]
    assert stored["score_7d"] == signal_7d["score"]
    assert stored["score_30d"] == signal_30d["score"]
    
    await collection.delete_many({"entity": "TEST_STORAGE"})


@pytest.mark.asyncio
async def test_multi_timeframe_update_preserves_data(mongo_db):
    """Test that updating signal scores preserves multi-timeframe data."""
    collection = mongo_db.entity_mentions
    await collection.delete_many({"entity": "TEST_UPDATE"})
    
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    
    # Create initial data
    for i in range(10):
        await collection.insert_one({
            "entity": "TEST_UPDATE",
            "entity_type": "ticker",
            "article_id": f"art_{i}",
            "sentiment": "neutral",
            "is_primary": True,
            "source": "source_a",
            "created_at": now - timedelta(hours=6),
            "metadata": {},
        })
    
    # First calculation and storage
    signal_24h_v1 = await calculate_signal_score("TEST_UPDATE", timeframe_hours=24)
    signal_7d_v1 = await calculate_signal_score("TEST_UPDATE", timeframe_hours=168)
    
    await upsert_signal_score(
        entity="TEST_UPDATE",
        entity_type="ticker",
        score=signal_24h_v1["score"],
        velocity=signal_24h_v1["velocity"],
        source_count=signal_24h_v1["source_count"],
        sentiment=signal_24h_v1["sentiment"],
        score_24h=signal_24h_v1["score"],
        score_7d=signal_7d_v1["score"],
        velocity_24h=signal_24h_v1["velocity"],
        velocity_7d=signal_7d_v1["velocity"],
    )
    
    # Add more mentions
    for i in range(10, 20):
        await collection.insert_one({
            "entity": "TEST_UPDATE",
            "entity_type": "ticker",
            "article_id": f"art_{i}",
            "sentiment": "positive",
            "is_primary": True,
            "source": "source_b",
            "created_at": now - timedelta(hours=2),
            "metadata": {},
        })
    
    # Second calculation and update
    signal_24h_v2 = await calculate_signal_score("TEST_UPDATE", timeframe_hours=24)
    signal_30d_v2 = await calculate_signal_score("TEST_UPDATE", timeframe_hours=720)
    
    await upsert_signal_score(
        entity="TEST_UPDATE",
        entity_type="ticker",
        score=signal_24h_v2["score"],
        velocity=signal_24h_v2["velocity"],
        source_count=signal_24h_v2["source_count"],
        sentiment=signal_24h_v2["sentiment"],
        score_24h=signal_24h_v2["score"],
        score_30d=signal_30d_v2["score"],
        velocity_24h=signal_24h_v2["velocity"],
        velocity_30d=signal_30d_v2["velocity"],
    )
    
    # Verify all fields are present
    stored = await get_entity_signal("TEST_UPDATE")
    
    assert stored["score_24h"] == signal_24h_v2["score"]  # Updated
    assert stored["score_7d"] == signal_7d_v1["score"]  # Preserved from first update
    assert stored["score_30d"] == signal_30d_v2["score"]  # Updated
    
    await collection.delete_many({"entity": "TEST_UPDATE"})


@pytest.mark.asyncio
async def test_multi_timeframe_different_growth_patterns(mongo_db):
    """Test that different timeframes capture different growth patterns."""
    collection = mongo_db.entity_mentions
    await collection.delete_many({"entity": "TEST_PATTERNS"})
    
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    
    # Simulate a spike in last 24h but steady over longer term
    # Last 24h: 100 mentions (spike)
    for i in range(100):
        await collection.insert_one({
            "entity": "TEST_PATTERNS",
            "entity_type": "ticker",
            "article_id": f"spike_{i}",
            "sentiment": "neutral",
            "is_primary": True,
            "source": "source_a",
            "created_at": now - timedelta(hours=6),
            "metadata": {},
        })
    
    # Previous 24h: 10 mentions (low baseline)
    for i in range(10):
        await collection.insert_one({
            "entity": "TEST_PATTERNS",
            "entity_type": "ticker",
            "article_id": f"prev_day_{i}",
            "sentiment": "neutral",
            "is_primary": True,
            "source": "source_a",
            "created_at": now - timedelta(hours=36),
            "metadata": {},
        })
    
    # 2-7 days ago: steady 50 mentions per day
    for day in range(2, 7):
        for i in range(50):
            await collection.insert_one({
                "entity": "TEST_PATTERNS",
                "entity_type": "ticker",
                "article_id": f"day{day}_{i}",
                "sentiment": "neutral",
                "is_primary": True,
                "source": "source_a",
                "created_at": now - timedelta(days=day),
                "metadata": {},
            })
    
    # Calculate all timeframes
    signal_24h = await calculate_signal_score("TEST_PATTERNS", timeframe_hours=24)
    signal_7d = await calculate_signal_score("TEST_PATTERNS", timeframe_hours=168)
    
    # 24h should show high velocity (spike: 100 vs 10 = 900% growth)
    assert signal_24h["velocity"] > 5.0
    
    # 7d should show lower velocity (more stable over week)
    assert signal_7d["velocity"] < signal_24h["velocity"]
    
    # 24h score should be higher due to recent spike
    assert signal_24h["score"] >= signal_7d["score"]
    
    await collection.delete_many({"entity": "TEST_PATTERNS"})
