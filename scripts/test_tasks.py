import asyncio
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import Celery app and tasks
from crypto_news_aggregator.tasks import app
from crypto_news_aggregator.tasks.news import (
    fetch_news,
    analyze_sentiment,
    process_article,
)
from crypto_news_aggregator.tasks.trends import (
    update_trends,
    calculate_article_keywords,
)


async def test_tasks():
    logger.info("Starting task queue tests...")

    # Test 1: Direct task execution
    logger.info("\n--- Testing direct task execution ---")
    try:
        result = fetch_news.delay()
        logger.info(f"Scheduled fetch_news task with ID: {result.id}")
        logger.info(f"Task status: {result.status}")
    except Exception as e:
        logger.error(f"Error scheduling fetch_news task: {e}")

    # Test 2: Task with arguments
    try:
        result = analyze_sentiment.delay(article_id=1)
        logger.info(f"\nScheduled analyze_sentiment task with ID: {result.id}")
        logger.info(f"Task status: {result.status}")
    except Exception as e:
        logger.error(f"Error scheduling analyze_sentiment task: {e}")

    # Test 3: Task with complex data
    try:
        article_data = {
            "title": "Test Article",
            "content": "This is a test article content.",
            "url": "https://example.com/test-article",
            "published_at": datetime.utcnow().isoformat(),
            "source_id": 1,
        }
        result = process_article.delay(article_data)
        logger.info(f"\nScheduled process_article task with ID: {result.id}")
        logger.info(f"Task status: {result.status}")
    except Exception as e:
        logger.error(f"Error scheduling process_article task: {e}")

    # Test 4: Scheduled task (trends update)
    try:
        result = update_trends.delay(time_window="24h")
        logger.info(f"\nScheduled update_trends task with ID: {result.id}")
        logger.info(f"Task status: {result.status}")
    except Exception as e:
        logger.error(f"Error scheduling update_trends task: {e}")


if __name__ == "__main__":
    asyncio.run(test_tasks())
