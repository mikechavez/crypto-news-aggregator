"""
Tests for article pagination in narratives API endpoint.

Tests the /api/v1/narratives/{narrative_id}/articles endpoint with pagination parameters.
"""

import pytest
from datetime import datetime, timezone
from bson import ObjectId
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.fixture
def sample_narrative_id():
    """Sample narrative ObjectId."""
    return str(ObjectId())


@pytest.fixture
def sample_article_ids():
    """Generate 184 sample article ObjectIds."""
    return [str(ObjectId()) for _ in range(184)]


@pytest.fixture
def sample_articles(sample_article_ids):
    """Generate sample articles with all article IDs."""
    articles = []
    for i, article_id in enumerate(sample_article_ids):
        articles.append({
            "_id": ObjectId(article_id),
            "title": f"Article {i+1}",
            "url": f"https://example.com/article-{i+1}",
            "source": "CoinDesk",
            "published_at": datetime(2025, 10, 1, 12, 0, 0, tzinfo=timezone.utc)
        })
    return articles


@pytest.fixture
def sample_narrative(sample_narrative_id, sample_article_ids):
    """Sample narrative document with 184 articles."""
    return {
        "_id": ObjectId(sample_narrative_id),
        "theme": "Coinbase News",
        "title": "Coinbase News and Updates",
        "summary": "Latest news about Coinbase",
        "entities": ["Coinbase", "SEC"],
        "article_ids": sample_article_ids,
        "article_count": len(sample_article_ids),
        "mention_velocity": 2.5,
        "lifecycle": "hot",
        "lifecycle_state": "hot",
        "first_seen": datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        "last_updated": datetime(2025, 10, 6, 14, 20, 0, tzinfo=timezone.utc),
        "days_active": 279,
    }


@pytest.fixture
def small_narrative_id():
    """Sample small narrative ObjectId."""
    return str(ObjectId())


@pytest.fixture
def small_article_ids():
    """Generate 15 sample article ObjectIds."""
    return [str(ObjectId()) for _ in range(15)]


@pytest.fixture
def small_articles(small_article_ids):
    """Generate sample articles for small narrative."""
    articles = []
    for i, article_id in enumerate(small_article_ids):
        articles.append({
            "_id": ObjectId(article_id),
            "title": f"Small Article {i+1}",
            "url": f"https://example.com/small-article-{i+1}",
            "source": "CoinDesk",
            "published_at": datetime(2025, 10, 1, 12, 0, 0, tzinfo=timezone.utc)
        })
    return articles


@pytest.fixture
def small_narrative(small_narrative_id, small_article_ids):
    """Sample narrative document with 15 articles."""
    return {
        "_id": ObjectId(small_narrative_id),
        "theme": "Small Narrative",
        "title": "Small Narrative Title",
        "summary": "A small narrative with few articles",
        "entities": ["Entity1"],
        "article_ids": small_article_ids,
        "article_count": len(small_article_ids),
        "mention_velocity": 0.5,
        "lifecycle": "emerging",
        "lifecycle_state": "emerging",
        "first_seen": datetime(2025, 10, 1, 0, 0, 0, tzinfo=timezone.utc),
        "last_updated": datetime(2025, 10, 1, 14, 20, 0, tzinfo=timezone.utc),
        "days_active": 1,
    }


@pytest.mark.asyncio
async def test_get_articles_pagination_default(sample_narrative_id, sample_articles):
    """Test default pagination (offset=0, limit=20)."""
    from crypto_news_aggregator.db.mongodb import mongo_manager

    with patch.object(mongo_manager, "get_async_database") as mock_get_db:
        # Setup mock database
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db

        # Setup narratives collection mock
        mock_narratives = AsyncMock()
        mock_db.narratives = mock_narratives

        # Setup articles collection mock - NOT AsyncMock!
        mock_articles = MagicMock()
        mock_db.articles = mock_articles

        # Create mock narrative
        narrative_doc = {
            "_id": ObjectId(sample_narrative_id),
            "article_ids": [article["_id"] for article in sample_articles],
        }
        mock_narratives.find_one = AsyncMock(return_value=narrative_doc)

        # Create mock articles cursor (first 20)
        first_page_articles = sample_articles[:20]

        # Motor cursors are async-iterable but find/sort/limit are sync
        # Mock the chained methods: find().sort().limit()
        async def async_iterator():
            for article in first_page_articles:
                yield article

        mock_cursor = MagicMock()
        mock_cursor.__aiter__ = MagicMock(return_value=async_iterator())
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)

        mock_articles.find.return_value = mock_cursor

        # Import and call endpoint
        from crypto_news_aggregator.api.v1.endpoints.narratives import get_articles_paginated

        result = await get_articles_paginated(
            narrative_id=sample_narrative_id,
            offset=0,
            limit=20,
            db=mock_db
        )

        # Verify response structure
        assert "articles" in result
        assert "total_count" in result
        assert "offset" in result
        assert "limit" in result
        assert "has_more" in result

        # Verify pagination metadata
        assert result["offset"] == 0
        assert result["limit"] == 20
        assert result["total_count"] == 184
        assert result["has_more"] is True
        assert len(result["articles"]) == 20


