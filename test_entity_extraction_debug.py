#!/usr/bin/env python3
"""
Test script to debug entity extraction with Anthropic API.
Tests the model availability and fallback logic.
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from crypto_news_aggregator.core.config import settings
from crypto_news_aggregator.llm.factory import get_llm_provider

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_api_key_configuration():
    """Test that API key is properly configured."""
    logger.info("=" * 60)
    logger.info("Testing API Key Configuration")
    logger.info("=" * 60)
    
    if not settings.ANTHROPIC_API_KEY:
        logger.error("❌ ANTHROPIC_API_KEY is not set!")
        return False
    
    # Show masked API key
    api_key = settings.ANTHROPIC_API_KEY
    masked_key = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "***"
    logger.info(f"✓ ANTHROPIC_API_KEY is set: {masked_key}")
    logger.info(f"✓ Entity Model: {settings.ANTHROPIC_ENTITY_MODEL}")
    logger.info(f"✓ Fallback Model: {settings.ANTHROPIC_ENTITY_FALLBACK_MODEL}")
    logger.info(f"✓ Batch Size: {settings.ENTITY_EXTRACTION_BATCH_SIZE}")
    return True


def test_entity_extraction():
    """Test entity extraction with sample articles."""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Entity Extraction")
    logger.info("=" * 60)
    
    # Get LLM provider
    llm_client = get_llm_provider()
    logger.info(f"✓ LLM Provider initialized: {llm_client.__class__.__name__}")
    
    # Sample articles for testing
    test_articles = [
        {
            "id": "test_1",
            "title": "Bitcoin Surges Past $50,000 as Institutional Interest Grows",
            "text": "Bitcoin (BTC) has broken through the $50,000 barrier as major institutions continue to accumulate the cryptocurrency. The rally comes amid growing regulatory clarity and increased adoption."
        },
        {
            "id": "test_2",
            "title": "Ethereum Upgrade Successfully Deployed",
            "text": "The Ethereum network has successfully completed its latest upgrade, improving transaction speeds and reducing gas fees. ETH price responded positively to the news."
        }
    ]
    
    logger.info(f"Testing with {len(test_articles)} sample articles...")
    
    try:
        result = llm_client.extract_entities_batch(test_articles)
        
        if not result or not result.get("results"):
            logger.error("❌ Entity extraction returned no results")
            logger.error(f"Result: {result}")
            return False
        
        # Log results
        logger.info(f"✓ Successfully extracted entities from {len(result['results'])} articles")
        
        # Log usage stats
        usage = result.get("usage", {})
        if usage:
            logger.info(f"\nUsage Statistics:")
            logger.info(f"  Model: {usage.get('model', 'unknown')}")
            logger.info(f"  Input tokens: {usage.get('input_tokens', 0)}")
            logger.info(f"  Output tokens: {usage.get('output_tokens', 0)}")
            logger.info(f"  Total cost: ${usage.get('total_cost', 0):.6f}")
        
        # Log extracted entities
        logger.info(f"\nExtracted Entities:")
        for article_result in result["results"]:
            article_id = article_result.get("article_id", "unknown")
            entities = article_result.get("entities", [])
            sentiment = article_result.get("sentiment", "unknown")
            
            logger.info(f"\n  Article: {article_id}")
            logger.info(f"  Sentiment: {sentiment}")
            logger.info(f"  Entities ({len(entities)}):")
            for entity in entities:
                logger.info(f"    - {entity.get('type')}: {entity.get('value')} (confidence: {entity.get('confidence', 1.0):.2f})")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Entity extraction failed with exception: {e}")
        logger.exception("Full traceback:")
        return False


def main():
    """Run all tests."""
    logger.info("Starting Entity Extraction Debug Tests\n")
    
    # Test 1: API Key Configuration
    if not test_api_key_configuration():
        logger.error("\n❌ API key configuration test failed. Please check your .env file.")
        return 1
    
    # Test 2: Entity Extraction
    if not test_entity_extraction():
        logger.error("\n❌ Entity extraction test failed. Check logs above for details.")
        return 1
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ All tests passed!")
    logger.info("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
