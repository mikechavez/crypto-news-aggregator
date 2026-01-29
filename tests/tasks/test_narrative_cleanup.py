"""
Tests for narrative cleanup tasks.

Tests validation logic for article references and data integrity.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from bson import ObjectId

from crypto_news_aggregator.tasks.narrative_cleanup import (
    cleanup_invalid_article_references,
    update_article_narrative_references,
    validate_narrative_data_integrity
)


@pytest.fixture
def mock_mongo_manager():
    """Mock MongoDB manager."""
    return MagicMock()


@pytest.mark.asyncio
async def test_cleanup_invalid_article_references():
    """Test cleanup of invalid article references."""
    with patch("crypto_news_aggregator.tasks.narrative_cleanup.mongo_manager") as mock_mongo:
        # Setup mock database
        mock_db = MagicMock()
        mock_narratives = MagicMock()
        mock_articles = MagicMock()
        mock_db.narratives = mock_narratives
        mock_db.articles = mock_articles

        # Setup mock narratives with mixed valid/invalid articles
        oid1 = ObjectId()
        oid2 = ObjectId()
        oid3 = ObjectId()
        oid_invalid = ObjectId()

        mock_narratives.find.return_value.to_list = AsyncMock(
            return_value=[
                {
                    "_id": ObjectId(),
                    "article_ids": [str(oid1), str(oid2), str(oid_invalid)],
                    "article_count": 3,
                    "lifecycle_state": "emerging"
                },
                {
                    "_id": ObjectId(),
                    "article_ids": [str(oid3)],
                    "article_count": 1,
                    "lifecycle_state": "hot"
                }
            ]
        )

        # Mock articles.distinct to return only valid articles
        async def mock_distinct(field, query):
            # Return valid articles only
            if "$in" in query["_id"]:
                ids = query["_id"]["$in"]
                return [aid for aid in ids if aid != oid_invalid]
            return []

        mock_articles.distinct = mock_distinct

        # Mock update_one
        mock_narratives.update_one = AsyncMock()

        # Setup get_async_database
        async def get_db():
            return mock_db

        mock_mongo.get_async_database = get_db

        # Run cleanup
        result = await cleanup_invalid_article_references()

        # Verify results
        assert result["narratives_processed"] == 2
        assert result["invalid_references_removed"] == 1  # One invalid reference removed
        assert result["narratives_updated"] == 1  # Only first narrative had invalid refs


@pytest.mark.asyncio
async def test_cleanup_preserves_valid_articles():
    """Test that cleanup preserves valid articles."""
    with patch("crypto_news_aggregator.tasks.narrative_cleanup.mongo_manager") as mock_mongo:
        mock_db = MagicMock()
        mock_narratives = MagicMock()
        mock_articles = MagicMock()
        mock_db.narratives = mock_narratives
        mock_db.articles = mock_articles

        # Create valid article IDs
        valid_ids = [str(ObjectId()) for _ in range(3)]

        mock_narratives.find.return_value.to_list = AsyncMock(
            return_value=[
                {
                    "_id": ObjectId(),
                    "article_ids": valid_ids,
                    "article_count": 3,
                    "lifecycle_state": "hot"
                }
            ]
        )

        # All articles are valid
        async def mock_distinct(field, query):
            return [ObjectId(aid) for aid in valid_ids]

        mock_articles.distinct = mock_distinct
        mock_narratives.update_one = AsyncMock()

        async def get_db():
            return mock_db

        mock_mongo.get_async_database = get_db

        # Run cleanup
        result = await cleanup_invalid_article_references()

        # Verify no updates were made (all articles valid)
        assert result["invalid_references_removed"] == 0
        assert result["narratives_updated"] == 0


@pytest.mark.asyncio
async def test_update_article_narrative_references():
    """Test updating article references to survivor narratives."""
    with patch("crypto_news_aggregator.tasks.narrative_cleanup.mongo_manager") as mock_mongo:
        mock_db = MagicMock()
        mock_narratives = MagicMock()
        mock_articles = MagicMock()
        mock_db.narratives = mock_narratives
        mock_db.articles = mock_articles

        merged_id = ObjectId()
        survivor_id = ObjectId()

        # Mock narratives with merged_into reference
        mock_narratives.find.return_value.to_list = AsyncMock(
            return_value=[
                {
                    "_id": merged_id,
                    "merged_into": survivor_id,
                    "article_ids": ["article1", "article2"]
                }
            ]
        )

        # Mock articles to update
        mock_articles.find.return_value.to_list = AsyncMock(
            return_value=[
                {"_id": ObjectId(), "narrative_id": merged_id},
                {"_id": ObjectId(), "narrative_id": merged_id}
            ]
        )

        # Mock update_many
        mock_result = MagicMock()
        mock_result.modified_count = 2
        mock_articles.update_many = AsyncMock(return_value=mock_result)

        async def get_db():
            return mock_db

        mock_mongo.get_async_database = get_db

        # Run update
        result = await update_article_narrative_references(dry_run=False)

        # Verify results
        assert result["articles_updated"] == 2
        assert result["narratives_with_merged_refs"] == 1


@pytest.mark.asyncio
async def test_update_article_narrative_references_dry_run():
    """Test dry run mode doesn't make changes."""
    with patch("crypto_news_aggregator.tasks.narrative_cleanup.mongo_manager") as mock_mongo:
        mock_db = MagicMock()
        mock_narratives = MagicMock()
        mock_articles = MagicMock()
        mock_db.narratives = mock_narratives
        mock_db.articles = mock_articles

        merged_id = ObjectId()
        survivor_id = ObjectId()

        # Mock narratives
        mock_narratives.find.return_value.to_list = AsyncMock(
            return_value=[
                {
                    "_id": merged_id,
                    "merged_into": survivor_id,
                    "article_ids": ["article1"]
                }
            ]
        )

        # Mock articles
        mock_articles.find.return_value.to_list = AsyncMock(
            return_value=[
                {"_id": ObjectId(), "narrative_id": merged_id}
            ]
        )

        mock_articles.update_many = AsyncMock()

        async def get_db():
            return mock_db

        mock_mongo.get_async_database = get_db

        # Run dry run
        result = await update_article_narrative_references(dry_run=True)

        # Verify no updates were made
        mock_articles.update_many.assert_not_called()
        assert result["articles_updated"] == 0


