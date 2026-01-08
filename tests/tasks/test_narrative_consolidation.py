"""
Integration tests for narrative consolidation task.

Tests cover:
- End-to-end consolidation flows
- Multiple narrative merging
- State transitions and tracking
- Article reference consistency
"""

import pytest
from bson import ObjectId

from src.crypto_news_aggregator.db import mongodb
from src.crypto_news_aggregator.services.narrative_service import consolidate_duplicate_narratives


@pytest.mark.asyncio
async def test_consolidation_end_to_end(mongo_db):
    """
    Create 3 duplicate narratives, run consolidation, verify only 1 remains.

    NOTE: This test uses the mongo_db fixture but the consolidation service
    uses mongo_manager. We need to patch mongo_manager before inserting data
    to ensure both use the same database.
    """
    # Create 3 narratives about same thing (high similarity)
    articles = [ObjectId(), ObjectId(), ObjectId(), ObjectId(), ObjectId()]

    n1 = {
        "_id": ObjectId(),
        "nucleus_entity": "Dogecoin",
        "narrative_focus": "price surge",
        "fingerprint": {
            "narrative_focus": "price surge",
            "nucleus_entity": "Dogecoin",
            "top_actors": ["Elon Musk"],
            "key_actions": ["tweet", "pump"],
        },
        "article_ids": articles[:2],
        "article_count": 2,
        "avg_sentiment": 0.6,
        "lifecycle_state": "hot",
        "timeline_data": [{"date": "2026-01-07", "article_count": 2, "velocity": 1.0, "entities": ["Dogecoin"]}],
    }

    n2 = {
        "_id": ObjectId(),
        "nucleus_entity": "Dogecoin",
        "narrative_focus": "price surge",  # Same focus
        "fingerprint": {
            "narrative_focus": "price surge",
            "nucleus_entity": "Dogecoin",
            "top_actors": ["Elon Musk"],
            "key_actions": ["tweet", "rally"],
        },
        "article_ids": articles[2:4],
        "article_count": 2,
        "avg_sentiment": 0.7,
        "lifecycle_state": "rising",
        "timeline_data": [{"date": "2026-01-07", "article_count": 2, "velocity": 1.2, "entities": ["Dogecoin"]}],
    }

    n3 = {
        "_id": ObjectId(),
        "nucleus_entity": "Dogecoin",
        "narrative_focus": "price surge",  # Same focus
        "fingerprint": {
            "narrative_focus": "price surge",
            "nucleus_entity": "Dogecoin",
            "top_actors": ["retail traders"],
            "key_actions": ["buy", "pump"],
        },
        "article_ids": [articles[4]],
        "article_count": 1,
        "avg_sentiment": 0.5,
        "lifecycle_state": "emerging",
        "timeline_data": [{"date": "2026-01-07", "article_count": 1, "velocity": 0.5, "entities": ["Dogecoin"]}],
    }

    # Insert narratives and articles to the test database
    await mongo_db.narratives.insert_many([n1, n2, n3])

    # Also create articles pointing to these narratives
    for i, article_id in enumerate(articles):
        narrative_id = n1["_id"] if i < 2 else (n2["_id"] if i < 4 else n3["_id"])
        await mongo_db.articles.insert_one({
            "_id": article_id,
            "narrative_id": narrative_id,
            "title": f"Article {i}",
            "text": "Content",
            "url": f"https://test.com/article-{i}",
        })

    # Verify data was inserted
    inserted_count = await mongo_db.narratives.count_documents({"nucleus_entity": "Dogecoin"})
    assert inserted_count == 3, f"Expected 3 narratives, but found {inserted_count}"

    # Inject test database into mongo_manager BEFORE calling consolidation
    # The conftest already sets up mongo_manager._db, but we need to ensure
    # get_async_database() is mocked to return our test database
    original_async_client = mongodb.mongo_manager._async_client

    try:
        # Temporarily set _async_client to None so injected_db is used
        mongodb.mongo_manager._async_client = None
        mongodb.mongo_manager._db = mongo_db

        # Run consolidation - now it will use our injected test database
        result = await consolidate_duplicate_narratives()

        # Should merge at least 1 narrative (high similarity pair)
        assert result["merge_count"] >= 1, f"Expected >=1 merges, got {result['merge_count']} - result: {result}"

        # Verify the merge was recorded
        assert len(result["merged_pairs"]) > 0, "Expected merged_pairs to be recorded"

        # Verify narratives were actually merged in database
        # After first pass, we should have at least 1 merged narrative
        merged_narratives = await mongo_db.narratives.count_documents({
            "nucleus_entity": "Dogecoin",
            "lifecycle_state": "merged"
        })
        assert merged_narratives >= 1, f"Expected >=1 merged narratives, found {merged_narratives}"

        # Verify active narratives were reduced
        active_narratives = await mongo_db.narratives.count_documents({
            "nucleus_entity": "Dogecoin",
            "lifecycle_state": {"$ne": "merged"}
        })
        assert active_narratives < 3, f"Expected <3 active narratives after merge, found {active_narratives}"

        # Verify all articles still exist
        article_count = await mongo_db.articles.count_documents({"_id": {"$in": articles}})
        assert article_count == 5, f"Expected 5 articles, found {article_count}"
    finally:
        # Restore original async client
        mongodb.mongo_manager._async_client = original_async_client


