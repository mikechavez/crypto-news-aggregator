import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.crypto_news_aggregator.services.price_service import price_service

async def main():
    """
    Main function to test the market analysis commentary generation.
    """
    print("--- Running in PRODUCTION mode (using live CoinGecko API) ---")
    # Re-initialize the service to ensure the latest settings from the .env file are loaded.
    price_service.reinitialize()
    
    print("\n--- Generating Market Analysis for Bitcoin ---")
    
    commentary_btc = await price_service.generate_market_analysis_commentary('bitcoin')
    print(commentary_btc)
    
    print("\n--- Generating Market Analysis for Ethereum ---")
    commentary_eth = await price_service.generate_market_analysis_commentary('ethereum')
    print(commentary_eth)

    # Important: Close the session when done
    await price_service.close()

if __name__ == "__main__":
    # In some environments, you might need to configure the python path
    # to recognize the 'src' directory. Poetry handles this automatically.
    asyncio.run(main())
