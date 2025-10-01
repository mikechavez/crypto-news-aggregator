#!/usr/bin/env python3
"""
Trigger entity extraction enrichment manually.
"""
import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from crypto_news_aggregator.background.rss_fetcher import (
    process_new_articles_from_mongodb,
)


async def main():
    print("🚀 Starting entity extraction enrichment...")
    try:
        processed = await process_new_articles_from_mongodb()
        print(f"✅ Successfully processed {processed} articles")
        return processed
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return 0


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result > 0 else 1)
