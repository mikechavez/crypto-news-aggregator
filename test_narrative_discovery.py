"""
Test script for narrative discovery system.

Tests the two-layer approach:
- Layer 1: Discover narrative elements
- Layer 2: Map to themes
"""

import asyncio
import sys
from src.crypto_news_aggregator.services.narrative_themes import (
    discover_narrative_from_article,
    map_narrative_to_themes
)


async def test_narrative_discovery():
    """Test narrative discovery on sample articles."""
    
    # Test case 1: Regulatory narrative
    print("=" * 80)
    print("TEST 1: Regulatory Narrative")
    print("=" * 80)
    
    article_id = "test_1"
    title = "SEC Charges Binance and Coinbase with Securities Violations"
    summary = """The Securities and Exchange Commission filed charges against 
    major cryptocurrency exchanges Binance and Coinbase, alleging they operated 
    as unregistered securities exchanges. The enforcement actions mark a significant 
    escalation in regulatory pressure on the crypto industry."""
    
    narrative_data = await discover_narrative_from_article(article_id, title, summary)
    
    if narrative_data:
        print(f"\n✓ Layer 1 Discovery:")
        print(f"  Actors: {narrative_data.get('actors', [])}")
        print(f"  Actions: {narrative_data.get('actions', [])}")
        print(f"  Tensions: {narrative_data.get('tensions', [])}")
        print(f"  Implications: {narrative_data.get('implications', '')}")
        print(f"  Narrative Summary: {narrative_data.get('narrative_summary', '')}")
        
        # Test Layer 2 mapping
        mapping = await map_narrative_to_themes(narrative_data.get('narrative_summary', ''), article_id)
        print(f"\n✓ Layer 2 Mapping:")
        print(f"  Themes: {mapping.get('themes', [])}")
        print(f"  Suggested New Theme: {mapping.get('suggested_new_theme', 'None')}")
    else:
        print("✗ Failed to discover narrative")
    
    # Test case 2: L2 scaling narrative
    print("\n" + "=" * 80)
    print("TEST 2: L2 Scaling Narrative")
    print("=" * 80)
    
    article_id = "test_2"
    title = "Arbitrum Surpasses Optimism in Daily Active Users"
    summary = """Ethereum Layer 2 solution Arbitrum has overtaken Optimism in 
    daily active users, reaching 500,000 users. The competition between L2 
    solutions intensifies as Base, Coinbase's L2, also gains traction with 
    major DeFi protocols migrating to reduce gas costs."""
    
    narrative_data = await discover_narrative_from_article(article_id, title, summary)
    
    if narrative_data:
        print(f"\n✓ Layer 1 Discovery:")
        print(f"  Actors: {narrative_data.get('actors', [])}")
        print(f"  Actions: {narrative_data.get('actions', [])}")
        print(f"  Tensions: {narrative_data.get('tensions', [])}")
        print(f"  Implications: {narrative_data.get('implications', '')}")
        print(f"  Narrative Summary: {narrative_data.get('narrative_summary', '')}")
        
        # Test Layer 2 mapping
        mapping = await map_narrative_to_themes(narrative_data.get('narrative_summary', ''), article_id)
        print(f"\n✓ Layer 2 Mapping:")
        print(f"  Themes: {mapping.get('themes', [])}")
        print(f"  Suggested New Theme: {mapping.get('suggested_new_theme', 'None')}")
    else:
        print("✗ Failed to discover narrative")
    
    # Test case 3: Emerging narrative (doesn't fit existing themes)
    print("\n" + "=" * 80)
    print("TEST 3: Emerging Narrative (New Category)")
    print("=" * 80)
    
    article_id = "test_3"
    title = "AI Agents Begin Trading on Decentralized Exchanges"
    summary = """Autonomous AI agents are now executing trades on decentralized 
    exchanges, marking a new frontier in crypto automation. Projects like Fetch.ai 
    and SingularityNET are enabling AI-driven trading strategies that adapt to 
    market conditions in real-time."""
    
    narrative_data = await discover_narrative_from_article(article_id, title, summary)
    
    if narrative_data:
        print(f"\n✓ Layer 1 Discovery:")
        print(f"  Actors: {narrative_data.get('actors', [])}")
        print(f"  Actions: {narrative_data.get('actions', [])}")
        print(f"  Tensions: {narrative_data.get('tensions', [])}")
        print(f"  Implications: {narrative_data.get('implications', '')}")
        print(f"  Narrative Summary: {narrative_data.get('narrative_summary', '')}")
        
        # Test Layer 2 mapping
        mapping = await map_narrative_to_themes(narrative_data.get('narrative_summary', ''), article_id)
        print(f"\n✓ Layer 2 Mapping:")
        print(f"  Themes: {mapping.get('themes', [])}")
        print(f"  Suggested New Theme: {mapping.get('suggested_new_theme', 'None')}")
    else:
        print("✗ Failed to discover narrative")
    
    print("\n" + "=" * 80)
    print("TESTS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    try:
        asyncio.run(test_narrative_discovery())
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
