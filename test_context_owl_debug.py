#!/usr/bin/env python3
"""
Context Owl Market Crash Fix Validation - Debug Version

This script tests the FIXED Context Owl implementation with detailed debugging.
"""

import json
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from typing import Dict, Any, List
from datetime import datetime, timezone

from crypto_news_aggregator.main import app
from crypto_news_aggregator.core.auth import get_api_keys


def create_crash_articles() -> List[Dict[str, Any]]:
    """Create crash-specific articles for testing."""
    return [
        {
            "title": "Bitcoin ETF Outflows Reach $1.2B as Investors Flee Risk Assets During Market Crash",
            "source": "CoinDesk",
            "sentiment_score": -0.4,
            "sentiment_label": "negative",
            "keywords": ["BTC", "bitcoin", "ETF", "outflows", "crash", "market"],
            "published_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "title": "Whale Liquidations Trigger Massive Cascade Selling in Crypto Markets",
            "source": "The Block",
            "sentiment_score": -0.6,
            "sentiment_label": "negative",
            "keywords": [
                "BTC",
                "bitcoin",
                "whale",
                "liquidations",
                "cascade",
                "selling",
                "crypto",
            ],
            "published_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "title": "Federal Reserve Signals Continued Hawkish Policy Amid Crypto Market Turmoil",
            "source": "Reuters",
            "sentiment_score": -0.3,
            "sentiment_label": "negative",
            "keywords": [
                "BTC",
                "bitcoin",
                "federal reserve",
                "policy",
                "hawkish",
                "crypto",
                "turmoil",
            ],
            "published_at": datetime.now(timezone.utc).isoformat(),
        },
    ]


def test_context_owl_fix_debug():
    """Test the FIXED Context Owl implementation with debugging."""

    print("🔥 CONTEXT OWL CRASH ANALYSIS FIX VALIDATION - DEBUG 🔥")
    print("=" * 60)

    client = TestClient(app)
    valid_api_keys = get_api_keys()

    if not valid_api_keys:
        print("❌ ERROR: No API keys configured for testing")
        return False

    # Test a single query to debug
    query = "Why is crypto crashing?"

    print(f"🧪 Testing query: {query}")

    # Test with real implementation and detailed mocking
    with patch(
        "crypto_news_aggregator.services.price_service.article_service"
    ) as mock_article_service:
        # Mock the article service to return crash articles
        mock_article_service.get_top_articles_for_symbols.return_value = (
            create_crash_articles()
        )
        mock_article_service.get_average_sentiment_for_symbols.return_value = {
            "BTC": -0.45
        }

        # Mock market data
        with patch(
            "crypto_news_aggregator.services.price_service.CoinGeckoPriceService.get_global_market_data"
        ) as mock_get_data:
            mock_get_data.return_value = {
                "bitcoin": {
                    "current_price": 60250,  # Realistic Bitcoin price
                    "price_change_percentage_1h_in_currency": -1.2,
                    "price_change_percentage_24h_in_currency": -2.7,
                    "price_change_percentage_7d_in_currency": -8.5,
                    "market_cap_rank": 1,
                    "total_volume": 25000000000,
                    "market_cap": 1180000000000,  # ~$1.18T market cap
                    "name": "Bitcoin",
                },
                "ethereum": {
                    "current_price": 2300,
                    "price_change_percentage_24h_in_currency": -6.5,
                    "name": "Ethereum",
                },
            }

            # Mock the _fetch_related_news method to ensure it returns our crash articles
            with patch(
                "crypto_news_aggregator.services.price_service.CoinGeckoPriceService._fetch_related_news"
            ) as mock_fetch_news:
                mock_fetch_news.return_value = create_crash_articles()

                request_data = {
                    "model": "crypto-insight-agent",
                    "messages": [{"role": "user", "content": query}],
                    "stream": False,
                }

                response = client.post(
                    "/v1/chat/completions",
                    json=request_data,
                    headers={"X-API-Key": valid_api_keys[0]},
                )

                if response.status_code != 200:
                    print(f"❌ FAILED: HTTP {response.status_code}")
                    print(f"   Error: {response.json()}")
                    return False

                response_data = response.json()
                content = response_data["choices"][0]["message"]["content"]
                print(f"✅ Response received ({len(content)} chars)")
                print(f"   Content: {content}")

                # Check if we got the sophisticated analysis
                if "No high-signal news to analyze yet" in content:
                    print(
                        "❌ ISSUE: Still getting fallback message instead of sophisticated analysis"
                    )
                    print(
                        "   This means _fetch_related_news is returning empty or _analyze_developing_narratives is not working"
                    )
                    return False
                elif "ETF outflows creating selling pressure" in content:
                    print(
                        "✅ SUCCESS: Got sophisticated crash analysis with key drivers!"
                    )
                    return True
                else:
                    print(
                        "⚠️  PARTIAL: Got some analysis but missing crash-specific themes"
                    )
                    return False


if __name__ == "__main__":
    success = test_context_owl_fix_debug()
    if success:
        print("🎉 SUCCESS: Context Owl fix is working!")
    else:
        print("❌ FAILED: Context Owl still needs work")
    exit(0 if success else 1)
