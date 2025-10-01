"""Tests for batch processing functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from crypto_news_aggregator.db.models import Article, Sentiment
from crypto_news_aggregator.tasks.process_article import _process_new_articles_async


@pytest.mark.asyncio
async def test_batch_processing_small_batch():
    """Test batch processing with batch size smaller than number of articles."""
    # Create test data (5 articles)
    test_articles = [
        Article(
            id=i,
            title=f"Batch Test Article {i}",
            content=f"This is batch test article {i} about cryptocurrency.",
            url=f"https://example.com/batch-test-{i}",
            published_at=datetime.now(timezone.utc) - timedelta(hours=i),
            source_id="test-source",
        )
        for i in range(1, 6)  # 5 articles
    ]

    # Setup mocks
    mock_session = AsyncMock(spec=AsyncSession)
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = test_articles
    mock_session.execute.return_value = result_mock

    # Make the mock session work as an async context manager
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = None

    # Mock sentiment analyzer
    mock_sentiment = {"polarity": 0.5, "subjectivity": 0.5, "label": "Neutral"}

    with (
        patch(
            "crypto_news_aggregator.tasks.process_article.get_sessionmaker",
            return_value=MagicMock(return_value=mock_session),
        ),
        patch(
            "crypto_news_aggregator.core.sentiment_analyzer.SentimentAnalyzer.analyze_article",
            return_value=mock_sentiment,
        ),
    ):
        # Process with batch size of 2 (should result in 3 commits)
        result = await _process_new_articles_async(batch_size=2)

        # Verify results
        assert result["status"] == "completed"
        assert result["total_articles"] == 5
        assert result["processed"] == 5
        assert result["errors"] == 0

        # Verify commit was called for each batch (3 times: 2+2+1)
        assert mock_session.commit.await_count == 3
        assert mock_session.add.call_count == 5


@pytest.mark.asyncio
async def test_batch_processing_large_batch():
    """Test batch processing with batch size larger than number of articles."""
    # Create test data (3 articles)
    test_articles = [
        Article(
            id=i,
            title=f"Large Batch Test {i}",
            content=f"This is large batch test {i}.",
            url=f"https://example.com/large-batch-{i}",
            published_at=datetime.now(timezone.utc) - timedelta(hours=i),
            source_id="test-source",
        )
        for i in range(1, 4)  # 3 articles
    ]

    # Setup mocks
    mock_session = AsyncMock(spec=AsyncSession)
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = test_articles
    mock_session.execute.return_value = result_mock

    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = None

    # Mock sentiment analyzer
    mock_sentiment = {"polarity": 0.5, "subjectivity": 0.5, "label": "Neutral"}

    with (
        patch(
            "crypto_news_aggregator.tasks.process_article.get_sessionmaker",
            return_value=MagicMock(return_value=mock_session),
        ),
        patch(
            "crypto_news_aggregator.core.sentiment_analyzer.SentimentAnalyzer.analyze_article",
            return_value=mock_sentiment,
        ),
    ):
        # Process with batch size of 10 (larger than number of articles)
        result = await _process_new_articles_async(batch_size=10)

        # Verify results
        assert result["status"] == "completed"
        assert result["total_articles"] == 3
        assert result["processed"] == 3
        assert result["errors"] == 0

        # Should be just 1 commit for all articles
        mock_session.commit.assert_awaited_once()
        assert mock_session.add.call_count == 3


@pytest.mark.asyncio
async def test_batch_processing_empty():
    """Test batch processing with no articles to process."""
    # Setup mocks for empty result
    mock_session = AsyncMock(spec=AsyncSession)
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = result_mock

    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = None

    with patch(
        "crypto_news_aggregator.tasks.process_article.get_sessionmaker",
        return_value=MagicMock(return_value=mock_session),
    ):
        result = await _process_new_articles_async()

        # Verify results
        assert result["status"] == "completed"
        assert result["total_articles"] == 0
        assert result["processed"] == 0
        assert result["errors"] == 0

        # No commits or adds should have happened
        mock_session.commit.assert_not_awaited()
        mock_session.add.assert_not_called()


@pytest.mark.asyncio
async def test_batch_processing_with_errors():
    """Test batch processing with some articles failing to process."""
    # Create test data (4 articles)
    test_articles = [
        Article(
            id=i,
            title=f"Error Test {i}",
            content=f"This is error test {i}.",
            url=f"https://example.com/error-test-{i}",
            published_at=datetime.now(timezone.utc) - timedelta(hours=i),
            source_id="test-source",
        )
        for i in range(1, 5)  # 4 articles
    ]

    # Setup mocks
    mock_session = AsyncMock(spec=AsyncSession)
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = test_articles
    mock_session.execute.return_value = result_mock

    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = None

    # Mock sentiment analyzer to fail on article with ID 2 and 4
    def mock_analyze_article(article_text, title):
        article_id = int(title.split()[-1])
        if article_id in [2, 4]:  # Fail on articles 2 and 4
            raise ValueError(f"Test error processing article {article_id}")
        return {"polarity": 0.5, "subjectivity": 0.5, "label": "Neutral"}

    with (
        patch(
            "crypto_news_aggregator.tasks.process_article.get_sessionmaker",
            return_value=MagicMock(return_value=mock_session),
        ),
        patch(
            "crypto_news_aggregator.core.sentiment_analyzer.SentimentAnalyzer.analyze_article",
            side_effect=mock_analyze_article,
        ),
    ):
        # Process with batch size of 2
        result = await _process_new_articles_async(batch_size=2)

        # Verify results - should process 2 successfully, 2 errors
        assert result["status"] == "completed"
        assert result["total_articles"] == 4
        assert result["processed"] == 2  # 2 successful
        assert result["errors"] == 2  # 2 failed

        # Should be 1 commit at the end (batch commit)
        assert mock_session.commit.await_count == 1
        # Should only have added 2 sentiment records (for successful articles 1 and 3)
        assert mock_session.add.call_count == 2

        # Verify the correct articles were processed successfully
        added_article_ids = [
            call[0][0].article_id for call in mock_session.add.call_args_list
        ]
        assert sorted(added_article_ids) == [
            1,
            3,
        ]  # Articles 2 and 4 should have failed
