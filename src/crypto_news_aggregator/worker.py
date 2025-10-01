import asyncio
import logging

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from crypto_news_aggregator.tasks.price_monitor import get_price_monitor
from crypto_news_aggregator.background.rss_fetcher import schedule_rss_fetch
from crypto_news_aggregator.core.config import get_settings
from crypto_news_aggregator.db.mongodb import initialize_mongodb, mongo_manager

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


async def main():
    """Initializes and runs all background tasks."""
    logger.info("--- Starting background worker process ---")
    settings = get_settings()
    await initialize_mongodb()
    logger.info("MongoDB connection initialized for worker.")

    tasks = []
    if not settings.TESTING:
        price_monitor = get_price_monitor()
        logger.info("Starting price monitor task...")
        tasks.append(asyncio.create_task(price_monitor.start()))
        logger.info("Price monitor task created.")

        rss_interval = 60 * 30  # 30 minutes
        logger.info("Starting RSS ingestion schedule (every %s seconds)", rss_interval)
        tasks.append(asyncio.create_task(schedule_rss_fetch(rss_interval)))
        logger.info("RSS ingestion task created.")

    if not tasks:
        logger.warning("No background tasks to run. Worker will exit.")
        return

    logger.info(f"{len(tasks)} background task(s) are running.")

    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        logger.info("Worker process received cancellation request.")
    finally:
        logger.info("Shutting down worker process...")
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await mongo_manager.aclose()
        logger.info("Worker process shut down gracefully.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker process stopped by user.")
