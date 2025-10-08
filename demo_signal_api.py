"""Demo the signal-to-narrative linking API response."""
import asyncio
import json
from crypto_news_aggregator.api.v1.endpoints.signals import get_trending_signals

async def demo():
    print("=" * 70)
    print("SIGNAL-TO-NARRATIVE LINKING - API DEMO")
    print("=" * 70)
    print()
    
    response = await get_trending_signals(limit=50, min_score=0.0, entity_type=None)
    
    # Find signals with narratives
    signals_with_narratives = [s for s in response['signals'] if s.get('narratives')]
    signals_emerging = [s for s in response['signals'] if s.get('is_emerging')]
    
    print(f"📊 Total signals: {response['count']}")
    print(f"📖 Signals with narratives: {len(signals_with_narratives)}")
    print(f"🆕 Emerging signals: {len(signals_emerging)}")
    print()
    
    # Show examples of signals WITH narratives
    print("=" * 70)
    print("SIGNALS WITH NARRATIVES (showing first 3)")
    print("=" * 70)
    
    for i, signal in enumerate(signals_with_narratives[:3], 1):
        print(f"\n{i}. {signal['entity']} (Score: {signal['signal_score']})")
        print(f"   Is Emerging: {signal['is_emerging']}")
        print(f"   Part of {len(signal['narratives'])} narrative(s):")
        
        for narrative in signal['narratives']:
            print(f"      • [{narrative['theme']}] {narrative['title']}")
            print(f"        Lifecycle: {narrative['lifecycle']}")
    
    # Show example of emerging signal
    print()
    print("=" * 70)
    print("EMERGING SIGNALS (not in any narrative)")
    print("=" * 70)
    
    if signals_emerging:
        for i, signal in enumerate(signals_emerging[:2], 1):
            print(f"\n{i}. {signal['entity']} (Score: {signal['signal_score']})")
            print(f"   🆕 Emerging: {signal['is_emerging']}")
            print(f"   Narratives: {signal['narratives']}")
    else:
        print("\nNo emerging signals found (all signals are part of narratives)")
    
    # Show raw JSON for one signal
    print()
    print("=" * 70)
    print("RAW API RESPONSE EXAMPLE")
    print("=" * 70)
    
    if signals_with_narratives:
        example = signals_with_narratives[0]
        print(json.dumps({
            "entity": example['entity'],
            "signal_score": example['signal_score'],
            "is_emerging": example['is_emerging'],
            "narratives": example['narratives']
        }, indent=2))

asyncio.run(demo())
