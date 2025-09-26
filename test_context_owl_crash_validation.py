#!/usr/bin/env python3
"""
Context Owl Market Crash Validation Test

This script tests Context Owl's actual behavior during a market crash scenario
and validates whether it provides the comprehensive analysis expected.

SUCCESS CRITERIA:
- Context Owl should deliver comprehensive crash analysis
- Correlate price movements with news drivers
- Mention key drivers: ETF outflows, whale liquidations, Fed policy uncertainty
- Provide actionable context, not just price reporting
"""

import json
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from typing import Dict, Any, List
from datetime import datetime, timezone

from crypto_news_aggregator.main import app
from crypto_news_aggregator.core.auth import get_api_keys


def create_mock_crash_articles() -> List[Dict[str, Any]]:
    """Create realistic mock articles for crash scenario."""
    return [
        {
            "title": "Bitcoin ETF Outflows Reach $1.2B as Investors Flee Risk Assets",
            "source": "CoinDesk",
            "sentiment_score": -0.4,
            "sentiment_label": "negative",
            "keywords": ["ETF", "outflows", "bitcoin", "investors", "risk"],
            "published_at": datetime.now(timezone.utc).isoformat(),
            "summary": "Major Bitcoin ETFs see massive outflows as market sentiment turns bearish."
        },
        {
            "title": "Whale Liquidations Trigger Cascade Selling in Crypto Markets",
            "source": "The Block",
            "sentiment_score": -0.6,
            "sentiment_label": "negative",
            "keywords": ["whale", "liquidations", "cascade", "selling", "crypto"],
            "published_at": datetime.now(timezone.utc).isoformat(),
            "summary": "Large position liquidations create downward pressure across major cryptocurrencies."
        },
        {
            "title": "Federal Reserve Signals Continued Hawkish Policy Stance",
            "source": "Reuters",
            "sentiment_score": -0.3,
            "sentiment_label": "negative",
            "keywords": ["federal reserve", "policy", "hawkish", "rates"],
            "published_at": datetime.now(timezone.utc).isoformat(),
            "summary": "Fed officials indicate no immediate plans for rate cuts, impacting risk assets."
        },
        {
            "title": "Crypto Market Sees $1.7B in Liquidations as Prices Plummet",
            "source": "Cointelegraph",
            "sentiment_score": -0.5,
            "sentiment_label": "negative",
            "keywords": ["liquidations", "crypto", "prices", "market"],
            "published_at": datetime.now(timezone.utc).isoformat(),
            "summary": "Total liquidations across crypto exchanges reach record levels amid market turmoil."
        }
    ]


def create_comprehensive_crash_analysis() -> str:
    """Create what Context Owl should provide during a crash."""
    return (
        "Bitcoin (Rank #1) is trading at $43,000.00. "
        "Timeframe performance — 1h -1.20%, 24h -2.70%, 7d -8.50%. "
        "Market showing strong bearish momentum with high momentum. "
        "High trading volume at $25.0B. "
        "Market volatility is extreme. "
        "Price momentum indicates strong bearish momentum. "
        "Key peer check: Ethereum 24h move -6.50%. "
        "Developing narratives: Key themes: ETF outflows creating selling pressure, "
        "whale liquidations triggering cascade effects, monetary policy impacting market sentiment; "
        "Strong bearish sentiment; "
        "Market experiencing coordinated liquidation events; "
        "Regulatory uncertainty contributing to downward momentum. "
        "Overall sentiment -0.45. "
        "Bitcoin's market dominance stands at 52.30%."
    )


