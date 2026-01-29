#!/usr/bin/env python3
"""
Test script to verify action extraction works correctly.

This script tests the action extraction logic without modifying the database.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

from crypto_news_aggregator.core.config import settings

# Import the function directly from the backfill script
import importlib.util
spec = importlib.util.spec_from_file_location(
    "backfill_narrative_actions",
    project_root / "scripts" / "backfill_narrative_actions.py"
)
backfill_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backfill_module)
extract_actions_from_summary = backfill_module.extract_actions_from_summary


def test_action_extraction():
    """Test action extraction with sample summaries."""
    
    # Check for API key
    if not settings.ANTHROPIC_API_KEY:
        print("ERROR: ANTHROPIC_API_KEY not configured in environment")
        return
    
    # Test cases
    test_summaries = [
        {
            "theme": "regulatory_enforcement",
            "summary": "The SEC filed a lawsuit against Binance for alleged securities violations. The regulatory enforcement action targets the exchange's handling of customer funds and unregistered securities offerings."
        },
        {
            "theme": "defi_protocol",
            "summary": "Uniswap announced a major partnership with Coinbase to integrate their decentralized exchange protocol. The collaboration aims to bring DeFi services to millions of new users."
        },
        {
            "theme": "network_upgrade",
            "summary": "Ethereum successfully completed the Dencun upgrade, introducing proto-danksharding to reduce Layer 2 transaction costs. The network upgrade marks a significant milestone in Ethereum's scaling roadmap."
        },
        {
            "theme": "market_movement",
            "summary": "Bitcoin experienced a significant price rally, surging past $50,000 amid institutional buying pressure. The bullish momentum was driven by spot ETF inflows and positive macroeconomic data."
        }
    ]
    
    print("Testing action extraction...")
    print("=" * 80)
    
    for idx, test_case in enumerate(test_summaries, 1):
        theme = test_case["theme"]
        summary = test_case["summary"]
        
        print(f"\nTest {idx}: {theme}")
        print(f"Summary: {summary[:100]}...")
        
        # Extract actions
        actions = extract_actions_from_summary(summary, settings.ANTHROPIC_API_KEY)
        
        if actions:
            print(f"✓ Extracted actions: {actions}")
        else:
            print(f"✗ Failed to extract actions")
        
        print("-" * 80)
    
    print("\nTest complete!")


if __name__ == "__main__":
    test_action_extraction()
