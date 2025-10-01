#!/usr/bin/env python3
"""
Context Owl Market Crash Fix Validation

This script tests the FIXED Context Owl implementation during a market crash scenario
to validate that it now provides comprehensive crash analysis.
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


def test_context_owl_fix():
    """Test the FIXED Context Owl implementation."""

    print("🔥 CONTEXT OWL CRASH ANALYSIS FIX VALIDATION 🔥")
    print("=" * 60)
    print("Testing FIXED implementation with crash-specific themes")
    print("=" * 60)

    client = TestClient(app)
    valid_api_keys = get_api_keys()

    if not valid_api_keys:
        print("❌ ERROR: No API keys configured for testing")
        return False

    # Test queries that should trigger crash analysis
    crash_queries = [
        "Why is crypto crashing?",
        "What are the main drivers of this market dump?",
        "How are ETF outflows affecting Bitcoin?",
    ]

    all_tests_passed = True

    for i, query in enumerate(crash_queries, 1):
        print(f"\n🧪 TEST {i}: {query}")
        print("-" * 40)

        # Test with real implementation (no mocking of main function)
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
                        "current_price": 43000,
                        "price_change_percentage_1h_in_currency": -1.2,
                        "price_change_percentage_24h_in_currency": -2.7,
                        "price_change_percentage_7d_in_currency": -8.5,
                        "market_cap_rank": 1,
                        "total_volume": 25000000000,
                        "market_cap": 840000000000,
                        "name": "Bitcoin",
                    },
                    "ethereum": {
                        "current_price": 2300,
                        "price_change_percentage_24h_in_currency": -6.5,
                        "name": "Ethereum",
                    },
                }

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
                    all_tests_passed = False
                    continue

                response_data = response.json()
                content = response_data["choices"][0]["message"]["content"]
                print(f"✅ Response received ({len(content)} chars)")
                print(f"   Content: {content}")

                # Check for crash-specific analysis
                success, issues = validate_crash_analysis(content, query)
                if success:
                    print("✅ PASS: Comprehensive crash analysis provided")
                else:
                    print(f"❌ FAIL: {issues}")
                    all_tests_passed = False

    # Summary
    print("\n" + "=" * 60)
    if all_tests_passed:
        print("🎉 ALL TESTS PASSED: Context Owl FIX is working!")
        print("✅ Responding to general market queries")
        print("✅ Using sophisticated narrative analysis")
        print("✅ Providing comprehensive crash context")
    else:
        print("⚠️  SOME TESTS FAILED: Context Owl needs more work")
        print("❌ Still missing some crash analysis features")

    print("=" * 60)
    return all_tests_passed


def validate_crash_analysis(content: str, query: str) -> tuple[bool, str]:
    """Validate that the response provides crash analysis."""

    content_lower = content.lower()

    # Check for key crash drivers
    key_drivers = [
        "etf",
        "outflows",
        "whale",
        "liquidations",
        "fed",
        "policy",
        "federal",
    ]
    driver_mentions = sum(1 for driver in key_drivers if driver in content_lower)

    # Check for actionable context
    context_indicators = [
        "sentiment",
        "narratives",
        "themes",
        "analysis",
        "context",
        "outlook",
    ]
    context_mentions = sum(
        1 for indicator in context_indicators if indicator in content_lower
    )

    # Check for crash-specific content
    crash_indicators = [
        "crash",
        "market",
        "volatility",
        "momentum",
        "bearish",
        "selling",
    ]
    crash_mentions = sum(
        1 for indicator in crash_indicators if indicator in content_lower
    )

    # Validate requirements
    issues = []

    if driver_mentions < 1:
        issues.append(f"Only {driver_mentions}/7 key drivers mentioned")

    if context_mentions < 2:
        issues.append(f"Only {context_mentions}/6 context indicators provided")

    if crash_mentions < 2:
        issues.append(f"Only {crash_mentions}/6 crash indicators mentioned")

    # Content should be substantial
    if len(content.split()) < 20:
        issues.append("Response too brief for comprehensive analysis")

    return len(issues) == 0, (
        "; ".join(issues) if issues else "All validation checks passed"
    )


if __name__ == "__main__":
    success = test_context_owl_fix()
    exit(0 if success else 1)