@pytest.mark.asyncio
async def test_validate_narrative_data_integrity_count_mismatch():
    """Test validation detects count mismatches."""
    with patch("crypto_news_aggregator.tasks.narrative_cleanup.mongo_manager") as mock_mongo:
        mock_db = MagicMock()
        mock_narratives = MagicMock()
        mock_articles = MagicMock()
        mock_db.narratives = mock_narratives
        mock_db.articles = mock_articles

        oid1 = ObjectId()
        oid2 = ObjectId()

        # Narrative has article_count=5 but only 2 article_ids
        mock_narratives.find.return_value.to_list = AsyncMock(
            return_value=[
                {
                    "_id": ObjectId(),
                    "article_ids": [str(oid1), str(oid2)],
                    "article_count": 5,  # Mismatch!
                    "lifecycle_state": "hot"
                }
            ]
        )

        # All articles are valid
        async def mock_distinct(field, query):
            return [oid1, oid2]

        mock_articles.distinct = mock_distinct

        async def get_db():
            return mock_db

        mock_mongo.get_async_database = get_db

        # Run validation
        result = await validate_narrative_data_integrity()

        # Verify count mismatch detected
        assert result["total_narratives"] == 1
        assert len(result["count_mismatches"]) == 1
        assert result["count_mismatches"][0]["expected"] == 5
        assert result["count_mismatches"][0]["actual"] == 2


@pytest.mark.asyncio
async def test_validate_narrative_data_integrity_invalid_references():
    """Test validation detects invalid article references."""
    with patch("crypto_news_aggregator.tasks.narrative_cleanup.mongo_manager") as mock_mongo:
        mock_db = MagicMock()
        mock_narratives = MagicMock()
        mock_articles = MagicMock()
        mock_db.narratives = mock_narratives
        mock_db.articles = mock_articles

        oid1 = ObjectId()
        oid_invalid = ObjectId()

        # Narrative has article IDs, one is invalid
        mock_narratives.find.return_value.to_list = AsyncMock(
            return_value=[
                {
                    "_id": ObjectId(),
                    "article_ids": [str(oid1), str(oid_invalid)],
                    "article_count": 2,
                    "lifecycle_state": "hot"
                }
            ]
        )

        # Only valid articles returned
        async def mock_distinct(field, query):
            return [oid1]  # Only one valid

        mock_articles.distinct = mock_distinct

        async def get_db():
            return mock_db

        mock_mongo.get_async_database = get_db

        # Run validation
        result = await validate_narrative_data_integrity()

        # Verify invalid references detected
        assert len(result["invalid_references"]) == 1
        assert result["invalid_references"][0]["total"] == 2
        assert result["invalid_references"][0]["valid"] == 1


