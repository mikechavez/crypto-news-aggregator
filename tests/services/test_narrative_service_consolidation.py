"""
Unit tests for narrative consolidation functionality.

Tests cover:
- Article ID deduplication
- Sentiment weighted average calculation
- Timeline data merging (overlapping and non-overlapping dates)
- Lifecycle state precedence
- Similarity threshold enforcement
- Article reference updates
- Merged narrative marking
- Missing focus field handling
"""

import pytest
from datetime import datetime, timezone
from bson import ObjectId

from src.crypto_news_aggregator.services.narrative_service import (
    consolidate_duplicate_narratives,
    _merge_narratives,
)


@pytest.mark.asyncio
async def test_merge_combines_article_ids(mongo_db):
    """Verify article_ids are combined and deduplicated."""
    # Create two narratives with overlapping articles
    article_1 = ObjectId()
    article_2 = ObjectId()
    article_3 = ObjectId()

    n1 = {
        "_id": ObjectId(),
        "nucleus_entity": "Bitcoin",
        "narrative_focus": "price surge",
        "article_ids": [article_1, article_2],
        "article_count": 2,
        "avg_sentiment": 0.5,
        "timeline_data": [],
        "lifecycle_state": "hot",
        "fingerprint": {
            "narrative_focus": "price surge",
            "nucleus_entity": "Bitcoin",
        },
    }
    n2 = {
        "_id": ObjectId(),
        "nucleus_entity": "Bitcoin",
        "narrative_focus": "price surge",
        "article_ids": [article_1, article_3],  # One overlap
        "article_count": 2,
        "avg_sentiment": 0.5,
        "timeline_data": [],
        "lifecycle_state": "rising",
        "fingerprint": {
            "narrative_focus": "price surge",
            "nucleus_entity": "Bitcoin",
        },
    }

    await mongo_db.narratives.insert_many([n1, n2])
    await _merge_narratives(n1, n2, similarity=0.95, db=mongo_db)

    # Verify survivor has all unique articles
    survivor = await mongo_db.narratives.find_one({"_id": n1["_id"]})
    assert len(survivor["article_ids"]) == 3  # 2 + 2 - 1 overlap
    assert survivor["article_count"] == 3


@pytest.mark.asyncio
async def test_merge_recalculates_sentiment(mongo_db):
    """Verify sentiment is weighted average by article count."""
    n1 = {
        "_id": ObjectId(),
        "nucleus_entity": "Ethereum",
        "narrative_focus": "protocol upgrade",
        "article_ids": [ObjectId(), ObjectId()],  # 2 articles
        "article_count": 2,
        "avg_sentiment": 0.8,
        "timeline_data": [],
        "lifecycle_state": "hot",
        "fingerprint": {
            "narrative_focus": "protocol upgrade",
            "nucleus_entity": "Ethereum",
        },
    }
    n2 = {
        "_id": ObjectId(),
        "nucleus_entity": "Ethereum",
        "narrative_focus": "protocol upgrade",
        "article_ids": [ObjectId()],  # 1 article
        "article_count": 1,
        "avg_sentiment": 0.2,
        "timeline_data": [],
        "lifecycle_state": "rising",
        "fingerprint": {
            "narrative_focus": "protocol upgrade",
            "nucleus_entity": "Ethereum",
        },
    }

    await mongo_db.narratives.insert_many([n1, n2])
    await _merge_narratives(n1, n2, similarity=0.92, db=mongo_db)

    # (0.8 * 2 + 0.2 * 1) / 3 = 1.8 / 3 = 0.6
    survivor = await mongo_db.narratives.find_one({"_id": n1["_id"]})
    assert abs(survivor["avg_sentiment"] - 0.6) < 0.01


