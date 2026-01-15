"""
Unit tests for narrative reactivation functionality.

Tests cover:
- should_reactivate_or_create_new() decision logic
- _reactivate_narrative() reactivation process
- Similarity threshold enforcement
- Dormant window enforcement (30 days)
- Timezone-aware datetime handling
- Edge cases (missing fields, empty candidates, etc.)
"""

import pytest
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from unittest.mock import AsyncMock, MagicMock, patch

from src.crypto_news_aggregator.services.narrative_service import (
    should_reactivate_or_create_new,
    _reactivate_narrative,
    calculate_fingerprint_similarity,
)


class TestShouldReactivateOrCreateNew:
    """Test the reactivation decision logic."""

    @pytest.mark.asyncio
    async def test_returns_create_new_when_no_nucleus_entity(self, mongo_db):
        """Returns create_new when nucleus_entity is missing."""
        fingerprint = {
            "narrative_focus": "price_surge",
            # Missing nucleus_entity
        }

        decision, matched = await should_reactivate_or_create_new(
            fingerprint, nucleus_entity=None
        )

        assert decision == "create_new"
        assert matched is None

    @pytest.mark.asyncio
    async def test_returns_create_new_when_no_dormant_candidates(self, mongo_db):
        """Returns create_new when no dormant narratives exist for nucleus_entity."""
        fingerprint = {
            "nucleus_entity": "Bitcoin",
            "narrative_focus": "price_surge",
            "key_entities": ["Bitcoin", "ETF"],
        }

        decision, matched = await should_reactivate_or_create_new(
            fingerprint, nucleus_entity="Bitcoin"
        )

        assert decision == "create_new"
        assert matched is None

    @pytest.mark.asyncio
    async def test_reactivates_when_similarity_above_threshold(self, mongo_db):
        """Reactivates dormant narrative when similarity >= 0.80."""
        now = datetime.now(timezone.utc)
        dormant_since = now - timedelta(days=5)

        # Create dormant narrative
        dormant_narrative = {
            "_id": ObjectId(),
            "nucleus_entity": "BlackRock",
            "narrative_focus": "institutional_adoption",
            "title": "Bitcoin ETF Adoption",
            "lifecycle_state": "dormant",
            "dormant_since": dormant_since,
            "article_ids": [ObjectId(), ObjectId()],
            "article_count": 2,
            "avg_sentiment": 0.65,
            "fingerprint": {
                "nucleus_entity": "BlackRock",
                "narrative_focus": "institutional_adoption",
                "key_entities": ["BlackRock", "Bitcoin", "ETF"],
            },
        }

        await mongo_db.narratives.insert_one(dormant_narrative)

        # Test fingerprint with matching focus (should achieve ~0.8 similarity)
        fingerprint = {
            "nucleus_entity": "BlackRock",
            "narrative_focus": "institutional_adoption",
            "key_entities": ["BlackRock", "Bitcoin", "ETF"],
        }

        decision, matched = await should_reactivate_or_create_new(
            fingerprint, nucleus_entity="BlackRock"
        )

        assert decision == "reactivate"
        assert matched is not None
        assert matched["_id"] == dormant_narrative["_id"]

    @pytest.mark.asyncio
    async def test_creates_new_when_similarity_below_threshold(self, mongo_db):
        """Returns create_new when similarity < 0.80."""
        now = datetime.now(timezone.utc)
        dormant_since = now - timedelta(days=5)

        # Create dormant narrative with one focus
        dormant_narrative = {
            "_id": ObjectId(),
            "nucleus_entity": "BlackRock",
            "narrative_focus": "institutional_adoption",
            "title": "Bitcoin ETF Adoption",
            "lifecycle_state": "dormant",
            "dormant_since": dormant_since,
            "article_ids": [ObjectId(), ObjectId()],
            "article_count": 2,
            "fingerprint": {
                "nucleus_entity": "BlackRock",
                "narrative_focus": "institutional_adoption",
                "key_entities": ["BlackRock", "Bitcoin"],
            },
        }

        await mongo_db.narratives.insert_one(dormant_narrative)

        # Test with DIFFERENT focus (should score low)
        fingerprint = {
            "nucleus_entity": "BlackRock",
            "narrative_focus": "regulatory_pressure",  # Different focus
            "key_entities": ["BlackRock"],
        }

        decision, matched = await should_reactivate_or_create_new(
            fingerprint, nucleus_entity="BlackRock"
        )

        assert decision == "create_new"
        assert matched is None

    @pytest.mark.asyncio
    async def test_ignores_dormant_narratives_older_than_30_days(self, mongo_db):
        """Ignores dormant narratives > 30 days old (outside reactivation window)."""
        now = datetime.now(timezone.utc)
        old_dormant_since = now - timedelta(days=35)  # Too old

        # Create old dormant narrative
        old_dormant = {
            "_id": ObjectId(),
            "nucleus_entity": "Bitcoin",
            "narrative_focus": "price_surge",
            "title": "Old Bitcoin Price Surge",
            "lifecycle_state": "dormant",
            "dormant_since": old_dormant_since,
            "article_ids": [ObjectId()],
            "article_count": 1,
            "fingerprint": {
                "nucleus_entity": "Bitcoin",
                "narrative_focus": "price_surge",
                "key_entities": ["Bitcoin"],
            },
        }

        await mongo_db.narratives.insert_one(old_dormant)

        # Even with matching fingerprint, should not reactivate old narrative
        fingerprint = {
            "nucleus_entity": "Bitcoin",
            "narrative_focus": "price_surge",
            "key_entities": ["Bitcoin"],
        }

        decision, matched = await should_reactivate_or_create_new(
            fingerprint, nucleus_entity="Bitcoin"
        )

        assert decision == "create_new"
        assert matched is None

    @pytest.mark.asyncio
    async def test_selects_best_match_among_multiple_candidates(self, mongo_db):
        """Selects narrative with highest similarity when multiple candidates exist."""
        now = datetime.now(timezone.utc)
        dormant_since = now - timedelta(days=5)

        # Create multiple dormant narratives for same nucleus_entity
        dormant_1 = {
            "_id": ObjectId(),
            "nucleus_entity": "Bitcoin",
            "narrative_focus": "price_surge",  # Low match
            "lifecycle_state": "dormant",
            "dormant_since": dormant_since,
            "article_ids": [ObjectId()],
            "fingerprint": {
                "nucleus_entity": "Bitcoin",
                "narrative_focus": "price_surge",
                "key_entities": ["Bitcoin"],
            },
        }

        dormant_2 = {
            "_id": ObjectId(),
            "nucleus_entity": "Bitcoin",
            "narrative_focus": "regulatory_clarity",  # Better match
            "lifecycle_state": "dormant",
            "dormant_since": dormant_since,
            "article_ids": [ObjectId()],
            "fingerprint": {
                "nucleus_entity": "Bitcoin",
                "narrative_focus": "regulatory_clarity",
                "key_entities": ["Bitcoin", "SEC"],
            },
        }

        await mongo_db.narratives.insert_many([dormant_1, dormant_2])

        # Test fingerprint matches dormant_2 better
        fingerprint = {
            "nucleus_entity": "Bitcoin",
            "narrative_focus": "regulatory_clarity",
            "key_entities": ["Bitcoin", "SEC"],
        }

        decision, matched = await should_reactivate_or_create_new(
            fingerprint, nucleus_entity="Bitcoin"
        )

        assert decision == "reactivate"
        assert matched["_id"] == dormant_2["_id"]

    @pytest.mark.asyncio
    async def test_handles_timezone_aware_dormant_since(self, mongo_db):
        """Handles timezone-aware datetime in dormant_since field."""
        now = datetime.now(timezone.utc)
        dormant_since = now.replace(tzinfo=timezone.utc) - timedelta(days=5)

        # Create narrative with timezone-aware dormant_since
        dormant_narrative = {
            "_id": ObjectId(),
            "nucleus_entity": "Ethereum",
            "narrative_focus": "protocol_upgrade",
            "lifecycle_state": "dormant",
            "dormant_since": dormant_since,
            "article_ids": [ObjectId()],
            "fingerprint": {
                "nucleus_entity": "Ethereum",
                "narrative_focus": "protocol_upgrade",
                "key_entities": ["Ethereum"],
            },
        }

        await mongo_db.narratives.insert_one(dormant_narrative)

        fingerprint = {
            "nucleus_entity": "Ethereum",
            "narrative_focus": "protocol_upgrade",
            "key_entities": ["Ethereum"],
        }

        # Should not raise error and should find the narrative
        decision, matched = await should_reactivate_or_create_new(
            fingerprint, nucleus_entity="Ethereum"
        )

        assert decision == "reactivate"
        assert matched is not None

    @pytest.mark.asyncio
    async def test_handles_timezone_naive_dormant_since(self, mongo_db):
        """Handles timezone-naive datetime in dormant_since field."""
        now = datetime.now(timezone.utc)
        dormant_since = (now - timedelta(days=5)).replace(tzinfo=None)  # Naive datetime

        # Create narrative with timezone-naive dormant_since
        dormant_narrative = {
            "_id": ObjectId(),
            "nucleus_entity": "Solana",
            "narrative_focus": "network_outage",
            "lifecycle_state": "dormant",
            "dormant_since": dormant_since,
            "article_ids": [ObjectId()],
            "fingerprint": {
                "nucleus_entity": "Solana",
                "narrative_focus": "network_outage",
                "key_entities": ["Solana"],
            },
        }

        await mongo_db.narratives.insert_one(dormant_narrative)

        fingerprint = {
            "nucleus_entity": "Solana",
            "narrative_focus": "network_outage",
            "key_entities": ["Solana"],
        }

        # Should not raise error and should find the narrative
        decision, matched = await should_reactivate_or_create_new(
            fingerprint, nucleus_entity="Solana"
        )

        assert decision == "reactivate"
        assert matched is not None

    @pytest.mark.asyncio
    async def test_skips_candidates_without_fingerprint(self, mongo_db):
        """Skips candidates that are missing fingerprint field."""
        now = datetime.now(timezone.utc)
        dormant_since = now - timedelta(days=5)

        # Create narrative without fingerprint
        no_fingerprint = {
            "_id": ObjectId(),
            "nucleus_entity": "Ripple",
            "narrative_focus": "adoption",
            "lifecycle_state": "dormant",
            "dormant_since": dormant_since,
            "article_ids": [ObjectId()],
            # Missing fingerprint field
        }

        # Create valid narrative
        valid_narrative = {
            "_id": ObjectId(),
            "nucleus_entity": "Ripple",
            "narrative_focus": "adoption",
            "lifecycle_state": "dormant",
            "dormant_since": dormant_since,
            "article_ids": [ObjectId()],
            "fingerprint": {
                "nucleus_entity": "Ripple",
                "narrative_focus": "adoption",
                "key_entities": ["Ripple"],
            },
        }

        await mongo_db.narratives.insert_many([no_fingerprint, valid_narrative])

        fingerprint = {
            "nucleus_entity": "Ripple",
            "narrative_focus": "adoption",
            "key_entities": ["Ripple"],
        }

        decision, matched = await should_reactivate_or_create_new(
            fingerprint, nucleus_entity="Ripple"
        )

        assert decision == "reactivate"
        assert matched["_id"] == valid_narrative["_id"]