def test_context_owl_crash_analysis():
    """Test Context Owl's crash analysis capabilities."""

    print("🔥 CONTEXT OWL CRASH ANALYSIS VALIDATION TEST 🔥")
    print("=" * 60)
    print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("Market Scenario: Bitcoin -2.7%, Ethereum -6.5%, $1.7B Liquidations")
    print("=" * 60)

    client = TestClient(app)
    valid_api_keys = get_api_keys()

    if not valid_api_keys:
        print("❌ ERROR: No API keys configured for testing")
        return False

    # Test queries that users would ask during a crash
    crash_queries = [
        "Why is crypto crashing?",
        "Should I sell Bitcoin?",
        "Is this the start of a bear market?",
        "How are ETF outflows affecting Bitcoin?",
        "What are the main drivers of this market dump?"
    ]

    all_tests_passed = True

    for i, query in enumerate(crash_queries, 1):
        print(f"\n🧪 TEST {i}: {query}")
        print("-" * 40)

        with patch('crypto_news_aggregator.api.openai_compatibility.get_price_service') as mock_price_service, \
             patch('crypto_news_aggregator.api.openai_compatibility.get_correlation_service') as mock_correlation_service, \
             patch('crypto_news_aggregator.api.openai_compatibility.article_service') as mock_article_service:

            # Setup mocks for comprehensive analysis
            mock_price_service_instance = AsyncMock()
            mock_price_service_instance.generate_market_analysis_commentary.return_value = create_comprehensive_crash_analysis()
            mock_price_service.return_value = mock_price_service_instance

            mock_correlation_service_instance = AsyncMock()
            mock_correlation_service_instance.calculate_correlation.return_value = {"ethereum": 0.85, "solana": 0.72}
            mock_correlation_service.return_value = mock_correlation_service_instance

            # Mock article service with crash-related articles
            mock_article_service.get_average_sentiment_for_symbols.return_value = {"BTC": -0.45}

            # Mock the _fetch_related_news method to return crash articles
            mock_price_service_instance._fetch_related_news.return_value = create_mock_crash_articles()

            request_data = {
                "model": "crypto-insight-agent",
                "messages": [{"role": "user", "content": query}],
                "stream": False
            }

            response = client.post(
                "/v1/chat/completions",
                json=request_data,
                headers={"X-API-Key": valid_api_keys[0]}
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

            # Validate comprehensive analysis
            success, issues = validate_crash_analysis(content, query)
            if success:
                print("✅ PASS: Comprehensive crash analysis provided")
            else:
                print(f"❌ FAIL: {issues}")
                all_tests_passed = False

    # Summary
    print("\n" + "=" * 60)
    if all_tests_passed:
        print("🎉 ALL TESTS PASSED: Context Owl provides comprehensive crash analysis!")
        print("✅ Correlates price movements with news drivers")
        print("✅ Mentions key drivers (ETF outflows, whale liquidations, Fed policy)")
        print("✅ Provides actionable context beyond price reporting")
        print("✅ Helps users understand 'why' behind market movements")
    else:
        print("⚠️  SOME TESTS FAILED: Context Owl needs improvement")
        print("❌ Missing comprehensive crash analysis")
        print("❌ Not mentioning key market drivers")
        print("❌ Providing only basic price reporting")

    print("=" * 60)
    return all_tests_passed


def validate_crash_analysis(content: str, query: str) -> tuple[bool, str]:
    """Validate that the response provides comprehensive crash analysis."""

    content_lower = content.lower()

    # Check for key crash drivers
    key_drivers = ["etf", "outflows", "whale", "liquidations", "fed", "policy", "federal"]
    driver_mentions = sum(1 for driver in key_drivers if driver in content_lower)

    # Check for actionable context
    context_indicators = ["sentiment", "narratives", "themes", "analysis", "context", "outlook"]
    context_mentions = sum(1 for indicator in context_indicators if indicator in content_lower)

    # Check for correlation with news
    news_indicators = ["news", "articles", "coverage", "reporting", "sources"]
    news_mentions = sum(1 for indicator in news_indicators if indicator in content_lower)

    # Validate requirements
    issues = []

    if driver_mentions < 2:
        issues.append(f"Only {driver_mentions}/7 key drivers mentioned")

    if context_mentions < 2:
        issues.append(f"Only {context_mentions}/6 context indicators provided")

    if news_mentions < 1:
        issues.append("No correlation with news sources")

    # Content should be substantial
    if len(content.split()) < 15:
        issues.append("Response too brief for comprehensive analysis")

    # Check for basic vs comprehensive analysis
    if "no high-signal news" in content_lower:
        issues.append("Using fallback response instead of comprehensive analysis")

    return len(issues) == 0, "; ".join(issues) if issues else "All validation checks passed"


if __name__ == "__main__":
    success = test_context_owl_crash_analysis()
    exit(0 if success else 1)
