import pytest
from unittest.mock import AsyncMock, patch, MagicMock, call, AsyncMock
from datetime import datetime, timezone, timedelta
from typing import AsyncGenerator

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from crypto_news_aggregator.db.models import Article, Sentiment, Source
from crypto_news_aggregator.tasks.process_article import (
    _process_article_async,
    _process_new_articles_async,
    process_article_async,
    process_new_articles_async,
)


# Helper function to create a mock async session
async def create_mock_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a mock async session for testing."""
    async with AsyncMock(spec=AsyncSession) as session:
        yield session


@pytest.mark.asyncio
async def test_process_article_success():
    """Test successful processing of an article with sentiment analysis."""
    # Create a test article in the database
    test_article = Article(
        id=1,
        title="Test Article",
        content="This is a positive test article about cryptocurrency.",
        url="https://example.com/test-article",
        published_at=datetime.now(timezone.utc),
        source_id="test-source",
    )

    # Create a mock session that implements the async context manager protocol
    mock_session = AsyncMock(spec=AsyncSession)

    # Mock the query result
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = test_article
    mock_session.execute.return_value = result_mock

    # Create a mock sessionmaker that returns our mock session
    session_maker_mock = MagicMock()
    session_maker_mock.return_value = mock_session

    # Make the mock session work as an async context manager
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = None

    # Mock the sentiment analyzer
    mock_sentiment = {"polarity": 0.8, "subjectivity": 0.6, "label": "Positive"}

    with (
        patch(
            "crypto_news_aggregator.tasks.process_article.get_sessionmaker",
            return_value=session_maker_mock,
        ),
        patch(
            "crypto_news_aggregator.core.sentiment_analyzer.SentimentAnalyzer.analyze_article",
            return_value=mock_sentiment,
        ),
    ):
        # Call the async function directly
        result = await _process_article_async(1)

        # Verify the result
        assert result["status"] == "success"
        assert result["article_id"] == 1
        assert result["sentiment"]["polarity"] == 0.8

        # Verify the article was updated
        assert test_article.sentiment_score == 0.8

        # Verify a sentiment record was created
        mock_session.add.assert_called_once()
        sentiment_arg = mock_session.add.call_args[0][0]
        assert isinstance(sentiment_arg, Sentiment)
        assert sentiment_arg.article_id == 1
        assert sentiment_arg.score == 0.8
        assert sentiment_arg.label == "Positive"
        assert sentiment_arg.subjectivity == 0.6

        # Verify the session was committed
        mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_article_not_found():
    """Test processing a non-existent article."""
    # Create a mock session that implements the async context manager protocol
    mock_session = AsyncMock(spec=AsyncSession)

    # Mock the query result to return None (article not found)
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = result_mock

    # Create a mock sessionmaker that returns our mock session
    session_maker_mock = MagicMock()
    session_maker_mock.return_value = mock_session

    # Make the mock session work as an async context manager
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = None

    with patch(
        "crypto_news_aggregator.tasks.process_article.get_sessionmaker",
        return_value=session_maker_mock,
    ):
        # Call the async function directly
        result = await _process_article_async(999)  # Non-existent ID

        # Verify the result
        assert result["status"] == "error"
        assert "not found" in result["message"].lower()

        # Verify no sentiment was added
        mock_session.add.assert_not_called()
        mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_process_new_articles():
    """Test finding and processing multiple new articles."""
    # Create test data
    test_articles = [
        Article(
            id=i,
            title=f"Test Article {i}",
            content=f"This is test article {i} about cryptocurrency.",
            url=f"https://example.com/test-article-{i}",
            published_at=datetime.now(timezone.utc) - timedelta(hours=i),
            source_id="test-source",
        )
        for i in range(1, 4)
    ]

    # Create a mock session that implements the async context manager protocol
    mock_session = AsyncMock(spec=AsyncSession)

    # Mock the query result for new articles
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = test_articles
    mock_session.execute.return_value = result_mock

    # Create a mock sessionmaker that returns our mock session
    session_maker_mock = MagicMock()
    session_maker_mock.return_value = mock_session

    # Make the mock session work as an async context manager
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = None

    # Mock the sentiment analyzer
    mock_sentiment = {"polarity": 0.5, "subjectivity": 0.5, "label": "Neutral"}

    with (
        patch(
            "crypto_news_aggregator.tasks.process_article.get_sessionmaker",
            return_value=session_maker_mock,
        ),
        patch(
            "crypto_news_aggregator.core.sentiment_analyzer.SentimentAnalyzer.analyze_article",
            return_value=mock_sentiment,
        ),
    ):
        # Call the async function directly
        result = await _process_new_articles_async()

        # Verify the result
        assert result["status"] == "completed"
        assert result["total_articles"] == 3
        assert result["processed"] == 3
        assert result["errors"] == 0

        # Verify the query was executed once to get articles
        assert mock_session.execute.await_count == 1

        # Verify sentiment was added for each article (3 total)
        assert mock_session.add.call_count == 3
        for i in range(3):
            sentiment_arg = mock_session.add.call_args_list[i][0][0]
            assert isinstance(sentiment_arg, Sentiment)
            assert sentiment_arg.article_id == i + 1
            assert sentiment_arg.score == 0.5
            assert sentiment_arg.label == "Neutral"

        # Should be 1 commit at the end (batch commit)
        mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_article_error_handling():
    """Test error handling during article processing."""
    # Create a test article
    test_article = Article(
        id=1,
        title="Test Article",
        content="This is a test article.",
        url="https://example.com/test-article",
        published_at=datetime.now(timezone.utc),
        source_id="test-source",
    )

    # Create a mock session that implements the async context manager protocol
    mock_session = AsyncMock(spec=AsyncSession)

    # Mock the query result
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = test_article
    mock_session.execute.return_value = result_mock

    # Create a mock sessionmaker that returns our mock session
    session_maker_mock = MagicMock()
    session_maker_mock.return_value = mock_session

    # Make the mock session work as an async context manager
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = None

    # Mock the sentiment analyzer to raise an exception
    with (
        patch(
            "crypto_news_aggregator.tasks.process_article.get_sessionmaker",
            return_value=session_maker_mock,
        ),
        patch(
            "crypto_news_aggregator.core.sentiment_analyzer.SentimentAnalyzer.analyze_article",
            side_effect=Exception("Analysis failed"),
        ),
    ):
        # Call the async function directly and expect an exception
        with pytest.raises(Exception, match="Analysis failed"):
            await _process_article_async(1)

        # Verify the session was rolled back
        mock_session.rollback.assert_awaited_once()
        # Verify commit was not called
        mock_session.commit.assert_not_called()

        # Verify the article was not updated
        assert test_article.sentiment_score is None