@pytest.mark.asyncio
async def test_validate_narrative_data_integrity_duplicates():
    """Test validation detects duplicate article IDs."""
    with patch("crypto_news_aggregator.tasks.narrative_cleanup.mongo_manager") as mock_mongo:
        mock_db = MagicMock()
        mock_narratives = MagicMock()
        mock_articles = MagicMock()
        mock_db.narratives = mock_narratives
        mock_db.articles = mock_articles

        oid1 = ObjectId()

        # Narrative has duplicate article IDs
        mock_narratives.find.return_value.to_list = AsyncMock(
            return_value=[
                {
                    "_id": ObjectId(),
                    "article_ids": [str(oid1), str(oid1), str(oid1)],  # Duplicates!
                    "article_count": 3,
                    "lifecycle_state": "hot"
                }
            ]
        )

        # All articles are valid
        async def mock_distinct(field, query):
            return [oid1]

        mock_articles.distinct = mock_distinct

        async def get_db():
            return mock_db

        mock_mongo.get_async_database = get_db

        # Run validation
        result = await validate_narrative_data_integrity()

        # Verify duplicates detected
        assert len(result["duplicates"]) == 1
        assert result["duplicates"][0]["total"] == 3
        assert result["duplicates"][0]["unique"] == 1


@pytest.mark.asyncio
async def test_validate_narrative_data_integrity_empty_active():
    """Test validation detects empty active narratives."""
    with patch("crypto_news_aggregator.tasks.narrative_cleanup.mongo_manager") as mock_mongo:
        mock_db = MagicMock()
        mock_narratives = MagicMock()
        mock_articles = MagicMock()
        mock_db.narratives = mock_narratives
        mock_db.articles = mock_articles

        # Narrative is "hot" but has no articles
        mock_narratives.find.return_value.to_list = AsyncMock(
            return_value=[
                {
                    "_id": ObjectId(),
                    "article_ids": [],  # Empty!
                    "article_count": 0,
                    "lifecycle_state": "hot"  # Active state
                }
            ]
        )

        async def mock_distinct(field, query):
            return []

        mock_articles.distinct = mock_distinct

        async def get_db():
            return mock_db

        mock_mongo.get_async_database = get_db

        # Run validation
        result = await validate_narrative_data_integrity()

        # Verify empty active narratives detected
        assert len(result["empty_narratives"]) == 1
        assert result["empty_narratives"][0]["lifecycle_state"] == "hot"


@pytest.mark.asyncio
async def test_validate_narrative_data_integrity_multiple_issues():
    """Test validation with multiple issues in same narrative."""
    with patch("crypto_news_aggregator.tasks.narrative_cleanup.mongo_manager") as mock_mongo:
        mock_db = MagicMock()
        mock_narratives = MagicMock()
        mock_articles = MagicMock()
        mock_db.narratives = mock_narratives
        mock_db.articles = mock_articles

        oid1 = ObjectId()

        # Narrative with multiple issues:
        # - Count mismatch (5 vs 3)
        # - Duplicates (1 appears 3 times)
        # - Some invalid references
        mock_narratives.find.return_value.to_list = AsyncMock(
            return_value=[
                {
                    "_id": ObjectId(),
                    "article_ids": [str(oid1), str(oid1), str(oid1)],
                    "article_count": 5,  # Mismatch: says 5
                    "lifecycle_state": "hot"
                }
            ]
        )

        async def mock_distinct(field, query):
            return [oid1]  # Only one valid

        mock_articles.distinct = mock_distinct

        async def get_db():
            return mock_db

        mock_mongo.get_async_database = get_db

        # Run validation
        result = await validate_narrative_data_integrity()

        # Verify all issues detected in single narrative
        assert len(result["count_mismatches"]) == 1
        assert len(result["duplicates"]) == 1
        assert len(result["invalid_references"]) == 1