@pytest.mark.asyncio
async def test_get_articles_pagination_second_page(sample_narrative_id, sample_articles):
    """Test fetching second page (offset=20, limit=20)."""
    from crypto_news_aggregator.db.mongodb import mongo_manager

    with patch.object(mongo_manager, "get_async_database") as mock_get_db:
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db

        mock_narratives = AsyncMock()
        mock_db.narratives = mock_narratives

        mock_articles = MagicMock()
        mock_db.articles = mock_articles

        narrative_doc = {
            "_id": ObjectId(sample_narrative_id),
            "article_ids": [article["_id"] for article in sample_articles],
        }
        mock_narratives.find_one = AsyncMock(return_value=narrative_doc)

        # Second page articles (20-40)
        second_page_articles = sample_articles[20:40]

        # Mock the chained methods: find().sort().limit()
        async def async_iterator():
            for article in second_page_articles:
                yield article

        mock_cursor = MagicMock()
        mock_cursor.__aiter__ = MagicMock(return_value=async_iterator())
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)

        mock_articles.find.return_value = mock_cursor

        from crypto_news_aggregator.api.v1.endpoints.narratives import get_articles_paginated

        result = await get_articles_paginated(
            narrative_id=sample_narrative_id,
            offset=20,
            limit=20,
            db=mock_db
        )

        assert result["offset"] == 20
        assert result["has_more"] is True
        assert len(result["articles"]) == 20


@pytest.mark.asyncio
async def test_get_articles_pagination_last_page(sample_narrative_id, sample_articles):
    """Test fetching last page with partial results."""
    from crypto_news_aggregator.db.mongodb import mongo_manager

    with patch.object(mongo_manager, "get_async_database") as mock_get_db:
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db

        mock_narratives = AsyncMock()
        mock_db.narratives = mock_narratives

        mock_articles = MagicMock()
        mock_db.articles = mock_articles

        narrative_doc = {
            "_id": ObjectId(sample_narrative_id),
            "article_ids": [article["_id"] for article in sample_articles],
        }
        mock_narratives.find_one = AsyncMock(return_value=narrative_doc)

        # Last page articles (180-184 = 4 remaining)
        last_page_articles = sample_articles[180:184]

        # Mock the chained methods: find().sort().limit()
        async def async_iterator():
            for article in last_page_articles:
                yield article

        mock_cursor = MagicMock()
        mock_cursor.__aiter__ = MagicMock(return_value=async_iterator())
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)

        mock_articles.find.return_value = mock_cursor

        from crypto_news_aggregator.api.v1.endpoints.narratives import get_articles_paginated

        result = await get_articles_paginated(
            narrative_id=sample_narrative_id,
            offset=180,
            limit=20,
            db=mock_db
        )

        assert result["offset"] == 180
        assert result["has_more"] is False
        assert len(result["articles"]) == 4
        assert result["total_count"] == 184


@pytest.mark.asyncio
async def test_get_articles_limit_exceeds_max(sample_narrative_id, sample_narrative):
    """Test limit validation (max 50)."""
    from fastapi import HTTPException

    from crypto_news_aggregator.db.mongodb import mongo_manager

    with patch.object(mongo_manager, "get_async_database") as mock_get_db:
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db

        from crypto_news_aggregator.api.v1.endpoints.narratives import get_articles_paginated

        with pytest.raises(HTTPException) as exc_info:
            await get_articles_paginated(
                narrative_id=sample_narrative_id,
                offset=0,
                limit=100,  # Exceeds max of 50
                db=mock_db
            )

        assert exc_info.value.status_code == 400
        assert "cannot exceed 50" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_get_articles_negative_offset(sample_narrative_id):
    """Test negative offset validation."""
    from fastapi import HTTPException
    from crypto_news_aggregator.db.mongodb import mongo_manager

    with patch.object(mongo_manager, "get_async_database") as mock_get_db:
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db

        from crypto_news_aggregator.api.v1.endpoints.narratives import get_articles_paginated

        with pytest.raises(HTTPException) as exc_info:
            await get_articles_paginated(
                narrative_id=sample_narrative_id,
                offset=-10,
                limit=20,
                db=mock_db
            )

        assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_get_articles_narrative_with_few_articles(small_narrative_id, small_articles):
    """Test narrative with <20 articles."""
    from crypto_news_aggregator.db.mongodb import mongo_manager

    with patch.object(mongo_manager, "get_async_database") as mock_get_db:
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db

        mock_narratives = AsyncMock()
        mock_db.narratives = mock_narratives

        mock_articles = MagicMock()
        mock_db.articles = mock_articles

        narrative_doc = {
            "_id": ObjectId(small_narrative_id),
            "article_ids": [article["_id"] for article in small_articles],
        }
        mock_narratives.find_one = AsyncMock(return_value=narrative_doc)

        # All articles returned (only 15)
        # Mock the chained methods: find().sort().limit()
        async def async_iterator():
            for article in small_articles:
                yield article

        mock_cursor = MagicMock()
        mock_cursor.__aiter__ = MagicMock(return_value=async_iterator())
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)

        mock_articles.find.return_value = mock_cursor

        from crypto_news_aggregator.api.v1.endpoints.narratives import get_articles_paginated

        result = await get_articles_paginated(
            narrative_id=small_narrative_id,
            offset=0,
            limit=20,
            db=mock_db
        )

        assert result["total_count"] == 15
        assert len(result["articles"]) == 15
        assert result["has_more"] is False


