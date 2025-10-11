#!/usr/bin/env python3
"""
Test script for theme-based narrative detection.

This script tests the new narrative detection system that uses
theme-based clustering instead of entity co-occurrence.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from crypto_news_aggregator.services.narrative_service import detect_narratives
from crypto_news_aggregator.db.operations.narratives import get_active_narratives
from crypto_news_aggregator.db.mongodb import mongo_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_narrative_detection():
    """Test the theme-based narrative detection system."""
    
    try:
        # Initialize MongoDB connection
        await mongo_manager.initialize()
        logger.info("Connected to MongoDB")
        
        # Run narrative detection
        logger.info("=" * 80)
        logger.info("Running theme-based narrative detection...")
        logger.info("=" * 80)
        
        narratives = await detect_narratives(hours=48, min_articles=2)
        
        logger.info("=" * 80)
        logger.info(f"RESULTS: Generated {len(narratives)} narratives")
        logger.info("=" * 80)
        
        # Display each narrative
        for i, narrative in enumerate(narratives, 1):
            logger.info(f"\n--- Narrative {i} ---")
            logger.info(f"Theme: {narrative['theme']}")
            logger.info(f"Title: {narrative['title']}")
            logger.info(f"Summary: {narrative['summary']}")
            logger.info(f"Entities: {', '.join(narrative['entities'][:5])}...")
            logger.info(f"Article Count: {narrative['article_count']}")
            logger.info(f"Mention Velocity: {narrative['mention_velocity']} articles/day")
            logger.info(f"Lifecycle: {narrative['lifecycle']}")
            logger.info(f"First Seen: {narrative['first_seen']}")
            logger.info(f"Last Updated: {narrative['last_updated']}")
        
        # Verify narratives were saved to database
        logger.info("\n" + "=" * 80)
        logger.info("Verifying narratives in database...")
        logger.info("=" * 80)
        
        db_narratives = await get_active_narratives(limit=20)
        logger.info(f"Found {len(db_narratives)} narratives in database")
        
        # Show lifecycle distribution
        lifecycle_counts = {}
        for narrative in db_narratives:
            lifecycle = narrative.get("lifecycle", "unknown")
            lifecycle_counts[lifecycle] = lifecycle_counts.get(lifecycle, 0) + 1
        
        logger.info("\nLifecycle Distribution:")
        for lifecycle, count in sorted(lifecycle_counts.items()):
            logger.info(f"  {lifecycle}: {count}")
        
        # Show theme distribution
        logger.info("\nTheme Distribution:")
        for narrative in db_narratives:
            lifecycle = narrative.get('lifecycle', 'unknown')
            logger.info(f"  {narrative['theme']}: {narrative['article_count']} articles ({lifecycle})")
        
        logger.info("\n" + "=" * 80)
        logger.info("TEST COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.exception(f"Error during narrative detection test: {e}")
        raise
    finally:
        # Close MongoDB connection
        await mongo_manager.close()
        logger.info("Closed MongoDB connection")


if __name__ == "__main__":
    asyncio.run(test_narrative_detection())
