#!/usr/bin/env python3
"""
Script to query and display articles from the database.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy.future import select
from sqlalchemy import desc

# Add project root to Python path
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from crypto_news_aggregator.db.session import get_sessionmaker
from crypto_news_aggregator.db.models import Article, Source

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)

async def query_recent_articles(limit: int = 10):
    """Query and display recently collected articles."""
    session_maker = get_sessionmaker()
    
    try:
        async with session_maker() as session:
            # Get the most recent articles
            result = await session.execute(
                select(Article)
                .join(Source)
                .order_by(desc(Article.published_at))
                .limit(limit)
            )
            
            articles = result.scalars().all()
            
            if not articles:
                logger.info("No articles found in the database.")
                return
            
            logger.info(f"Found {len(articles)} recent articles:")
            logger.info("-" * 80)
            
            for i, article in enumerate(articles, 1):
                logger.info(f"{i}. {article.title}")
                logger.info(f"   Source: {article.source.name if article.source else 'Unknown'}")
                logger.info(f"   Published: {article.published_at}")
                logger.info(f"   URL: {article.url}")
                if article.description:
                    logger.info(f"   Description: {article.description[:150]}...")
                logger.info("-" * 80)
                
    except Exception as e:
        logger.error(f"Error querying articles: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(query_recent_articles(limit=5))
