import logging
import asyncio
from typing import Dict, Any, Optional, Union, Coroutine, TypeVar
from functools import wraps

from celery import shared_task
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..db.session import get_sessionmaker, get_engine
from ..db.models import Article, Source, Sentiment
from ..core.sentiment_analyzer import SentimentAnalyzer

logger = logging.getLogger(__name__)

# Type variable for coroutine return type
T = TypeVar("T")


def run_async(coro: Coroutine[None, None, T]) -> T:
    """
    Run an async function in the current event loop or a new one if needed.
    Handles both sync and async contexts.
    """
    try:
        # Try to get the running event loop
        loop = asyncio.get_event_loop()
    except RuntimeError:
        # No event loop, create a new one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if loop.is_running():
        # If loop is running, we're in an async context
        async def run():
            return await coro

        return loop.run_until_complete(run())
    else:
        # If loop is not running, we're in a sync context
        return loop.run_until_complete(coro)


async def _process_article_async(article_id: int) -> Dict[str, Any]:
    """Async function to process an article."""
    session_maker = get_sessionmaker()
    try:
        async with session_maker() as session:
            # Get the article
            result = await session.execute(
                select(Article).where(Article.id == article_id)
            )
            article = result.scalar_one_or_none()

            if not article:
                logger.error(f"Article {article_id} not found")
                return {"status": "error", "message": "Article not found"}

            # Check if sentiment analysis was already performed
            if article.sentiment_score is not None:
                logger.info(f"Article {article_id} already has sentiment analysis")
                return {
                    "status": "skipped",
                    "message": "Sentiment analysis already performed",
                }

            # Analyze sentiment
            sentiment = SentimentAnalyzer.analyze_article(
                article_text=article.content or "", title=article.title
            )

            # Update article with sentiment score
            article.sentiment_score = sentiment["polarity"]

            # Create sentiment record
            sentiment_record = Sentiment(
                article_id=article.id,
                score=sentiment["polarity"],
                label=sentiment["label"],
                subjectivity=sentiment["subjectivity"],
                raw_data=sentiment,
            )

            session.add(sentiment_record)
            await session.commit()

            logger.info(
                f"Processed article {article_id} - Score: {sentiment['polarity']}, Label: {sentiment['label']}"
            )
            return {
                "status": "success",
                "article_id": article_id,
                "sentiment": sentiment,
            }
    except Exception as e:
        logger.error(
            f"Error in _process for article {article_id}: {str(e)}", exc_info=True
        )
        try:
            if "session" in locals():
                await session.rollback()
        except Exception as rollback_error:
            logger.error(
                f"Error rolling back transaction for article {article_id}: {str(rollback_error)}",
                exc_info=True,
            )
        raise


async def process_article_async(article_id: int) -> Dict[str, Any]:
    """
    Async version of process_article that can be used in async contexts.
    """
    logger.info(f"Processing article ID: {article_id}")
    return await _process_article_async(article_id)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_article(self, article_id: int) -> Dict[str, Any]:
    """
    Process a single article through the sentiment analysis pipeline.

    This is the Celery task entry point that works in a sync context.

    Args:
        article_id: ID of the article to process

    Returns:
        Dict containing processing status and results
    """
    logger.info(f"Processing article ID: {article_id}")

    try:
        # Use run_async to handle both sync and async contexts
        return run_async(_process_article_async(article_id))
    except Exception as e:
        logger.error(f"Error processing article {article_id}: {str(e)}", exc_info=True)
        # Retry on error
        raise self.retry(exc=e)


async def _process_new_articles_async(batch_size: int = 10) -> Dict[str, Any]:
    """
    Async function to process new articles with batch commits for better performance.

    Args:
        batch_size: Number of articles to process before committing the transaction

    Returns:
        Dict with processing statistics
    """
    session_maker = get_sessionmaker()
    processed = 0
    skipped = 0
    errors = 0
    current_batch = 0

    try:
        async with session_maker() as session:
            # Find articles without sentiment analysis
            result = await session.execute(
                select(Article)
                .where(Article.sentiment_score.is_(None))
                .order_by(Article.published_at.desc())
            )
            articles = result.scalars().all()

            if not articles:
                logger.info("No new articles to process")
                return {
                    "status": "completed",
                    "total_articles": 0,
                    "processed": 0,
                    "skipped": 0,
                    "errors": 0,
                }

            logger.info(f"Found {len(articles)} articles to process")

            for article in articles:
                try:
                    # Process each article
                    sentiment = SentimentAnalyzer.analyze_article(
                        article_text=article.content or "", title=article.title
                    )

                    # Update article with sentiment score
                    article.sentiment_score = sentiment["polarity"]

                    # Create sentiment record
                    sentiment_record = Sentiment(
                        article_id=article.id,
                        score=sentiment["polarity"],
                        label=sentiment["label"],
                        subjectivity=sentiment["subjectivity"],
                        raw_data=sentiment,
                    )

                    session.add(sentiment_record)
                    current_batch += 1
                    processed += 1

                    # Commit in batches
                    if current_batch >= batch_size:
                        await session.commit()
                        logger.debug(f"Committed batch of {current_batch} articles")
                        current_batch = 0

                except Exception as e:
                    errors += 1
                    logger.error(
                        f"Error processing article {article.id}: {str(e)}",
                        exc_info=True,
                    )
                    # Continue with next article even if one fails

            # Commit any remaining items in the last batch
            if current_batch > 0:
                await session.commit()
                logger.debug(f"Committed final batch of {current_batch} articles")

            return {
                "status": "completed",
                "total_articles": len(articles),
                "processed": processed,
                "skipped": skipped,
                "errors": errors,
            }
    except Exception as e:
        logger.error(f"Error in _process_new_articles_async: {str(e)}", exc_info=True)
        raise


async def process_new_articles_async() -> Dict[str, Any]:
    """
    Async version of process_new_articles that can be used in async contexts.
    """
    logger.info("Starting to process new articles for sentiment analysis")
    return await _process_new_articles_async()


@shared_task
def process_new_articles() -> Dict[str, Any]:
    """
    Find and process all articles that haven't been analyzed yet.

    This is the Celery task entry point that works in a sync context.

    Returns:
        Dict with processing statistics
    """
    logger.info("Starting to process new articles for sentiment analysis")

    try:
        # Use run_async to handle both sync and async contexts
        return run_async(_process_new_articles_async())
    except Exception as e:
        logger.error(f"Error in process_new_articles: {str(e)}", exc_info=True)
        return {"status": "error", "error": str(e)}
