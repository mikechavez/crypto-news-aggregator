"""
Test the signal calculation fix.
"""
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

from crypto_news_aggregator.services.signal_service import (
    calculate_velocity,
    calculate_source_diversity,
    calculate_sentiment_metrics,
    calculate_signal_score
)

async def main():
    test_entity = "Bitcoin"
    
    print(f"Testing signal calculation for: {test_entity}\n")
    
    # Test individual components
    print("1. Testing velocity calculation...")
    velocity = await calculate_velocity(test_entity)
    print(f"   Velocity: {velocity}")
    
    print("\n2. Testing source diversity...")
    diversity = await calculate_source_diversity(test_entity)
    print(f"   Source count: {diversity}")
    
    print("\n3. Testing sentiment metrics...")
    sentiment = await calculate_sentiment_metrics(test_entity)
    print(f"   Sentiment: {sentiment}")
    
    print("\n4. Testing overall signal score...")
    signal = await calculate_signal_score(test_entity)
    print(f"   Signal score: {signal}")

asyncio.run(main())
