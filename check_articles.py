#!/usr/bin/env python3
"""
Script to query and display articles from MongoDB.
"""
import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from crypto_news_aggregator.db.mongodb import mongo_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def check_articles_collection():
    """Check what's in the articles collection."""
    try:
        db = await mongo_manager.get_async_database()
        collection = db.articles

        # Count total articles
        total_count = await collection.count_documents({})
        logger.info(f"Total articles in database: {total_count}")

        if total_count == 0:
            logger.info("No articles found in database.")
            return

        # Get recent articles (last 7 days instead of 24 hours)
        recent_query = {
            "created_at": {
                "$gte": datetime.utcnow().timestamp() - (7 * 24 * 60 * 60)  # Last 7 days
            }
        }
        recent_count = await collection.count_documents(recent_query)
        logger.info(f"Articles from last 7 days: {recent_count}")

        # Get articles with sentiment analysis
        analyzed_query = {
            "sentiment_score": {"$exists": True, "$ne": None}
        }
        analyzed_count = await collection.count_documents(analyzed_query)
        logger.info(f"Articles with sentiment analysis: {analyzed_count}")

        # Get sample of recent articles (by database insertion time)
        recent_articles = collection.find().sort("created_at", -1).limit(10)

        logger.info("\n=== Most Recent Articles by DB Insertion Time ===")
        async for article in recent_articles:
            logger.info(f"Title: {article.get('title', 'No title')}")
            logger.info(f"Source: {article.get('source', 'No source')}")
            logger.info(f"DB Created: {article.get('created_at', 'No date')}")
            if 'published_at' in article:
                logger.info(f"Published: {article.get('published_at', 'No published date')}")
            logger.info(f"Sentiment: {article.get('sentiment_score', 'No sentiment')}")
            logger.info("---")

        # Check for articles without analysis
        unanalyzed_query = {
            "$or": [
                {"sentiment_score": {"$exists": False}},
                {"sentiment_score": None}
            ]
        }
        unanalyzed_count = await collection.count_documents(unanalyzed_query)
        logger.info(f"Articles needing analysis: {unanalyzed_count}")

    except Exception as e:
        logger.error(f"Error checking articles: {str(e)}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(check_articles_collection())