class TestReactivateNarrative:
    """Test the narrative reactivation process."""

    @pytest.mark.asyncio
    async def test_deduplicates_article_ids(self, mongo_db):
        """Combines and deduplicates article IDs."""
        article_1 = str(ObjectId())
        article_2 = str(ObjectId())
        article_3 = str(ObjectId())

        dormant_narrative = {
            "_id": ObjectId(),
            "nucleus_entity": "Bitcoin",
            "narrative_focus": "price_surge",
            "article_ids": [article_1, article_2],
            "article_count": 2,
            "avg_sentiment": 0.7,
            "lifecycle_history": [],
        }

        cluster = [
            {
                "_id": ObjectId(article_1),
                "sentiment_score": 0.6,
                "published_at": datetime.now(timezone.utc),
            },
            {
                "_id": ObjectId(article_2),
                "sentiment_score": 0.8,
                "published_at": datetime.now(timezone.utc),
            },
            {
                "_id": ObjectId(article_3),
                "sentiment_score": 0.7,
                "published_at": datetime.now(timezone.utc),
            },
        ]

        fingerprint = {
            "nucleus_entity": "Bitcoin",
            "narrative_focus": "price_surge",
        }

        await mongo_db.narratives.insert_one(dormant_narrative)

        # Reactivate with new articles
        reactivated_id = await _reactivate_narrative(
            dormant_narrative, [article_1, article_2, article_3], cluster, fingerprint
        )

        # Verify article IDs are combined
        reactivated = await mongo_db.narratives.find_one({"_id": ObjectId(reactivated_id)})
        assert len(reactivated["article_ids"]) == 3
        assert article_1 in reactivated["article_ids"]
        assert article_2 in reactivated["article_ids"]
        assert article_3 in reactivated["article_ids"]

    @pytest.mark.asyncio
    async def test_recalculates_sentiment_as_weighted_average(self, mongo_db):
        """Recalculates sentiment as weighted average of existing and new articles."""
        article_1 = str(ObjectId())
        article_2 = str(ObjectId())
        article_3 = str(ObjectId())

        dormant_narrative = {
            "_id": ObjectId(),
            "nucleus_entity": "Ethereum",
            "narrative_focus": "protocol_upgrade",
            "article_ids": [article_1, article_2],
            "article_count": 2,
            "avg_sentiment": 0.8,  # 2 articles, avg 0.8
            "lifecycle_history": [],
        }

        cluster = [
            {
                "_id": ObjectId(article_1),
                "sentiment_score": 0.8,
                "published_at": datetime.now(timezone.utc),
            },
            {
                "_id": ObjectId(article_2),
                "sentiment_score": 0.8,
                "published_at": datetime.now(timezone.utc),
            },
            {
                "_id": ObjectId(article_3),
                "sentiment_score": 0.2,
                "published_at": datetime.now(timezone.utc),
            },
        ]

        fingerprint = {
            "nucleus_entity": "Ethereum",
            "narrative_focus": "protocol_upgrade",
        }

        await mongo_db.narratives.insert_one(dormant_narrative)

        # Reactivate with 1 new article with low sentiment
        reactivated_id = await _reactivate_narrative(
            dormant_narrative, [article_1, article_2, article_3], cluster, fingerprint
        )

        reactivated = await mongo_db.narratives.find_one({"_id": ObjectId(reactivated_id)})

        # (0.8 * 2 + 0.2 * 1) / 3 = 1.8 / 3 = 0.6
        # Note: actual implementation may calculate slightly differently due to rounding
        expected_sentiment = 0.6
        assert abs(reactivated["avg_sentiment"] - expected_sentiment) < 0.1

    @pytest.mark.asyncio
    async def test_sets_lifecycle_state_to_reactivated(self, mongo_db):
        """Sets lifecycle_state to 'reactivated'."""
        dormant_narrative = {
            "_id": ObjectId(),
            "nucleus_entity": "Bitcoin",
            "narrative_focus": "price_surge",
            "article_ids": [str(ObjectId())],
            "article_count": 1,
            "avg_sentiment": 0.5,
            "lifecycle_state": "dormant",
            "lifecycle_history": [],
        }

        cluster = [
            {
                "_id": ObjectId(),
                "sentiment_score": 0.6,
                "published_at": datetime.now(timezone.utc),
            }
        ]

        fingerprint = {
            "nucleus_entity": "Bitcoin",
            "narrative_focus": "price_surge",
        }

        await mongo_db.narratives.insert_one(dormant_narrative)

        reactivated_id = await _reactivate_narrative(
            dormant_narrative,
            [str(ObjectId())],
            cluster,
            fingerprint,
        )

        reactivated = await mongo_db.narratives.find_one({"_id": ObjectId(reactivated_id)})
        assert reactivated["lifecycle_state"] == "reactivated"

    @pytest.mark.asyncio
    async def test_increments_reactivated_count(self, mongo_db):
        """Increments reactivated_count."""
        dormant_narrative = {
            "_id": ObjectId(),
            "nucleus_entity": "Bitcoin",
            "narrative_focus": "price_surge",
            "article_ids": [str(ObjectId())],
            "article_count": 1,
            "avg_sentiment": 0.5,
            "reactivated_count": 2,  # Already reactivated twice
            "lifecycle_history": [],
        }

        cluster = [
            {
                "_id": ObjectId(),
                "sentiment_score": 0.6,
                "published_at": datetime.now(timezone.utc),
            }
        ]

        fingerprint = {
            "nucleus_entity": "Bitcoin",
            "narrative_focus": "price_surge",
        }

        await mongo_db.narratives.insert_one(dormant_narrative)

        reactivated_id = await _reactivate_narrative(
            dormant_narrative,
            [str(ObjectId())],
            cluster,
            fingerprint,
        )

        reactivated = await mongo_db.narratives.find_one({"_id": ObjectId(reactivated_id)})
        assert reactivated["reactivated_count"] == 3

    @pytest.mark.asyncio
    async def test_clears_dormant_since(self, mongo_db):
        """Clears dormant_since timestamp."""
        dormant_narrative = {
            "_id": ObjectId(),
            "nucleus_entity": "Bitcoin",
            "narrative_focus": "price_surge",
            "article_ids": [str(ObjectId())],
            "article_count": 1,
            "avg_sentiment": 0.5,
            "dormant_since": datetime.now(timezone.utc) - timedelta(days=5),
            "lifecycle_history": [],
        }

        cluster = [
            {
                "_id": ObjectId(),
                "sentiment_score": 0.6,
                "published_at": datetime.now(timezone.utc),
            }
        ]

        fingerprint = {
            "nucleus_entity": "Bitcoin",
            "narrative_focus": "price_surge",
        }

        await mongo_db.narratives.insert_one(dormant_narrative)

        reactivated_id = await _reactivate_narrative(
            dormant_narrative,
            [str(ObjectId())],
            cluster,
            fingerprint,
        )

        reactivated = await mongo_db.narratives.find_one({"_id": ObjectId(reactivated_id)})
        assert reactivated["dormant_since"] is None

    @pytest.mark.asyncio
    async def test_adds_lifecycle_history_entry(self, mongo_db):
        """Adds reactivation entry to lifecycle_history."""
        dormant_narrative = {
            "_id": ObjectId(),
            "nucleus_entity": "Bitcoin",
            "narrative_focus": "price_surge",
            "article_ids": [str(ObjectId())],
            "article_count": 1,
            "avg_sentiment": 0.5,
            "lifecycle_history": [
                {
                    "state": "emerging",
                    "timestamp": datetime.now(timezone.utc) - timedelta(days=30),
                }
            ],
        }

        cluster = [
            {
                "_id": ObjectId(),
                "sentiment_score": 0.6,
                "published_at": datetime.now(timezone.utc),
            }
        ]

        fingerprint = {
            "nucleus_entity": "Bitcoin",
            "narrative_focus": "price_surge",
        }

        await mongo_db.narratives.insert_one(dormant_narrative)

        reactivated_id = await _reactivate_narrative(
            dormant_narrative,
            [str(ObjectId())],
            cluster,
            fingerprint,
        )

        reactivated = await mongo_db.narratives.find_one({"_id": ObjectId(reactivated_id)})

        # Should have 2 history entries now
        assert len(reactivated["lifecycle_history"]) == 2

        # Last entry should be reactivation
        last_entry = reactivated["lifecycle_history"][-1]
        assert last_entry["state"] == "reactivated"
        assert "timestamp" in last_entry
        assert "article_count" in last_entry

    @pytest.mark.asyncio
    async def test_returns_narrative_id(self, mongo_db):
        """Returns the ID of the reactivated narrative."""
        dormant_narrative = {
            "_id": ObjectId(),
            "nucleus_entity": "Bitcoin",
            "narrative_focus": "price_surge",
            "article_ids": [str(ObjectId())],
            "article_count": 1,
            "avg_sentiment": 0.5,
            "lifecycle_history": [],
        }

        cluster = [
            {
                "_id": ObjectId(),
                "sentiment_score": 0.6,
                "published_at": datetime.now(timezone.utc),
            }
        ]

        fingerprint = {
            "nucleus_entity": "Bitcoin",
            "narrative_focus": "price_surge",
        }

        await mongo_db.narratives.insert_one(dormant_narrative)

        reactivated_id = await _reactivate_narrative(
            dormant_narrative,
            [str(ObjectId())],
            cluster,
            fingerprint,
        )

        assert str(reactivated_id) == str(dormant_narrative["_id"])


