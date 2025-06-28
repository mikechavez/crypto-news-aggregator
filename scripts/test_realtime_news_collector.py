#!/usr/bin/env python3
"""
Test script for the RealtimeNewsCollector with the self-hosted realtime-newsapi.
"""
import asyncio
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.crypto_news_aggregator.core.realtime_news_collector import RealtimeNewsCollector
from src.crypto_news_aggregator.core.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('realtime_news_test.log')
    ]
)
logger = logging.getLogger(__name__)

async def test_realtime_news_collector():
    """Test the RealtimeNewsCollector with the realtime-newsapi service."""
    settings = get_settings()
    logger.info("Starting RealtimeNewsCollector test...")
    
    try:
        # Initialize the collector with the configured URL
        collector = RealtimeNewsCollector(settings.REALTIME_NEWSAPI_URL)
        await collector.initialize()
        
        # Test 1: Get all sources
        logger.info("Testing source listing...")
        async with collector.client as client:
            sources = await client.get_sources()
            logger.info(f"Found {len(sources['sources'])} sources")
            if sources['sources']:
                logger.info(f"First source: {sources['sources'][0]}")
        
        # Test 2: Collect from a specific source (use the first available source)
        if sources and sources['sources']:
            source_id = sources['sources'][0]['id']
            logger.info(f"Testing article collection from source: {source_id}")
            
            new_articles = await collector.collect_from_source(source_id)
            logger.info(f"Collected {new_articles} new articles from {source_id}")
            
            # Test 3: Try to collect from all sources (limit to 2 for testing)
            logger.info("Testing collection from all sources (limited to 2 sources)...")
            total_new = await collector.collect_all_sources(max_sources=2)
            logger.info(f"Total new articles collected: {total_new}")
        else:
            logger.warning("No sources available for testing")
            
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        return False
    
    return True

if __name__ == "__main__":
    logger.info("=== Starting Realtime News Collector Test ===")
    
    try:
        success = asyncio.run(test_realtime_news_collector())
        if success:
            logger.info("=== Test completed successfully ===")
        else:
            logger.error("=== Test failed ===")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        sys.exit(1)
