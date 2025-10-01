"""
Tests for the ArticleService class.
"""

import asyncio
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from bson import ObjectId
from pymongo.results import InsertOneResult, UpdateResult

from src.crypto_news_aggregator.services.article_service import (
    ArticleService,
    article_service,
)
from src.crypto_news_aggregator.models.article import (
    ArticleInDB,
    ArticleAuthor,
    ArticleMetrics,
)
from src.crypto_news_aggregator.models.sentiment import (
    SentimentAnalysis,
    SentimentLabel,
)

# Test data
TEST_ARTICLE_ID = "507f1f77bcf86cd799439011"
TEST_SENTIMENT = SentimentAnalysis(
    score=0.8, magnitude=0.9, label=SentimentLabel.POSITIVE, subjectivity=0.6
)


def create_test_article(article_id=TEST_ARTICLE_ID, **overrides):
    """Helper to create a test article dictionary."""
    article = {
        "id": ObjectId(article_id),
        "title": "Test Article",
        "source_id": "test-source-123",
        "source": "rss",
        "text": "This is a test article content.",
        "author": ArticleAuthor(
            id="author-123", name="Test Author", username="testauthor"
        ),
        "url": "https://example.com/test-article",
        "lang": "en",
        "metrics": ArticleMetrics(views=100, likes=10, replies=5, retweets=2, quotes=1),
        "keywords": ["test", "crypto"],
        "relevance_score": 0.8,
        "sentiment_score": 0.5,
        "sentiment_label": "neutral",
        "raw_data": {"original_source": "test"},
        "published_at": datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        "created_at": datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        "updated_at": datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        "description": "Test description",
        "image_url": "https://example.com/image.jpg",
        "tags": ["test", "crypto"],
        "entities": [],
    }
    article.update(overrides)
    return article


@pytest.fixture
def mock_collection():
    """Fixture that mocks the MongoDB collection."""
    with patch(
        "src.crypto_news_aggregator.services.article_service.mongo_manager.get_async_collection"
    ) as mock_get_collection:
        mock_collection = AsyncMock()
        mock_get_collection.return_value = mock_collection
        yield mock_collection