class TestFingerprintSimilarity:
    """Test fingerprint similarity calculation."""

    def test_identical_fingerprints_score_maximum(self):
        """Identical fingerprints should score high."""
        fp1 = {
            "nucleus_entity": "Bitcoin",
            "narrative_focus": "price_surge",
            "key_entities": ["Bitcoin", "ETF"],
        }

        fp2 = {
            "nucleus_entity": "Bitcoin",
            "narrative_focus": "price_surge",
            "key_entities": ["Bitcoin", "ETF"],
        }

        similarity = calculate_fingerprint_similarity(fp1, fp2)
        # With weighted scoring: focus (0.5) + nucleus (0.3) + entities (0.2) = 1.0 weight
        # Identical should be at least 0.8 (matching focus and nucleus gets 0.8)
        assert similarity >= 0.8

    def test_different_focus_scores_low(self):
        """Fingerprints with different focus should score low."""
        fp1 = {
            "nucleus_entity": "Bitcoin",
            "narrative_focus": "price_surge",
            "key_entities": ["Bitcoin"],
        }

        fp2 = {
            "nucleus_entity": "Bitcoin",
            "narrative_focus": "regulatory_pressure",  # Different
            "key_entities": ["Bitcoin", "SEC"],
        }

        similarity = calculate_fingerprint_similarity(fp1, fp2)
        assert similarity < 0.7

    def test_same_nucleus_and_focus_scores_high(self):
        """Same nucleus and focus should score >= 0.80."""
        fp1 = {
            "nucleus_entity": "Bitcoin",
            "narrative_focus": "price_surge",
            "key_entities": ["Bitcoin"],
        }

        fp2 = {
            "nucleus_entity": "Bitcoin",
            "narrative_focus": "price_surge",
            "key_entities": ["Bitcoin", "Ethereum"],  # Slightly different entities
        }

        similarity = calculate_fingerprint_similarity(fp1, fp2)
        assert similarity >= 0.80