@pytest.mark.asyncio
async def test_merge_timeline_data_overlapping_dates(mongo_db):
    """Verify timeline data is merged correctly with overlapping dates."""
    n1 = {
        "_id": ObjectId(),
        "nucleus_entity": "Solana",
        "narrative_focus": "network outage",
        "article_ids": [ObjectId()],
        "article_count": 1,
        "avg_sentiment": 0.3,
        "timeline_data": [
            {"date": "2026-01-05", "article_count": 2, "velocity": 1.5, "entities": ["Solana"]},
            {"date": "2026-01-06", "article_count": 1, "velocity": 0.5, "entities": ["Solana"]},
        ],
        "lifecycle_state": "hot",
        "fingerprint": {
            "narrative_focus": "network outage",
            "nucleus_entity": "Solana",
        },
    }
    n2 = {
        "_id": ObjectId(),
        "nucleus_entity": "Solana",
        "narrative_focus": "network outage",
        "article_ids": [ObjectId()],
        "article_count": 1,
        "avg_sentiment": 0.2,
        "timeline_data": [
            {"date": "2026-01-06", "article_count": 1, "velocity": 0.8, "entities": ["Validators"]},
            {"date": "2026-01-07", "article_count": 2, "velocity": 2.0, "entities": ["Solana", "Developers"]},
        ],
        "lifecycle_state": "rising",
        "fingerprint": {
            "narrative_focus": "network outage",
            "nucleus_entity": "Solana",
        },
    }

    await mongo_db.narratives.insert_many([n1, n2])
    await _merge_narratives(n1, n2, similarity=0.93, db=mongo_db)

    survivor = await mongo_db.narratives.find_one({"_id": n1["_id"]})
    timeline = {t["date"]: t for t in survivor["timeline_data"]}

    # 2026-01-05: only n1 (2 articles, 1.5 velocity)
    assert timeline["2026-01-05"]["article_count"] == 2
    assert abs(timeline["2026-01-05"]["velocity"] - 1.5) < 0.01

    # 2026-01-06: both (1+1=2 articles, 0.5+0.8=1.3 velocity)
    assert timeline["2026-01-06"]["article_count"] == 2
    assert abs(timeline["2026-01-06"]["velocity"] - 1.3) < 0.01
    assert set(timeline["2026-01-06"]["entities"]) == {"Solana", "Validators"}

    # 2026-01-07: only n2 (2 articles, 2.0 velocity)
    assert timeline["2026-01-07"]["article_count"] == 2
    assert abs(timeline["2026-01-07"]["velocity"] - 2.0) < 0.01


@pytest.mark.asyncio
async def test_merge_timeline_data_non_overlapping_dates(mongo_db):
    """Verify timeline data with completely separate dates."""
    n1 = {
        "_id": ObjectId(),
        "nucleus_entity": "Cardano",
        "narrative_focus": "hard fork",
        "article_ids": [ObjectId()],
        "article_count": 1,
        "avg_sentiment": 0.7,
        "timeline_data": [
            {"date": "2026-01-05", "article_count": 3, "velocity": 2.0, "entities": ["Cardano"]},
        ],
        "lifecycle_state": "hot",
        "fingerprint": {
            "narrative_focus": "hard fork",
            "nucleus_entity": "Cardano",
        },
    }
    n2 = {
        "_id": ObjectId(),
        "nucleus_entity": "Cardano",
        "narrative_focus": "hard fork",
        "article_ids": [ObjectId()],
        "article_count": 1,
        "avg_sentiment": 0.6,
        "timeline_data": [
            {"date": "2026-01-07", "article_count": 2, "velocity": 1.5, "entities": ["Cardano"]},
        ],
        "lifecycle_state": "rising",
        "fingerprint": {
            "narrative_focus": "hard fork",
            "nucleus_entity": "Cardano",
        },
    }

    await mongo_db.narratives.insert_many([n1, n2])
    await _merge_narratives(n1, n2, similarity=0.94, db=mongo_db)

    survivor = await mongo_db.narratives.find_one({"_id": n1["_id"]})
    assert len(survivor["timeline_data"]) == 2

    timeline = {t["date"]: t for t in survivor["timeline_data"]}
    assert "2026-01-05" in timeline
    assert "2026-01-07" in timeline


