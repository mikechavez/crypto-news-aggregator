#!/usr/bin/env python3
"""
Quick test of the signals endpoint to verify it works.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from src.crypto_news_aggregator.main import app
from src.crypto_news_aggregator.db.mongodb import initialize_mongodb
from src.crypto_news_aggregator.core.config import get_settings


async def setup():
    """Initialize MongoDB for testing."""
    await initialize_mongodb()


def test_signals_endpoint():
    """Test the signals endpoint."""
    settings = get_settings()
    
    # Run async setup
    asyncio.run(setup())
    
    # Create test client
    client = TestClient(app)
    
    # Test the endpoint
    print("🧪 Testing GET /api/v1/signals/trending")
    response = client.get(
        f"{settings.API_V1_STR}/signals/trending",
        headers={"X-API-Key": settings.API_KEY}
    )
    
    print(f"   Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Success!")
        print(f"   Count: {data.get('count', 0)}")
        print(f"   Filters: {data.get('filters', {})}")
        
        if data.get('signals'):
            print(f"\n   Top 3 Trending:")
            for i, signal in enumerate(data['signals'][:3], 1):
                print(f"   {i}. {signal['entity']} ({signal['entity_type']})")
                print(f"      Score: {signal['signal_score']}, Velocity: {signal['velocity']}")
        else:
            print("   No signals found (database may be empty)")
    else:
        print(f"   ❌ Failed: {response.text}")
    
    # Test with filters
    print("\n🧪 Testing with filters (entity_type=ticker, limit=5)")
    response = client.get(
        f"{settings.API_V1_STR}/signals/trending?entity_type=ticker&limit=5",
        headers={"X-API-Key": settings.API_KEY}
    )
    
    print(f"   Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Success! Found {data.get('count', 0)} ticker signals")
    else:
        print(f"   ❌ Failed: {response.text}")
    
    # Test without API key (should fail)
    print("\n🧪 Testing without API key (should fail)")
    response = client.get(f"{settings.API_V1_STR}/signals/trending")
    print(f"   Status Code: {response.status_code}")
    if response.status_code == 403:
        print("   ✅ Correctly rejected (403 Forbidden)")
    else:
        print(f"   ❌ Unexpected response: {response.status_code}")


if __name__ == "__main__":
    test_signals_endpoint()
    print("\n✅ Endpoint testing complete!")