@pytest.mark.asyncio
async def test_get_articles_narrative_not_found(sample_narrative_id):
    """Test requesting articles for non-existent narrative."""
    from fastapi import HTTPException
    from crypto_news_aggregator.db.mongodb import mongo_manager

    with patch.object(mongo_manager, "get_async_database") as mock_get_db:
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db

        mock_narratives = AsyncMock()
        mock_db.narratives = mock_narratives
        mock_narratives.find_one.return_value = None  # Not found

        from crypto_news_aggregator.api.v1.endpoints.narratives import get_articles_paginated

        with pytest.raises(HTTPException) as exc_info:
            await get_articles_paginated(
                narrative_id=sample_narrative_id,
                offset=0,
                limit=20,
                db=mock_db
            )

        assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_articles_invalid_narrative_id():
    """Test with invalid narrative ID format."""
    from fastapi import HTTPException
    from crypto_news_aggregator.db.mongodb import mongo_manager

    with patch.object(mongo_manager, "get_async_database") as mock_get_db:
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db

        from crypto_news_aggregator.api.v1.endpoints.narratives import get_articles_paginated

        with pytest.raises(HTTPException) as exc_info:
            await get_articles_paginated(
                narrative_id="not-a-valid-id",
                offset=0,
                limit=20,
                db=mock_db
            )

        assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_get_articles_offset_beyond_total(sample_narrative_id, sample_articles):
    """Test offset beyond total articles."""
    from crypto_news_aggregator.db.mongodb import mongo_manager

    with patch.object(mongo_manager, "get_async_database") as mock_get_db:
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db

        mock_narratives = AsyncMock()
        mock_db.narratives = mock_narratives

        mock_articles = AsyncMock()
        mock_db.articles = mock_articles

        narrative_doc = {
            "_id": ObjectId(sample_narrative_id),
            "article_ids": [article["_id"] for article in sample_articles],
        }
        mock_narratives.find_one = AsyncMock(return_value=narrative_doc)

        # Empty result (offset beyond total)
        # Mock the chained methods: find().sort().limit()
        mock_limit = AsyncMock()
        mock_limit.__aiter__.return_value = iter([])

        mock_sort = MagicMock()
        mock_sort.limit.return_value = mock_limit

        mock_articles.find.return_value = mock_sort

        from crypto_news_aggregator.api.v1.endpoints.narratives import get_articles_paginated

        result = await get_articles_paginated(
            narrative_id=sample_narrative_id,
            offset=200,  # Beyond 184 total
            limit=20,
            db=mock_db
        )

        assert len(result["articles"]) == 0
        assert result["has_more"] is False


@pytest.mark.asyncio
async def test_get_articles_empty_narrative(sample_narrative_id):
    """Test narrative with no articles."""
    from crypto_news_aggregator.db.mongodb import mongo_manager

    with patch.object(mongo_manager, "get_async_database") as mock_get_db:
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db

        mock_narratives = AsyncMock()
        mock_db.narratives = mock_narratives

        mock_articles = AsyncMock()
        mock_db.articles = mock_articles

        narrative_doc = {
            "_id": ObjectId(sample_narrative_id),
            "article_ids": [],
        }
        mock_narratives.find_one.return_value = narrative_doc

        # Mock the chained methods: find().sort().limit()
        mock_limit = AsyncMock()
        mock_limit.__aiter__.return_value = iter([])

        mock_sort = MagicMock()
        mock_sort.limit.return_value = mock_limit

        mock_articles.find.return_value = mock_sort

        from crypto_news_aggregator.api.v1.endpoints.narratives import get_articles_paginated

        result = await get_articles_paginated(
            narrative_id=sample_narrative_id,
            offset=0,
            limit=20,
            db=mock_db
        )

        assert result["total_count"] == 0
        assert len(result["articles"]) == 0
        assert result["has_more"] is False