@pytest.mark.asyncio
async def test_similarity_threshold_respected(mongo_db):
    """Narratives with similarity <0.9 are NOT merged."""
    n1 = {
        "_id": ObjectId(),
        "nucleus_entity": "Cardano",
        "narrative_focus": "price surge",
        "fingerprint": {
            "narrative_focus": "price surge",
            "nucleus_entity": "Cardano",
            "top_actors": ["retail"],
            "key_actions": ["buy"],
        },
        "article_ids": [ObjectId()],
        "article_count": 1,
        "avg_sentiment": 0.5,
        "timeline_data": [],
        "lifecycle_state": "hot",
    }
    n2 = {
        "_id": ObjectId(),
        "nucleus_entity": "Cardano",
        "narrative_focus": "governance vote",  # Different focus
        "fingerprint": {
            "narrative_focus": "governance vote",
            "nucleus_entity": "Cardano",
            "top_actors": ["validators"],
            "key_actions": ["vote"],
        },
        "article_ids": [ObjectId()],
        "article_count": 1,
        "avg_sentiment": 0.4,
        "timeline_data": [],
        "lifecycle_state": "emerging",
    }

    await mongo_db.narratives.insert_many([n1, n2])

    result = await consolidate_duplicate_narratives()

    # No merges should happen (similarity ~0.32 based on FEATURE-010 weights)
    assert result["merge_count"] == 0


@pytest.mark.asyncio
async def test_lifecycle_state_precedence(mongo_db):
    """Most advanced lifecycle state is kept after merge."""
    n1 = {
        "_id": ObjectId(),
        "nucleus_entity": "Ripple",
        "narrative_focus": "SEC case",
        "article_ids": [ObjectId(), ObjectId()],
        "article_count": 2,
        "avg_sentiment": 0.3,
        "timeline_data": [],
        "lifecycle_state": "emerging",  # Less advanced
        "fingerprint": {
            "narrative_focus": "SEC case",
            "nucleus_entity": "Ripple",
        },
    }
    n2 = {
        "_id": ObjectId(),
        "nucleus_entity": "Ripple",
        "narrative_focus": "SEC case",
        "article_ids": [ObjectId()],
        "article_count": 1,
        "avg_sentiment": 0.2,
        "timeline_data": [],
        "lifecycle_state": "hot",  # More advanced
        "fingerprint": {
            "narrative_focus": "SEC case",
            "nucleus_entity": "Ripple",
        },
    }

    await mongo_db.narratives.insert_many([n1, n2])
    await _merge_narratives(n1, n2, similarity=0.95, db=mongo_db)

    survivor = await mongo_db.narratives.find_one({"_id": n1["_id"]})
    assert survivor["lifecycle_state"] == "hot"


@pytest.mark.asyncio
async def test_merged_narrative_marked_correctly(mongo_db):
    """Merged narrative gets merged_into field and lifecycle=merged."""
    n1 = {
        "_id": ObjectId(),
        "nucleus_entity": "Polkadot",
        "narrative_focus": "parachain auction",
        "article_ids": [ObjectId(), ObjectId()],
        "article_count": 2,
        "avg_sentiment": 0.6,
        "timeline_data": [],
        "lifecycle_state": "hot",
        "fingerprint": {
            "narrative_focus": "parachain auction",
            "nucleus_entity": "Polkadot",
        },
    }
    n2 = {
        "_id": ObjectId(),
        "nucleus_entity": "Polkadot",
        "narrative_focus": "parachain auction",
        "article_ids": [ObjectId()],
        "article_count": 1,
        "avg_sentiment": 0.5,
        "timeline_data": [],
        "lifecycle_state": "rising",
        "fingerprint": {
            "narrative_focus": "parachain auction",
            "nucleus_entity": "Polkadot",
        },
    }

    await mongo_db.narratives.insert_many([n1, n2])
    await _merge_narratives(n1, n2, similarity=0.96, db=mongo_db)

    merged = await mongo_db.narratives.find_one({"_id": n2["_id"]})
    assert merged["lifecycle_state"] == "merged"
    assert merged["merged_into"] == n1["_id"]


