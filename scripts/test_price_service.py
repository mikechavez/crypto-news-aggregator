"""
Test script for the price service.
"""

import asyncio
import os
from dotenv import load_dotenv
import sys
import os

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from crypto_news_aggregator.services.price_service import price_service


async def test_bitcoin_price():
    """Test fetching the current Bitcoin price."""
    print("Testing Bitcoin price service...")
    try:
        # Get the current Bitcoin price
        price_data = await price_service.get_bitcoin_price()
        if price_data is None:
            print("❌ Failed to fetch Bitcoin price: No data returned")
            return

        print(f"✅ Successfully fetched Bitcoin price:")
        print(f"  Price: ${price_data.get('price', 'N/A'):,.2f}")
        print(f"  24h Change: {price_data.get('change_24h', 0):.2f}%")
        print(f"  Timestamp: {price_data.get('timestamp')}")

    except Exception as e:
        print(f"❌ Error fetching Bitcoin price: {str(e)}")
    finally:
        # Clean up the session
        await price_service.close()


if __name__ == "__main__":
    # Load environment variables
    load_dotenv()

    # Run the test
    asyncio.run(test_bitcoin_price())
