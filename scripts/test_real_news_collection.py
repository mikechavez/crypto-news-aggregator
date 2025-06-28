#!/usr/bin/env python3
"""
Test script for collecting real news articles using the NewsCollector.

This script demonstrates how to use the NewsCollector to fetch real news articles
from the NewsAPI, with proper error handling and rate limiting.
"""
import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text, func

from crypto_news_aggregator.db.models import Article, Source

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from newsapi import NewsApiClient

from crypto_news_aggregator.core.news_collector import NewsCollector
from crypto_news_aggregator.core.config import get_settings
from crypto_news_aggregator.db.session import get_sessionmaker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('news_collection_test.log')
    ]
)
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

async def test_news_collection():
    """Test the news collection with real API calls."""
    # Get session maker
    session_maker = get_sessionmaker()
    
    # Verify database connection
    try:
        async with session_maker() as session:
            await session.execute(text("SELECT 1"))
            # Verify we can query the sources table
            result = await session.execute(select(Source).limit(1))
            logger.info("✅ Successfully connected to the database")
    except Exception as e:
        logger.error(f"❌ Failed to connect to the database: {str(e)}")
        logger.error("Please ensure the database is running and accessible")
        logger.error("You may need to run migrations first: `alembic upgrade head`")
        return
    
    # Create NewsAPI client
    try:
        newsapi = NewsApiClient(api_key=settings.NEWS_API_KEY)
        # Test the API key by making a simple request
        sources = newsapi.get_sources()
        logger.info(f"✅ Successfully connected to NewsAPI. Found {len(sources.get('sources', []))} sources")
    except Exception as e:
        logger.error(f"❌ Failed to initialize NewsAPI client: {str(e)}")
        logger.error("Please check your NEWS_API_KEY environment variable")
        return
    
    # Test direct API call first
    logger.info("\n=== TEST 0: Direct NewsAPI Test ===")
    try:
        # Test getting sources
        sources_response = newsapi.get_sources(language='en', country='us')
        logger.info(f"✅ Successfully connected to NewsAPI. Found {len(sources_response['sources'])} sources")
        
        # Test getting articles for crypto-related sources
        top_sources = [s['id'] for s in sources_response['sources'] if 'crypto' in s['name'].lower() or 'coin' in s['name'].lower()]
        logger.info(f"Found {len(top_sources)} crypto-related sources: {', '.join(top_sources[:5])}{'...' if len(top_sources) > 5 else ''}")
        
        # Test getting articles from the first crypto source
        if top_sources:
            test_source = top_sources[0]
            logger.info(f"\nTesting article retrieval for source: {test_source}")
            articles = newsapi.get_everything(
                sources=test_source,
                q='bitcoin OR ethereum OR crypto',
                language='en',
                sort_by='publishedAt',
                page_size=3
            )
            logger.info(f"Found {articles['totalResults']} total articles, showing {len(articles['articles'])}")
            for i, article in enumerate(articles['articles'][:2], 1):
                logger.info(f"  {i}. {article['title']}")
                logger.info(f"     Published: {article['publishedAt']}")
                logger.info(f"     URL: {article['url']}")
        
        # Add a small delay before continuing with the collector tests
        await asyncio.sleep(2)
        
    except Exception as e:
        logger.error(f"❌ Direct NewsAPI test failed: {str(e)}", exc_info=True)
        logger.error("Please check your API key and network connection")
        return
    
    # Initialize collector
    collector = NewsCollector(newsapi_client=newsapi)
    try:
        await collector.initialize()
        logger.info("✅ Successfully initialized NewsCollector")
    except Exception as e:
        logger.error(f"❌ Failed to initialize NewsCollector: {str(e)}")
        return
    
    # Define test parameters
    test_keywords = ['bitcoin', 'ethereum', 'crypto']
    test_sources = ['coindesk', 'cointelegraph', 'crypto-news']
    
    try:
        logger.info("🚀 Starting news collection test...")
        
        # Test 1: Collect from specific sources with detailed logging
        logger.info(f"\n=== TEST 1: Collecting from specific sources ===")
        for source in test_sources:
            try:
                logger.info(f"\n🔍 Attempting to collect from source: {source}")
                
                # Get source info first
                try:
                    source_info = await collector.newsapi.get_sources()
                    source_names = [s['id'] for s in source_info.get('sources', [])]
                    logger.info(f"Available sources: {', '.join(source_names[:10])}{'...' if len(source_names) > 10 else ''}")
                except Exception as e:
                    logger.warning(f"Could not fetch source list: {str(e)}")
                
                # Collect articles
                logger.info(f"Starting collection from {source}...")
                new_articles = await collector.collect_from_source(source)
                
                if new_articles > 0:
                    logger.info(f"✅ Successfully collected {new_articles} new articles from {source}")
                    
                    # Query the database to verify
                    try:
                        async with session_maker() as session:
                            result = await session.execute(
                                select(Article)
                                .join(Source)
                                .where(Source.id == source)
                                .order_by(Article.published_at.desc())
                                .limit(1)
                            )
                            latest_article = result.scalars().first()
                            if latest_article:
                                logger.info(f"Latest article from {source}:")
                                logger.info(f"  Title: {latest_article.title}")
                                logger.info(f"  Published: {latest_article.published_at}")
                                logger.info(f"  URL: {latest_article.url}")
                    except Exception as e:
                        logger.warning(f"Could not verify articles in database: {str(e)}")
                else:
                    logger.warning(f"⚠️ No new articles collected from {source}")
                
                # Small delay between sources to respect rate limits
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"❌ Error collecting from source {source}: {str(e)}", exc_info=True)
                continue
        
        # Test 2: Collect from all available sources (limited)
        logger.info("\n=== TEST 2: Collecting from all available sources (limited to 2) ===")
        try:
            from sqlalchemy import func
            logger.info("Starting collection from all available sources...")
            total_new_articles = await collector.collect_all_sources(max_sources=2)
            
            if total_new_articles > 0:
                logger.info(f"✅ Successfully collected {total_new_articles} new articles from all sources")
                
                # Get a count of articles in the database
                try:
                    async with session_maker() as session:
                        result = await session.execute(select(Article))
                        total_articles = len(result.scalars().all())
                        logger.info(f"Total articles in database: {total_articles}")
                        
                        # Get article counts by source
                        result = await session.execute(
                            select(Source.name, func.count(Article.id))
                            .join(Article)
                            .group_by(Source.name)
                        )
                        logger.info("Articles by source:")
                        for source_name, count in result.all():
                            logger.info(f"  {source_name}: {count} articles")
                            
                except Exception as e:
                    logger.warning(f"Could not query article counts: {str(e)}")
            else:
                logger.warning("⚠️ No new articles collected from any source")
        except Exception as e:
            logger.error(f"❌ Error collecting from all sources: {str(e)}", exc_info=True)
        
        logger.info("News collection test completed successfully!")
        
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(test_news_collection())
