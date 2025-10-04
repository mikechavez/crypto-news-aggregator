"""
Test RSS fetch with progress output and timeout.
"""
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

from crypto_news_aggregator.background.rss_fetcher import fetch_and_process_rss_feeds

async def main():
    print("Starting RSS fetch...")
    print("This will:")
    print("  1. Fetch articles from RSS feeds")
    print("  2. Process through LLM for entity extraction")
    print("  3. Store entity mentions in MongoDB")
    print("  4. Calculate sentiment")
    print("\nThis may take 1-2 minutes...\n")
    
    try:
        await asyncio.wait_for(fetch_and_process_rss_feeds(), timeout=300)  # 5 min timeout
        print("\n✅ RSS fetch completed successfully!")
    except asyncio.TimeoutError:
        print("\n⚠️  RSS fetch timed out after 5 minutes")
    except Exception as e:
        print(f"\n❌ Error during RSS fetch: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(main())
