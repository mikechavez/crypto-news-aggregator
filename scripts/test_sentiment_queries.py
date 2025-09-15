#!/usr/bin/env python3
"""
Smoke test for MongoDB-backed sentiment queries using ArticleService.

Prerequisites:
- Export MONGODB_URI to point at a running MongoDB instance.
- Ensure the database has some articles with `keywords` and `sentiment.score` fields.

Usage:
    python scripts/test_sentiment_queries.py BTC ETH SOL
"""
import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import List

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("sentiment_query_test")

# Ensure project root on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from crypto_news_aggregator.core.config import get_settings
from crypto_news_aggregator.db.mongodb import initialize_mongodb, mongo_manager
from crypto_news_aggregator.services.article_service import ArticleService


async def main(symbols: List[str]) -> int:
    settings = get_settings()
    if not settings.MONGODB_URI:
        logger.error("MONGODB_URI is not set. Please export it or add it to your .env file.")
        return 2

    logger.info("Initializing MongoDB...")
    ok = await initialize_mongodb()
    if not ok:
        logger.error("Failed to initialize MongoDB. Aborting.")
        return 3

    logger.info("Querying average sentiment for symbols: %s", symbols)
    svc = ArticleService()
    sentiment_map = await svc.get_average_sentiment_for_symbols(symbols, days_ago=14)

    logger.info("Results:")
    for sym in symbols:
        logger.info("%s => %s", sym, sentiment_map.get(sym))

    # Clean up
    await mongo_manager.aclose()
    return 0


if __name__ == "__main__":
    syms = sys.argv[1:] or ["BTC", "ETH", "SOL"]
    rc = asyncio.run(main(syms))
    sys.exit(rc)
