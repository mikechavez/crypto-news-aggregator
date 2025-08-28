import asyncio
import logging
import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.crypto_news_aggregator.tasks.price_monitor import PriceMonitor

logging.basicConfig(level=logging.INFO)

async def main():
    """Runs the price monitor for a short duration for testing."""
    print("Starting price monitor for test...")
    monitor = PriceMonitor()
    await monitor.start()
    
    try:
        # Run for a short period to see if it starts correctly
        await asyncio.sleep(15)
    finally:
        print("Stopping price monitor...")
        await monitor.stop()

    print("Price monitor test finished.")

if __name__ == "__main__":
    asyncio.run(main())
