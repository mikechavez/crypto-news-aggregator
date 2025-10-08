"""Test the signals API endpoint to verify narrative linking."""
import asyncio
import json
from crypto_news_aggregator.api.v1.endpoints.signals import get_trending_signals

async def test_api():
    print("Testing /api/v1/signals/trending endpoint...\n")
    
    # Call the endpoint function directly
    response = await get_trending_signals(limit=3, min_score=0.0, entity_type=None)
    
    print(f"Response has {response['count']} signals\n")
    
    for i, signal in enumerate(response['signals'][:3], 1):
        print(f"Signal {i}: {signal['entity']}")
        print(f"  Score: {signal['signal_score']}")
        print(f"  Is Emerging: {signal.get('is_emerging', 'MISSING')}")
        print(f"  Narratives: {len(signal.get('narratives', []))}")
        
        if signal.get('narratives'):
            for narrative in signal['narratives']:
                print(f"    - {narrative['title']} ({narrative['theme']})")
        elif signal.get('is_emerging'):
            print(f"    🆕 Emerging signal!")
        print()

asyncio.run(test_api())
