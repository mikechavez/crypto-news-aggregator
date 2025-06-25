#!/usr/bin/env python3
"""
Test script for the NewsCollector class.

This script demonstrates how to use the NewsCollector to fetch and store news articles.
"""
import asyncio
import logging
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv(project_root / '.env')

async def test_news_collector():
    """Test the NewsCollector with a specific source."""
    from crypto_news_aggregator.core.news_collector import NewsCollector
    
    try:
        # Initialize the collector
        collector = NewsCollector()
        
        # Initialize the collector (async)
        await collector.initialize()
        
        # Test with a specific source (e.g., 'bbc-news')
        source_id = 'bbc-news'  # You can change this to any valid NewsAPI source ID
        
        # Test collecting from a specific source
        logger.info(f"Testing collection from source: {source_id}")
        count = await collector.collect_from_source(source_id)
        logger.info(f"Collected {count} new articles from {source_id}")
        
        # Test collecting from all sources (be careful with rate limits)
        # logger.info("Testing collection from all sources...")
        # total = await collector.collect_all_sources()
        # logger.info(f"Collected {total} new articles in total")
        
        return count
        
    except Exception as e:
        logger.error(f"Error in test_news_collector: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    # Create a new event loop for the test
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(test_news_collector())
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
    finally:
        # Clean up the event loop
        loop.close()