@pytest.mark.asyncio
class TestArticleService:
    """Test cases for ArticleService."""

    @pytest.mark.stable
    async def test_generate_fingerprint(self):
        """Test fingerprint generation is consistent."""
        service = ArticleService()
        title = "Test Title"
        content = "Test Content"

        # Generate fingerprint twice with same input
        fp1 = await service._generate_fingerprint(title, content)
        fp2 = await service._generate_fingerprint(title, content)

        # Should be the same
        assert fp1 == fp2

        # Different content should produce different fingerprint
        fp3 = await service._generate_fingerprint(title, "Different content")
        assert fp1 != fp3

    @pytest.mark.stable
    async def test_is_duplicate_finds_exact_match(self, mock_collection):
        """Test that exact duplicates are detected."""
        service = ArticleService()

        # Mock MongoDB to return a matching document
        mock_collection.find_one = AsyncMock(
            return_value={
                "_id": ObjectId(TEST_ARTICLE_ID),
                "fingerprint": "test_fingerprint",
            }
        )

        # Test with matching fingerprint
        is_dupe, orig_id = await service._is_duplicate(
            title="Test",
            content="Content",
            source_id="test",
            published_at=datetime.now(timezone.utc),
        )

        assert is_dupe is True
        assert str(orig_id) == TEST_ARTICLE_ID
        mock_collection.find_one.assert_called_once()

    @pytest.mark.broken(reason="Test successful article creation")
    async def test_create_article_success(self, mock_collection):
        """Test successful article creation."""
        service = ArticleService()
        article_data = create_test_article()

        # Mock MongoDB operations
        # First call to find_one (duplicate check) returns None
        # Second call returns the created article
        mock_collection.find_one = AsyncMock(side_effect=[None, article_data])
        mock_collection.insert_one = AsyncMock(
            return_value=InsertOneResult(
                inserted_id=ObjectId(TEST_ARTICLE_ID), acknowledged=True
            )
        )

        # Create article
        result = await service.create_article(article_data)

        # Verify result
        assert result is not None
        assert str(result.id) == TEST_ARTICLE_ID
        assert result.title == article_data["title"]

        # Verify insert was called with correct data
        args, _ = mock_collection.insert_one.call_args
        assert "fingerprint" in args[0]
        assert args[0]["title"] == article_data["title"]

    @pytest.mark.stable
    async def test_create_article_duplicate(self, mock_collection):
        """Test that duplicate articles are handled correctly."""
        service = ArticleService()
        article_data = create_test_article()

        # Mock MongoDB to return a duplicate
        mock_collection.find_one.return_value = {
            "_id": ObjectId(TEST_ARTICLE_ID),
            "fingerprint": "test_fingerprint",
        }

        # Mock update_duplicate_metadata
        with patch.object(
            service, "_update_duplicate_metadata", new_callable=AsyncMock
        ) as mock_update:
            # Create article (should be detected as duplicate)
            result = await service.create_article(article_data)

            # Should return None for duplicates
            assert result is None

            # Should have called update_duplicate_metadata
            mock_update.assert_awaited_once_with(
                ObjectId(TEST_ARTICLE_ID), article_data
            )

    @pytest.mark.broken(reason="Test retrieving an existing article")
    async def test_get_article_success(self, mock_collection):
        """Test retrieving an existing article."""
        service = ArticleService()
        article_data = create_test_article()

        # Mock MongoDB to return our test article
        mock_collection.find_one = AsyncMock(return_value=article_data)

        # Get the article
        result = await service.get_article(TEST_ARTICLE_ID)

        # Verify result
        assert result is not None
        assert str(result.id) == TEST_ARTICLE_ID
        assert result.title == article_data["title"]

        # Verify MongoDB was called with correct ID
        mock_collection.find_one.assert_awaited_once_with(
            {"_id": ObjectId(TEST_ARTICLE_ID)}
        )

    @pytest.mark.stable
    async def test_get_article_not_found(self, mock_collection):
        """Test retrieving a non-existent article."""
        service = ArticleService()

        # Mock MongoDB to return None (not found)
        mock_collection.find_one = AsyncMock(return_value=None)

        # Get non-existent article
        result = await service.get_article("507f1f77bcf86cd799439999")

        # Should return None
        assert result is None

    @pytest.mark.broken(reason="Test listing articles with various filters")
    async def test_list_articles_with_filters(self, mock_collection):
        """Test listing articles with various filters."""
        from unittest.mock import MagicMock

        service = ArticleService()
        test_articles = [create_test_article() for _ in range(3)]

        # Create a mock cursor that simulates MongoDB's async cursor with method chaining
        mock_cursor = MagicMock()

        # Set up method chaining
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor

        # Set up to_list to return our test articles
        async def to_list_async(*args, **kwargs):
            return [dict(art) for art in test_articles]

        mock_cursor.to_list.side_effect = to_list_async

        # Set up find to return our mock cursor
        mock_collection.find.return_value = mock_cursor

        # Set up count_documents to return a future that resolves to 3
        mock_collection.count_documents.return_value = 3

        # Ensure _get_collection returns our mock collection
        service._get_collection = AsyncMock(return_value=mock_collection)

        # List articles with filters
        articles, total = await service.list_articles(
            skip=0,
            limit=10,
            source_id="test-source",
            start_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2023, 12, 31, tzinfo=timezone.utc),
            keywords=["crypto"],
            min_sentiment=0.5,
            max_sentiment=1.0,
        )

        # Verify results
        assert len(articles) == 3
        assert total == 3

        # Verify MongoDB was called with correct query
        args, _ = mock_collection.find.call_args
        query = args[0]  # First positional arg is the query

        assert query["source.id"] == "test-source"
        assert "$gte" in query["published_at"]
        assert "$lte" in query["published_at"]
        assert "keywords" in query

    @pytest.mark.broken(reason="Test full-text search functionality")
    async def test_search_articles_functionality(self, mock_collection):
        """Test full-text search functionality."""
        service = ArticleService()
        test_articles = [create_test_article()]

        # Mock MongoDB operations
        mock_collection.count_documents.return_value = 1

        # Create a mock cursor for the aggregate result
        mock_aggregate_cursor = AsyncMock()
        mock_aggregate_cursor.to_list.return_value = test_articles

        # Set up aggregate() to return our mock cursor
        mock_collection.aggregate.return_value = mock_aggregate_cursor

        # Perform search
        articles, total = await service.search_articles(
            query="bitcoin price",
            skip=0,
            limit=10,
            source_id="test-source",
            start_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2023, 12, 31, tzinfo=timezone.utc),
        )

        # Verify results
        assert len(articles) == 1
        assert total == 1
        assert articles[0].title == "Test Article"

        # Verify MongoDB was called with correct pipeline
        args, _ = mock_collection.aggregate.call_args
        pipeline = args[0]
        assert len(pipeline) == 5  # match + addFields + sort + skip + limit

        # Verify text search in $match
        assert "$match" in pipeline[0]
        assert "$and" in pipeline[0]["$match"]
        assert "$text" in pipeline[0]["$match"]["$and"][0]
        assert pipeline[0]["$match"]["$and"][0]["$text"] == {
            "$caseSensitive": False,
            "$search": "bitcoin price",
        }

        # Verify sort by text score
        assert pipeline[2]["$sort"] == {"score": {"$meta": "textScore"}}

    @pytest.mark.stable
    async def test_update_article_sentiment_success(self, mock_collection):
        """Test updating article sentiment."""
        service = ArticleService()

        # Mock successful update
        mock_collection.update_one.return_value = UpdateResult(
            raw_result={"nModified": 1, "ok": 1.0}, acknowledged=True
        )

        # Update sentiment
        result = await service.update_article_sentiment(
            article_id=TEST_ARTICLE_ID, sentiment=TEST_SENTIMENT
        )

        # Should return True for success
        assert result is True

        # Verify MongoDB was called with correct update
        args, _ = mock_collection.update_one.call_args
        query, update = args

        assert query == {"_id": ObjectId(TEST_ARTICLE_ID)}
        assert "$set" in update
        assert "sentiment" in update["$set"]
        assert "updated_at" in update["$set"]

    @pytest.mark.stable
    async def test_update_article_sentiment_failure(self, mock_collection):
        """Test failed sentiment update."""
        service = ArticleService()

        # Test with error return value (no document modified)
        mock_collection.update_one.return_value = UpdateResult(
            raw_result={"nModified": 0, "ok": 1.0}, acknowledged=True
        )

        # Should return False when no document was modified
        result = await service.update_article_sentiment(
            article_id=TEST_ARTICLE_ID, sentiment=TEST_SENTIMENT
        )
        assert result is False

        # Test with exception
        mock_collection.update_one.side_effect = Exception("Connection error")
        mock_collection.update_one.return_value = None

        # Should handle the exception and return False
        result = await service.update_article_sentiment(
            article_id=TEST_ARTICLE_ID, sentiment=TEST_SENTIMENT
        )
        assert result is False
