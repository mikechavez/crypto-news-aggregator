"""
Integration tests for narrative reactivation functionality.

Tests cover:
- End-to-end reactivation flow from decision to completion
- Detect narratives with reactivation integration
- Timeline continuity across reactivation
- Lifecycle state transitions
- Multiple article clustering with reactivation
"""

import pytest
from datetime import datetime, timezone, timedelta
from bson import ObjectId

from src.crypto_news_aggregator.services.narrative_service import (
    detect_narratives,
    should_reactivate_or_create_new,
    _reactivate_narrative,
)


class TestReactivationIntegration:
    """Integration tests for end-to-end reactivation flow."""

    @pytest.mark.asyncio
    async def test_reactivation_preserves_timeline_continuity(self, mongo_db):
        """Reactivation should preserve and extend timeline data."""
        now = datetime.now(timezone.utc)
        dormant_since = now - timedelta(days=5)

        # Create dormant narrative with history
        dormant_narrative = {
            "_id": ObjectId(),
            "nucleus_entity": "Bitcoin",
            "narrative_focus": "institutional_adoption",
            "title": "Bitcoin ETF Adoption",
            "lifecycle_state": "dormant",
            "dormant_since": dormant_since,
            "article_ids": [ObjectId(), ObjectId()],
            "article_count": 2,
            "avg_sentiment": 0.65,
            "lifecycle_history": [
                {
                    "state": "emerging",
                    "timestamp": now - timedelta(days=30),
                    "article_count": 3,
                    "mention_velocity": 0.15,
                },
                {
                    "state": "hot",
                    "timestamp": now - timedelta(days=20),
                    "article_count": 8,
                    "mention_velocity": 0.5,
                },
                {
                    "state": "cooling",
                    "timestamp": now - timedelta(days=10),
                    "article_count": 5,
                    "mention_velocity": 0.25,
                },
                {
                    "state": "dormant",
                    "timestamp": dormant_since,
                    "article_count": 2,
                    "mention_velocity": 0.0,
                },
            ],
            "fingerprint": {
                "nucleus_entity": "Bitcoin",
                "narrative_focus": "institutional_adoption",
                "key_entities": ["Bitcoin", "ETF"],
            },
        }

        await mongo_db.narratives.insert_one(dormant_narrative)

        # Create new articles matching dormant narrative
        new_articles = [
            {
                "_id": ObjectId(),
                "title": "Bitcoin ETF Gains New Institutional Interest",
                "text": "Major institutions renew bitcoin ETF allocations",
                "url": "https://example.com/btc-etf-1",
                "sentiment_score": 0.7,
                "published_at": now - timedelta(hours=2),
            },
            {
                "_id": ObjectId(),
                "title": "Bitcoin Spot ETF Momentum Continues",
                "text": "Bitcoin spot ETF market expands",
                "url": "https://example.com/btc-etf-2",
                "sentiment_score": 0.6,
                "published_at": now - timedelta(hours=1),
            },
        ]

        await mongo_db.articles.insert_many(new_articles)

        # Trigger reactivation
        fingerprint = {
            "nucleus_entity": "Bitcoin",
            "narrative_focus": "institutional_adoption",
            "key_entities": ["Bitcoin", "ETF"],
        }

        decision, matched = await should_reactivate_or_create_new(
            fingerprint, nucleus_entity="Bitcoin"
        )

        assert decision == "reactivate"

        # Process reactivation
        new_article_ids = [str(article["_id"]) for article in new_articles]
        reactivated_id = await _reactivate_narrative(
            matched, new_article_ids, new_articles, fingerprint
        )

        # Verify timeline continuity
        reactivated = await mongo_db.narratives.find_one({"_id": ObjectId(reactivated_id)})

        # Should have 5 history entries (4 original + 1 reactivation)
        assert len(reactivated["lifecycle_history"]) == 5

        # History should be in chronological order
        history = reactivated["lifecycle_history"]
        for i in range(len(history) - 1):
            assert history[i]["timestamp"] <= history[i + 1]["timestamp"]

        # Last entry should be reactivation
        assert history[-1]["state"] == "reactivated"

        # Article count should increase
        assert reactivated["article_count"] > 2

    @pytest.mark.asyncio
    async def test_reactivation_handles_overlapping_articles(self, mongo_db):
        """Should handle overlap when same article appears in multiple sources."""
        now = datetime.now(timezone.utc)
        dormant_since = now - timedelta(days=5)

        shared_article = ObjectId()
        exclusive_old = ObjectId()
        exclusive_new = ObjectId()

        dormant_narrative = {
            "_id": ObjectId(),
            "nucleus_entity": "Ethereum",
            "narrative_focus": "protocol_upgrade",
            "title": "Ethereum Upgrade",
            "lifecycle_state": "dormant",
            "dormant_since": dormant_since,
            "article_ids": [str(shared_article), str(exclusive_old)],
            "article_count": 2,
            "avg_sentiment": 0.7,
            "lifecycle_history": [],
            "fingerprint": {
                "nucleus_entity": "Ethereum",
                "narrative_focus": "protocol_upgrade",
                "key_entities": ["Ethereum"],
            },
        }

        await mongo_db.narratives.insert_one(dormant_narrative)

        # New articles: some overlap, some exclusive
        new_articles = [
            {
                "_id": shared_article,
                "url": "https://example.com/eth-overlap",
                "sentiment_score": 0.7,
                "published_at": now - timedelta(hours=2),
            },
            {
                "_id": exclusive_new,
                "url": "https://example.com/eth-new",
                "sentiment_score": 0.8,
                "published_at": now - timedelta(hours=1),
            },
        ]

        await mongo_db.articles.insert_many(new_articles)

        # Reactivate
        fingerprint = {
            "nucleus_entity": "Ethereum",
            "narrative_focus": "protocol_upgrade",
            "key_entities": ["Ethereum"],
        }

        decision, matched = await should_reactivate_or_create_new(
            fingerprint, nucleus_entity="Ethereum"
        )

        new_article_ids = [str(article["_id"]) for article in new_articles]
        reactivated_id = await _reactivate_narrative(
            matched, new_article_ids, new_articles, fingerprint
        )

        reactivated = await mongo_db.narratives.find_one({"_id": ObjectId(reactivated_id)})

        # Should have 3 unique articles (2 old + 2 new - 1 shared = 3)
        assert reactivated["article_count"] == 3
        article_ids = set(reactivated["article_ids"])
        assert len(article_ids) == 3

    @pytest.mark.asyncio
    async def test_reactivation_updates_last_updated_timestamp(self, mongo_db):
        """Should update last_updated when reactivating."""
        now = datetime.now(timezone.utc)
        dormant_since = now - timedelta(days=5)
        old_timestamp = now - timedelta(days=20)

        dormant_narrative = {
            "_id": ObjectId(),
            "nucleus_entity": "Bitcoin",
            "narrative_focus": "price_surge",
            "title": "Bitcoin Price Surge",
            "lifecycle_state": "dormant",
            "dormant_since": dormant_since,
            "last_updated": old_timestamp,  # Old timestamp
            "article_ids": [str(ObjectId())],
            "article_count": 1,
            "avg_sentiment": 0.5,
            "lifecycle_history": [],
            "fingerprint": {
                "nucleus_entity": "Bitcoin",
                "narrative_focus": "price_surge",
                "key_entities": ["Bitcoin"],
            },
        }

        await mongo_db.narratives.insert_one(dormant_narrative)

        new_articles = [
            {
                "_id": ObjectId(),
                "url": "https://example.com/bitcoin-timestamp-update",
                "sentiment_score": 0.7,
                "published_at": now - timedelta(hours=1),
            }
        ]

        await mongo_db.articles.insert_many(new_articles)

        fingerprint = {
            "nucleus_entity": "Bitcoin",
            "narrative_focus": "price_surge",
            "key_entities": ["Bitcoin"],
        }

        decision, matched = await should_reactivate_or_create_new(
            fingerprint, nucleus_entity="Bitcoin"
        )

        new_article_ids = [str(article["_id"]) for article in new_articles]
        reactivated_id = await _reactivate_narrative(
            matched, new_article_ids, new_articles, fingerprint
        )

        reactivated = await mongo_db.narratives.find_one({"_id": ObjectId(reactivated_id)})

        # last_updated should be recent (within last few seconds)
        time_diff = (now - reactivated["last_updated"]).total_seconds()
        assert time_diff < 5  # Should be very recent

    @pytest.mark.asyncio
    async def test_multiple_dormant_narratives_with_same_entity(self, mongo_db):
        """Should select best match when multiple narratives exist for same entity."""
        now = datetime.now(timezone.utc)
        dormant_since = now - timedelta(days=5)

        # Create multiple dormant narratives for same nucleus_entity
        dormant_1 = {
            "_id": ObjectId(),
            "nucleus_entity": "Bitcoin",
            "narrative_focus": "price_surge",
            "lifecycle_state": "dormant",
            "dormant_since": dormant_since,
            "article_ids": [str(ObjectId())],
            "article_count": 1,
            "avg_sentiment": 0.5,
            "lifecycle_history": [],
            "fingerprint": {
                "nucleus_entity": "Bitcoin",
                "narrative_focus": "price_surge",
                "key_entities": ["Bitcoin"],
            },
        }

        dormant_2 = {
            "_id": ObjectId(),
            "nucleus_entity": "Bitcoin",
            "narrative_focus": "institutional_adoption",  # Different focus
            "lifecycle_state": "dormant",
            "dormant_since": dormant_since,
            "article_ids": [str(ObjectId())],
            "article_count": 1,
            "avg_sentiment": 0.5,
            "lifecycle_history": [],
            "fingerprint": {
                "nucleus_entity": "Bitcoin",
                "narrative_focus": "institutional_adoption",
                "key_entities": ["Bitcoin", "ETF"],
            },
        }

        await mongo_db.narratives.insert_many([dormant_1, dormant_2])

        # Test with fingerprint matching dormant_2
        fingerprint = {
            "nucleus_entity": "Bitcoin",
            "narrative_focus": "institutional_adoption",
            "key_entities": ["Bitcoin", "ETF"],
        }

        decision, matched = await should_reactivate_or_create_new(
            fingerprint, nucleus_entity="Bitcoin"
        )

        # Should match dormant_2, not dormant_1
        assert decision == "reactivate"
        assert matched["_id"] == dormant_2["_id"]

    @pytest.mark.asyncio
    async def test_reactivation_with_zero_velocity_articles(self, mongo_db):
        """Should handle articles published at same time (zero velocity articles)."""
        now = datetime.now(timezone.utc)
        dormant_since = now - timedelta(days=5)

        dormant_narrative = {
            "_id": ObjectId(),
            "nucleus_entity": "Solana",
            "narrative_focus": "network_recovery",
            "lifecycle_state": "dormant",
            "dormant_since": dormant_since,
            "article_ids": [str(ObjectId())],
            "article_count": 1,
            "avg_sentiment": 0.5,
            "lifecycle_history": [],
            "fingerprint": {
                "nucleus_entity": "Solana",
                "narrative_focus": "network_recovery",
                "key_entities": ["Solana"],
            },
        }

        await mongo_db.narratives.insert_one(dormant_narrative)

        # Articles published at same time
        same_time = now - timedelta(hours=1)
        new_articles = [
            {
                "_id": ObjectId(),
                "url": "https://example.com/solana-recovery-1",
                "sentiment_score": 0.6,
                "published_at": same_time,
            },
            {
                "_id": ObjectId(),
                "url": "https://example.com/solana-recovery-2",
                "sentiment_score": 0.7,
                "published_at": same_time,
            },
        ]

        await mongo_db.articles.insert_many(new_articles)

        fingerprint = {
            "nucleus_entity": "Solana",
            "narrative_focus": "network_recovery",
            "key_entities": ["Solana"],
        }

        decision, matched = await should_reactivate_or_create_new(
            fingerprint, nucleus_entity="Solana"
        )

        new_article_ids = [str(article["_id"]) for article in new_articles]
        reactivated_id = await _reactivate_narrative(
            matched, new_article_ids, new_articles, fingerprint
        )

        reactivated = await mongo_db.narratives.find_one({"_id": ObjectId(reactivated_id)})

        # Should complete without error
        assert reactivated["article_count"] == 3
        assert reactivated["lifecycle_state"] == "reactivated"

    @pytest.mark.asyncio
    async def test_reactivation_with_empty_lifecycle_history(self, mongo_db):
        """Should handle dormant narratives with missing lifecycle_history."""
        now = datetime.now(timezone.utc)
        dormant_since = now - timedelta(days=5)

        # Narrative without lifecycle_history
        dormant_narrative = {
            "_id": ObjectId(),
            "nucleus_entity": "Cardano",
            "narrative_focus": "governance",
            "lifecycle_state": "dormant",
            "dormant_since": dormant_since,
            "article_ids": [str(ObjectId())],
            "article_count": 1,
            "avg_sentiment": 0.5,
            # Missing lifecycle_history
            "fingerprint": {
                "nucleus_entity": "Cardano",
                "narrative_focus": "governance",
                "key_entities": ["Cardano"],
            },
        }

        await mongo_db.narratives.insert_one(dormant_narrative)

        new_articles = [
            {
                "_id": ObjectId(),
                "url": "https://example.com/bitcoin-update",
                "sentiment_score": 0.6,
                "published_at": now - timedelta(hours=1),
            }
        ]

        await mongo_db.articles.insert_many(new_articles)

        fingerprint = {
            "nucleus_entity": "Cardano",
            "narrative_focus": "governance",
            "key_entities": ["Cardano"],
        }

        decision, matched = await should_reactivate_or_create_new(
            fingerprint, nucleus_entity="Cardano"
        )

        new_article_ids = [str(article["_id"]) for article in new_articles]

        # Should not raise error even though lifecycle_history is missing
        reactivated_id = await _reactivate_narrative(
            matched, new_article_ids, new_articles, fingerprint
        )

        reactivated = await mongo_db.narratives.find_one({"_id": ObjectId(reactivated_id)})

        # Should have created lifecycle_history
        assert "lifecycle_history" in reactivated
        assert len(reactivated["lifecycle_history"]) > 0

    @pytest.mark.asyncio
    async def test_edge_case_single_article_reactivation(self, mongo_db):
        """Should handle reactivation with single new article."""
        now = datetime.now(timezone.utc)
        dormant_since = now - timedelta(days=5)

        dormant_narrative = {
            "_id": ObjectId(),
            "nucleus_entity": "Polygon",
            "narrative_focus": "scaling",
            "lifecycle_state": "dormant",
            "dormant_since": dormant_since,
            "article_ids": [str(ObjectId())],
            "article_count": 1,
            "avg_sentiment": 0.5,
            "lifecycle_history": [],
            "fingerprint": {
                "nucleus_entity": "Polygon",
                "narrative_focus": "scaling",
                "key_entities": ["Polygon"],
            },
        }

        await mongo_db.narratives.insert_one(dormant_narrative)

        # Single new article
        new_article = {
            "_id": ObjectId(),
            "url": "https://example.com/polygon-scaling",
            "sentiment_score": 0.8,
            "published_at": now - timedelta(hours=1),
        }

        await mongo_db.articles.insert_one(new_article)

        fingerprint = {
            "nucleus_entity": "Polygon",
            "narrative_focus": "scaling",
            "key_entities": ["Polygon"],
        }

        decision, matched = await should_reactivate_or_create_new(
            fingerprint, nucleus_entity="Polygon"
        )

        reactivated_id = await _reactivate_narrative(
            matched, [str(new_article["_id"])], [new_article], fingerprint
        )

        reactivated = await mongo_db.narratives.find_one({"_id": ObjectId(reactivated_id)})

        # (0.5 * 1 + 0.8 * 1) / 2 = 1.3 / 2 = 0.65
        expected_sentiment = 0.65
        assert abs(reactivated["avg_sentiment"] - expected_sentiment) < 0.01

    @pytest.mark.asyncio
    async def test_reactivation_idempotency(self, mongo_db):
        """Should handle re-reactivation correctly."""
        now = datetime.now(timezone.utc)
        dormant_since = now - timedelta(days=5)

        # Narrative that was previously reactivated
        previously_reactivated = {
            "_id": ObjectId(),
            "nucleus_entity": "Bitcoin",
            "narrative_focus": "adoption",
            "lifecycle_state": "dormant",  # Went dormant again
            "dormant_since": dormant_since,
            "article_ids": [str(ObjectId()), str(ObjectId())],
            "article_count": 2,
            "avg_sentiment": 0.6,
            "reactivated_count": 1,  # Already reactivated once
            "lifecycle_history": [
                {"state": "emerging", "timestamp": now - timedelta(days=30)},
                {"state": "reactivated", "timestamp": now - timedelta(days=10)},
                {"state": "dormant", "timestamp": dormant_since},
            ],
            "fingerprint": {
                "nucleus_entity": "Bitcoin",
                "narrative_focus": "adoption",
                "key_entities": ["Bitcoin"],
            },
        }

        await mongo_db.narratives.insert_one(previously_reactivated)

        new_articles = [
            {
                "_id": ObjectId(),
                "url": "https://example.com/bitcoin-re-adoption",
                "sentiment_score": 0.7,
                "published_at": now - timedelta(hours=1),
            }
        ]

        await mongo_db.articles.insert_many(new_articles)

        fingerprint = {
            "nucleus_entity": "Bitcoin",
            "narrative_focus": "adoption",
            "key_entities": ["Bitcoin"],
        }

        decision, matched = await should_reactivate_or_create_new(
            fingerprint, nucleus_entity="Bitcoin"
        )

        new_article_ids = [str(article["_id"]) for article in new_articles]
        reactivated_id = await _reactivate_narrative(
            matched, new_article_ids, new_articles, fingerprint
        )

        reactivated = await mongo_db.narratives.find_one({"_id": ObjectId(reactivated_id)})

        # reactivated_count should increment
        assert reactivated["reactivated_count"] == 2

        # Should have another reactivation entry in history
        history_states = [h["state"] for h in reactivated["lifecycle_history"]]
        assert history_states.count("reactivated") == 2
