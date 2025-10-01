#!/usr/bin/env python3
"""
Context Owl Market Crash Analysis - Final Validation

This script provides a comprehensive validation of the FIXED Context Owl implementation
during a market crash scenario.
"""

import json
from fastapi.testclient import TestClient
from unittest.mock import patch
from typing import Dict, Any, List
from datetime import datetime, timezone

from crypto_news_aggregator.main import app
from crypto_news_aggregator.core.auth import get_api_keys


def create_comprehensive_crash_analysis() -> str:
    """Create what Context Owl should provide during a crash with realistic prices and clear explanations."""
    return (
        "Bitcoin (Rank #1) is trading at $60,250.00. "
        "Timeframe performance — 1h -1.20%, 24h -2.70%, 7d -8.50%. "
        "Market showing strong bearish momentum with moderate momentum. "
        "High trading volume at $25.0B. "
        "Market volatility is high. "
        "Price momentum indicates strong bearish momentum. "
        "Key peer check: Ethereum 24h move -6.50%. "
        "Market analysis: Key drivers: ETF outflows creating significant selling pressure, "
        "large holder sales triggering market decline, central bank policy creating market uncertainty; "
        "Strong negative sentiment suggesting continued downward pressure; "
        "Multiple consistent factors pointing to continued downward movement; "
        "Strong negative news flow suggests continued downside risk. "
        "Overall sentiment -0.43. "
        "Bitcoin's market dominance stands at 52.30%."
    )


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


def test_context_owl_comprehensive():
    """Comprehensive test of the FIXED Context Owl implementation."""

    print("🔥 CONTEXT OWL MARKET CRASH ANALYSIS - FINAL VALIDATION 🔥")
    print("=" * 70)
    print("Testing FIXED Context Owl with comprehensive crash analysis")
    print("=" * 70)

    client = TestClient(app)
    valid_api_keys = get_api_keys()

    if not valid_api_keys:
        print("❌ ERROR: No API keys configured for testing")
        return False

    # Test queries that represent real user scenarios during a crash
    crash_queries = [
        "Why is crypto crashing?",
        "Should I sell Bitcoin?",
        "Is this the start of a bear market?",
        "How are ETF outflows affecting Bitcoin?",
        "What are the main drivers of this market dump?",
    ]

    all_tests_passed = True
    total_score = 0

    for i, query in enumerate(crash_queries, 1):
        print(f"\n🧪 TEST {i}: {query}")
        print("-" * 50)

        # Test with comprehensive mocking
        with patch(
            "crypto_news_aggregator.services.price_service.article_service"
        ) as mock_article_service:
            mock_article_service.get_top_articles_for_symbols.return_value = (
                create_crash_articles()
            )
            mock_article_service.get_average_sentiment_for_symbols.return_value = {
                "BTC": -0.45
            }

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
                        all_tests_passed = False
                        continue

                    response_data = response.json()
                    content = response_data["choices"][0]["message"]["content"]
                    print(f"✅ Response received ({len(content)} chars)")

                    # Validate comprehensive analysis
                    score, issues, details = validate_comprehensive_crash_analysis(
                        content, query
                    )
                    total_score += score

                    if score >= 8:
                        print("✅ PASS: Excellent crash analysis provided")
                    elif score >= 6:
                        print("✅ PASS: Good crash analysis provided")
                    elif score >= 4:
                        print("⚠️  PARTIAL: Basic crash analysis provided")
                    else:
                        print("❌ FAIL: Insufficient crash analysis")
                        all_tests_passed = False

                    if issues:
                        print(f"   Issues: {issues}")
                    if details:
                        print(f"   Details: {details}")

    # Final summary
    print("\n" + "=" * 70)
    print("📊 FINAL RESULTS SUMMARY")
    print("=" * 70)

    avg_score = total_score / len(crash_queries)
    print(f"Average Score: {avg_score:.1f}/10")

    if all_tests_passed and avg_score >= 8:
        print("🎉 EXCELLENT: Context Owl provides comprehensive crash analysis!")
        print("✅ Responds to general market queries")
        print("✅ Uses sophisticated narrative analysis")
        print(
            "✅ Mentions key crash drivers (ETF outflows, whale liquidations, Fed policy)"
        )
        print("✅ Provides actionable context beyond price reporting")
        print("✅ Correlates price movements with news drivers")
        print("✅ Shows market volatility and momentum analysis")
        print("✅ Includes sentiment analysis and narrative evolution")
        print("\n🚀 CONTEXT OWL IS NOW READY FOR MARKET CRASHES!")
    elif avg_score >= 6:
        print("✅ GOOD: Context Owl provides solid crash analysis")
        print("⚠️  Minor improvements could enhance the analysis")
    else:
        print("⚠️  NEEDS IMPROVEMENT: Context Owl crash analysis needs work")
        print("❌ Still missing some key crash analysis features")

    print("=" * 70)
    return all_tests_passed and avg_score >= 8


def validate_comprehensive_crash_analysis(
    content: str, query: str
) -> tuple[int, str, str]:
    """Validate comprehensive crash analysis with detailed scoring."""

    content_lower = content.lower()
    score = 0
    issues = []
    details = []

    # 1. Check for key crash drivers (3 points)
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
    score += min(driver_mentions * 0.5, 3)
    if driver_mentions >= 2:
        details.append(f"✅ Key drivers: {driver_mentions}/7 mentioned")
    else:
        issues.append(f"Only {driver_mentions}/7 key drivers mentioned")

    # 2. Check for actionable context (2 points)
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
    score += min(context_mentions * 0.4, 2)
    if context_mentions >= 3:
        details.append(f"✅ Context: {context_mentions}/6 indicators")
    else:
        issues.append(f"Only {context_mentions}/6 context indicators")

    # 3. Check for market mechanics (2 points)
    market_indicators = ["volatility", "momentum", "volume", "dominance", "correlation"]
    market_mentions = sum(
        1 for indicator in market_indicators if indicator in content_lower
    )
    score += min(market_mentions * 0.4, 2)
    if market_mentions >= 2:
        details.append(f"✅ Market mechanics: {market_mentions}/5 indicators")
    else:
        issues.append(f"Only {market_mentions}/5 market indicators")

    # 4. Check for crash-specific language (2 points)
    crash_terms = ["crash", "bearish", "selling", "pressure", "turmoil", "cascade"]
    crash_mentions = sum(1 for term in crash_terms if term in content_lower)
    score += min(crash_mentions * 0.3, 2)
    if crash_mentions >= 3:
        details.append(f"✅ Crash language: {crash_mentions}/6 terms")
    else:
        issues.append(f"Only {crash_mentions}/6 crash terms")

    # 5. Check response length and comprehensiveness (1 point)
    if len(content.split()) >= 50:
        score += 1
        details.append("✅ Comprehensive response length")
    else:
        issues.append("Response too brief")

    return score, "; ".join(issues), "; ".join(details)


if __name__ == "__main__":
    success = test_context_owl_comprehensive()
    exit(0 if success else 1)
