"""Test script for NewsAPI integration."""

import os
import asyncio
import logging
from dotenv import load_dotenv
from newsapi import NewsApiClient
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()


class NewsAPITester:
    """Test class for NewsAPI integration."""

    def __init__(self, api_key: str):
        """Initialize with NewsAPI client."""
        self.newsapi = NewsApiClient(api_key=api_key)
        self.retry_delay = 5  # seconds

    async def test_connection(self):
        """Test the connection to NewsAPI."""
        try:
            # Get the sources endpoint to test the connection
            sources = self.newsapi.get_sources(language="en")
            if sources["status"] == "ok":
                logger.info("✅ Successfully connected to NewsAPI")
                return True
            else:
                logger.error(f"❌ Failed to connect to NewsAPI: {sources}")
                return False
        except Exception as e:
            logger.error(f"❌ Error connecting to NewsAPI: {str(e)}")
            return False

    async def fetch_crypto_news(self, query="cryptocurrency", page_size=5):
        """Fetch crypto news with error handling and rate limiting."""
        try:
            # Get everything published in the last 24 hours
            from_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

            logger.info(f"🔍 Fetching {page_size} articles about '{query}'...")

            # Make the API request
            response = self.newsapi.get_everything(
                q=query,
                language="en",
                sort_by="publishedAt",
                page_size=min(page_size, 100),  # Max 100 articles per request
                from_param=from_date,
            )

            if response["status"] == "ok":
                articles = response.get("articles", [])
                logger.info(f"✅ Successfully fetched {len(articles)} articles")

                # Log article details
                for i, article in enumerate(articles, 1):
                    logger.info(f"\n📰 Article {i}:")
                    logger.info(f"   Title: {article.get('title', 'No title')}")
                    logger.info(
                        f"   Source: {article.get('source', {}).get('name', 'Unknown')}"
                    )
                    logger.info(
                        f"   Published: {article.get('publishedAt', 'Unknown')}"
                    )
                    logger.info(f"   URL: {article.get('url', 'No URL')}")

                return articles
            else:
                logger.error(f"❌ Failed to fetch articles: {response}")
                return []

        except Exception as e:
            logger.error(f"❌ Error fetching articles: {str(e)}")
            return []


async def main():
    """Run the test script."""
    # Get API key from environment variable
    api_key = os.getenv("NEWS_API_KEY")

    if not api_key:
        logger.error("❌ NEWS_API_KEY not found in environment variables")
        logger.info("Please set NEWS_API_KEY in your .env file")
        return

    tester = NewsAPITester(api_key)

    # Test connection
    if not await tester.test_connection():
        return

    # Test fetching crypto news
    await tester.fetch_crypto_news(
        query="cryptocurrency OR bitcoin OR ethereum", page_size=3
    )


if __name__ == "__main__":
    asyncio.run(main())