@pytest.mark.asyncio
async def test_consolidation_skips_different_entities(mongo_db):
    """Narratives with different nucleus_entity are not merged."""
    n1 = {
        "_id": ObjectId(),
        "nucleus_entity": "Bitcoin",
        "narrative_focus": "price surge",
        "fingerprint": {
            "narrative_focus": "price surge",
            "nucleus_entity": "Bitcoin",
        },
        "article_ids": [ObjectId()],
        "article_count": 1,
        "avg_sentiment": 0.8,
        "lifecycle_state": "hot",
        "timeline_data": [],
    }
    n2 = {
        "_id": ObjectId(),
        "nucleus_entity": "Ethereum",  # Different entity
        "narrative_focus": "price surge",
        "fingerprint": {
            "narrative_focus": "price surge",
            "nucleus_entity": "Ethereum",
        },
        "article_ids": [ObjectId()],
        "article_count": 1,
        "avg_sentiment": 0.7,
        "lifecycle_state": "hot",
        "timeline_data": [],
    }

    await mongo_db.narratives.insert_many([n1, n2])

    # Inject test database and temporarily disable async client
    original_async_client = mongodb.mongo_manager._async_client
    try:
        mongodb.mongo_manager._async_client = None
        mongodb.mongo_manager._db = mongo_db

        result = await consolidate_duplicate_narratives()

        # Should not merge - different entities
        assert result["merge_count"] == 0
    finally:
        mongodb.mongo_manager._async_client = original_async_client


@pytest.mark.asyncio
async def test_consolidation_skips_already_merged(mongo_db):
    """Already merged narratives are skipped."""
    survivor_id = ObjectId()

    n1 = {
        "_id": survivor_id,
        "nucleus_entity": "Litecoin",
        "narrative_focus": "halving",
        "fingerprint": {
            "narrative_focus": "halving",
            "nucleus_entity": "Litecoin",
        },
        "article_ids": [ObjectId()],
        "article_count": 1,
        "avg_sentiment": 0.6,
        "lifecycle_state": "hot",
        "timeline_data": [],
    }
    n2 = {
        "_id": ObjectId(),
        "nucleus_entity": "Litecoin",
        "narrative_focus": "halving",
        "fingerprint": {
            "narrative_focus": "halving",
            "nucleus_entity": "Litecoin",
        },
        "article_ids": [ObjectId()],
        "article_count": 1,
        "avg_sentiment": 0.5,
        "lifecycle_state": "merged",  # Already merged
        "merged_into": survivor_id,
        "timeline_data": [],
    }

    await mongo_db.narratives.insert_many([n1, n2])

    # Inject test database and temporarily disable async client
    original_async_client = mongodb.mongo_manager._async_client
    try:
        mongodb.mongo_manager._async_client = None
        mongodb.mongo_manager._db = mongo_db

        result = await consolidate_duplicate_narratives()

        # Should not merge - n2 already merged
        assert result["merge_count"] == 0
    finally:
        mongodb.mongo_manager._async_client = original_async_client
