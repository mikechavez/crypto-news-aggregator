#!/usr/bin/env python3
"""
Context Owl Market Crash Analysis Demonstration

This script demonstrates what Context Owl SHOULD be doing during a market crash.
It shows how Context Owl should correlate price movements with news drivers
and provide comprehensive, actionable context to users.

The current implementation is missing the sophisticated narrative analysis
that would mention key drivers like ETF outflows, whale liquidations, and Fed policy.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List
from collections import Counter


def demonstrate_context_owl_crash_analysis():
    """Demonstrate what Context Owl should provide during a market crash."""

    print("🔥 CONTEXT OWL MARKET CRASH ANALYSIS DEMONSTRATION 🔥")
    print("=" * 60)
    print(f"Market Crash: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("Bitcoin: -2.7% | Ethereum: -6.5% | $1.7B Liquidations")
    print("=" * 60)

    # Simulate what Context Owl currently provides (basic analysis)
    print("\n❌ CURRENT CONTEXT OWL RESPONSE:")
    print("Bitcoin (Rank #1) is trading at $43,000.00.")
    print("Timeframe performance — 1h -1.20%, 24h -2.70%, 7d -8.50%.")
    print("Developing narratives: No high-signal news to analyze yet.")
    print("Overall sentiment 0.00.")
    print("\n❌ ISSUE: No correlation with crash drivers, no actionable context!")

    # Demonstrate what Context Owl SHOULD provide
    print("\n✅ EXPECTED CONTEXT OWL RESPONSE:")
    expected_analysis = generate_comprehensive_crash_analysis()
    print(expected_analysis)

    # Show key drivers that should be mentioned
    print("\n🎯 KEY CRASH DRIVERS THAT SHOULD BE MENTIONED:")
    key_drivers = [
        "📉 ETF Outflows: $1.2B Bitcoin ETF outflows creating selling pressure",
        "🐋 Whale Liquidations: Large position liquidations triggering cascade selling",
        "🏦 Fed Policy: Federal Reserve signals continued hawkish stance",
        "💹 Market Mechanics: $1.7B total liquidations across crypto exchanges",
        "📰 Narrative Analysis: Strong bearish sentiment with regulatory concerns",
        "📊 Correlation: High correlation between BTC/ETH during crash events",
    ]

    for driver in key_drivers:
        print(f"  {driver}")

    print("\n" + "=" * 60)
    print("📈 CONTEXT OWL VALUE PROPOSITION:")
    print("• Correlates price action with news drivers")
    print("• Provides actionable context, not just price reporting")
    print("• Explains 'why' behind market movements")
    print("• Helps users make informed decisions during volatility")
    print("=" * 60)


def generate_comprehensive_crash_analysis() -> str:
    """Generate what Context Owl should provide during a market crash."""

    # Mock crash scenario data
    crash_articles = [
        {
            "title": "Bitcoin ETF Outflows Reach $1.2B as Investors Flee Risk Assets",
            "source": "CoinDesk",
            "sentiment_score": -0.4,
            "keywords": ["ETF", "outflows", "bitcoin", "investors", "risk"],
        },
        {
            "title": "Whale Liquidations Trigger Cascade Selling in Crypto Markets",
            "source": "The Block",
            "sentiment_score": -0.6,
            "keywords": ["whale", "liquidations", "cascade", "selling"],
        },
        {
            "title": "Federal Reserve Signals Continued Hawkish Policy Stance",
            "source": "Reuters",
            "sentiment_score": -0.3,
            "keywords": ["federal reserve", "policy", "hawkish"],
        },
    ]

    # Analyze themes and narratives
    themes = extract_themes_from_articles(crash_articles)
    sentiment_trend = analyze_sentiment_trend(crash_articles)

    # Generate comprehensive analysis
    analysis_parts = [
        "Bitcoin (Rank #1) is trading at $43,000.00.",
        "Timeframe performance — 1h -1.20%, 24h -2.70%, 7d -8.50%.",
        "Key peer check: Ethereum 24h move -6.50%.",
        generate_narrative_description(themes, sentiment_trend),
        "Bitcoin's market dominance stands at 52.30%.",
    ]

    return " ".join(analysis_parts)


def extract_themes_from_articles(articles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Extract meaningful themes from crash-related articles."""
    themes = []
    sentiment_scores = []
    narrative_elements = []

    for article in articles:
        title = article.get("title", "").lower()
        keywords = article.get("keywords", [])

        # Extract themes
        if any(word in title for word in ["etf", "outflows", "institutional"]):
            themes.append("institutional_investment")
        if any(word in title for word in ["whale", "liquidations", "cascade"]):
            themes.append("liquidation_events")
        if any(word in title for word in ["federal", "policy", "hawkish"]):
            themes.append("regulatory_development")

        # Extract sentiment
        sentiment_score = article.get("sentiment_score", 0.0)
        sentiment_scores.append(sentiment_score)

        # Extract narrative elements
        if "bear" in title or "crash" in title:
            narrative_elements.append("bearish_sentiment")

    theme_counts = Counter(themes)
    sorted_themes = sorted(theme_counts.items(), key=lambda x: x[1], reverse=True)

    return {
        "themes": sorted_themes,
        "sentiment_scores": sentiment_scores,
        "narrative_elements": list(set(narrative_elements)),
        "avg_sentiment": (
            sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.0
        ),
    }


def analyze_sentiment_trend(articles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze sentiment trends in crash articles."""
    sentiment_scores = [article.get("sentiment_score", 0.0) for article in articles]
    avg_sentiment = (
        sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.0
    )

    if avg_sentiment <= -0.15:
        trend = "bearish"
        confidence = min(abs(avg_sentiment) * 3, 1.0)
    else:
        trend = "neutral"
        confidence = 0.5

    return {"trend": trend, "confidence": confidence, "avg_score": avg_sentiment}


def generate_narrative_description(themes: Dict, sentiment_trend: Dict) -> str:
    """Generate comprehensive narrative description for crash scenario."""
    top_themes = themes.get("themes", [])

    if not top_themes:
        return "Developing narratives: Limited coverage observed."

    theme_descriptions = []
    for theme, count in top_themes[:3]:
        if theme == "institutional_investment":
            theme_descriptions.append("ETF outflows creating selling pressure")
        elif theme == "liquidation_events":
            theme_descriptions.append("whale liquidations triggering cascade effects")
        elif theme == "regulatory_development":
            theme_descriptions.append("Federal Reserve policy impacting risk assets")
        else:
            theme_descriptions.append(f"{theme.replace('_', ' ')} trends")

    narrative_parts = []
    narrative_parts.append(f"Key themes: {', '.join(theme_descriptions)}")

    # Add crash-specific context
    narrative_parts.append(
        "Strong bearish sentiment with institutional selling pressure"
    )
    narrative_parts.append("Market experiencing coordinated liquidation events")
    narrative_parts.append("Regulatory uncertainty contributing to downward momentum")

    sentiment_desc = f"Strong {sentiment_trend['trend']} sentiment"
    narrative_parts.append(sentiment_desc)

    return f"Developing narratives: {'; '.join(narrative_parts)}. Overall sentiment {themes.get('avg_sentiment', 0):+.2f}."


if __name__ == "__main__":
    demonstrate_context_owl_crash_analysis()