@pytest.mark.asyncio
async def test_article_references_updated(mongo_db):
    """All articles from merged narrative point to survivor."""
    n1_id = ObjectId()
    n2_id = ObjectId()
    article_1 = ObjectId()
    article_2 = ObjectId()
    article_3 = ObjectId()

    n1 = {
        "_id": n1_id,
        "nucleus_entity": "Avalanche",
        "narrative_focus": "subnet launch",
        "article_ids": [article_1, article_2],
        "article_count": 2,
        "avg_sentiment": 0.7,
        "timeline_data": [],
        "lifecycle_state": "hot",
        "fingerprint": {
            "narrative_focus": "subnet launch",
            "nucleus_entity": "Avalanche",
        },
    }
    n2 = {
        "_id": n2_id,
        "nucleus_entity": "Avalanche",
        "narrative_focus": "subnet launch",
        "article_ids": [article_3],
        "article_count": 1,
        "avg_sentiment": 0.6,
        "timeline_data": [],
        "lifecycle_state": "rising",
        "fingerprint": {
            "narrative_focus": "subnet launch",
            "nucleus_entity": "Avalanche",
        },
    }

    await mongo_db.narratives.insert_many([n1, n2])

    # Create articles pointing to n2
    await mongo_db.articles.insert_one({
        "_id": article_3,
        "narrative_id": n2_id,
        "title": "Article about subnet",
        "text": "Content",
    })

    await _merge_narratives(n1, n2, similarity=0.97, db=mongo_db)

    # Verify article now points to n1
    article = await mongo_db.articles.find_one({"_id": article_3})
    assert article["narrative_id"] == n1_id


@pytest.mark.asyncio
async def test_skips_narratives_without_focus(mongo_db):
    """Narratives missing narrative_focus are skipped with warning."""
    n1 = {
        "_id": ObjectId(),
        "nucleus_entity": "Chainlink",
        "narrative_focus": "price surge",
        "fingerprint": {"narrative_focus": "price surge", "nucleus_entity": "Chainlink"},
        "article_ids": [ObjectId()],
        "article_count": 1,
        "avg_sentiment": 0.5,
        "timeline_data": [],
        "lifecycle_state": "hot",
    }
    n2 = {
        "_id": ObjectId(),
        "nucleus_entity": "Chainlink",
        # Missing narrative_focus field
        "fingerprint": {"nucleus_entity": "Chainlink"},
        "article_ids": [ObjectId()],
        "article_count": 1,
        "avg_sentiment": 0.4,
        "timeline_data": [],
        "lifecycle_state": "rising",
    }

    await mongo_db.narratives.insert_many([n1, n2])

    result = await consolidate_duplicate_narratives()

    # Should skip pair due to missing focus
    assert result["merge_count"] == 0


@pytest.mark.asyncio
async def test_consolidation_only_processes_active_states(mongo_db):
    """Dormant and merged narratives are excluded from consolidation."""
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
        "avg_sentiment": 0.5,
        "timeline_data": [],
        "lifecycle_state": "dormant",  # Not active
    }
    n2 = {
        "_id": ObjectId(),
        "nucleus_entity": "Bitcoin",
        "narrative_focus": "price surge",
        "fingerprint": {
            "narrative_focus": "price surge",
            "nucleus_entity": "Bitcoin",
        },
        "article_ids": [ObjectId()],
        "article_count": 1,
        "avg_sentiment": 0.5,
        "timeline_data": [],
        "lifecycle_state": "merged",  # Not active
    }

    await mongo_db.narratives.insert_many([n1, n2])

    result = await consolidate_duplicate_narratives()

    # Should not merge - narratives are not in active states
    assert result["merge_count"] == 0


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
        "timeline_data": [],
        "lifecycle_state": "hot",
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
        "timeline_data": [],
        "lifecycle_state": "hot",
    }

    await mongo_db.narratives.insert_many([n1, n2])

    result = await consolidate_duplicate_narratives()

    # Should not merge - different entities
    assert result["merge_count"] == 0
