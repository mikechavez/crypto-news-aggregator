"""Tests for Context Owl's market crash analysis capabilities.

This module tests Context Owl's ability to provide comprehensive market crash analysis
during real-world market dumps, correlating price movements with news drivers and
providing actionable context to users.
"""
import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Dict, Any, List
from datetime import datetime, timezone

from crypto_news_aggregator.main import app
from crypto_news_aggregator.core.auth import get_api_keys
from crypto_news_aggregator.core.config import get_settings


class TestContextOwlMarketCrashAnalysis:
    """Test Context Owl's market crash analysis capabilities."""

    def setup_method(self):
        """Set up test client and mock data."""
        self.client = TestClient(app)
        self.settings = get_settings()
        self.valid_api_keys = get_api_keys()

        # Skip if no API keys configured
        if not self.valid_api_keys:
            pytest.skip("No valid API keys configured for testing")

    def _create_mock_crash_context(self) -> Dict[str, Any]:
        """Create mock market crash context data."""
        return {
            "bitcoin": {
                "current_price": 43000,
                "price_change_percentage_24h_in_currency": -2.7,
                "price_change_percentage_1h_in_currency": -1.2,
                "market_cap": 840000000000,
                "total_volume": 25000000000
            },
            "ethereum": {
                "current_price": 2300,
                "price_change_percentage_24h_in_currency": -6.5,
                "price_change_percentage_1h_in_currency": -2.8,
                "market_cap": 280000000000,
                "total_volume": 15000000000
            }
        }

    def _create_mock_crash_articles(self) -> List[Dict[str, Any]]:
        """Create mock news articles related to market crash."""
        return [
            {
                "title": "Bitcoin ETF Outflows Reach $1.2B as Investors Flee Risk Assets",
                "source": "CoinDesk",
                "sentiment_score": -0.4,
                "sentiment_label": "negative",
                "keywords": ["ETF", "outflows", "bitcoin", "investors", "risk"],
                "published_at": datetime.now(timezone.utc).isoformat(),
                "url": "https://example.com/etf-outflows",
                "summary": "Major Bitcoin ETFs see massive outflows as market sentiment turns bearish."
            },
            {
                "title": "Whale Liquidations Trigger Cascade Selling in Crypto Markets",
                "source": "The Block",
                "sentiment_score": -0.6,
                "sentiment_label": "negative",
                "keywords": ["whale", "liquidations", "cascade", "selling", "crypto"],
                "published_at": datetime.now(timezone.utc).isoformat(),
                "url": "https://example.com/whale-liquidations",
                "summary": "Large position liquidations create downward pressure across major cryptocurrencies."
            },
            {
                "title": "Federal Reserve Signals Continued Hawkish Policy Stance",
                "source": "Reuters",
                "sentiment_score": -0.3,
                "sentiment_label": "negative",
                "keywords": ["federal reserve", "policy", "hawkish", "rates"],
                "published_at": datetime.now(timezone.utc).isoformat(),
                "url": "https://example.com/fed-policy",
                "summary": "Fed officials indicate no immediate plans for rate cuts, impacting risk assets."
            },
            {
                "title": "Crypto Market Sees $1.7B in Liquidations as Prices Plummet",
                "source": "Cointelegraph",
                "sentiment_score": -0.5,
                "sentiment_label": "negative",
                "keywords": ["liquidations", "crypto", "prices", "market"],
                "published_at": datetime.now(timezone.utc).isoformat(),
                "url": "https://example.com/market-liquidations",
                "summary": "Total liquidations across crypto exchanges reach record levels amid market turmoil."
            }
        ]

    def _create_mock_market_analysis(self, coin_id: str) -> str:
        """Create mock market analysis response for crash scenario."""
        if coin_id == "bitcoin":
            return (
                "Bitcoin (Rank #1) is trading at $43,000.00. "
                "Timeframe performance — 1h -1.20%, 24h -2.70%, 7d -8.50%. "
                "Key peer check: Ethereum 24h move -6.50%. "
                "Developing narratives: Key themes: market correction concerns, institutional investment growing; "
                "Emerging narratives: regulatory clarity emerging; "
                "Continuing themes: price decline trends; "
                "Strong bearish sentiment. "
                "Well-established narrative foundation. "
                "Overall sentiment -0.45."
            )
        elif coin_id == "ethereum":
            return (
                "Ethereum (Rank #2) is trading at $2,300.00. "
                "Timeframe performance — 1h -2.80%, 24h -6.50%, 7d -12.30%. "
                "Key peer check: Bitcoin 24h move -2.70%. "
                "Developing narratives: Key themes: price decline trends, technical innovation advancing; "
                "Emerging narratives: institutional adoption accelerating; "
                "Continuing themes: market correction concerns; "
                "Strong bearish sentiment. "
                "Developing narrative structure. "
                "Overall sentiment -0.52."
            )
        else:
            return f"{coin_id.capitalize()} market analysis during crash period."

    @patch('crypto_news_aggregator.api.openai_compatibility.get_price_service')
    @patch('crypto_news_aggregator.api.openai_compatibility.get_correlation_service')
    def test_crash_query_why_crypto_crashing(self, mock_correlation_service, mock_price_service):
        """Test 'Why is crypto crashing?' query with comprehensive context."""
        # Mock services
        mock_price_service_instance = AsyncMock()
        mock_price_service_instance.generate_market_analysis_commentary.side_effect = self._create_mock_market_analysis
        mock_price_service.return_value = mock_price_service_instance

        mock_correlation_service_instance = AsyncMock()
        mock_correlation_service_instance.calculate_correlation.return_value = {"ethereum": 0.85, "solana": 0.72}
        mock_correlation_service.return_value = mock_correlation_service_instance

        # Mock article service with crash-related articles
        with patch('crypto_news_aggregator.api.openai_compatibility.article_service') as mock_article_service:
            mock_article_service.get_average_sentiment_for_symbols.return_value = {"BTC": -0.45, "ETH": -0.52}

            request_data = {
                "model": "crypto-insight-agent",
                "messages": [{"role": "user", "content": "Why is crypto crashing?"}],
                "stream": False
            }

            response = self.client.post(
                "/v1/chat/completions",
                json=request_data,
                headers={"X-API-Key": self.valid_api_keys[0]}
            )

            assert response.status_code == 200
            response_data = response.json()
            content = response_data["choices"][0]["message"]["content"].lower()

            # Verify comprehensive crash analysis
            assert "choices" in response_data
            assert len(response_data["choices"]) > 0
            assert "message" in response_data["choices"][0]
            assert "content" in response_data["choices"][0]["message"]

            # Check for key crash drivers mentioned
            crash_drivers = ["etf", "outflows", "whale", "liquidations", "fed", "policy"]
            driver_mentions = sum(1 for driver in crash_drivers if driver in content)
            assert driver_mentions >= 2, f"Expected at least 2 crash drivers mentioned, got {driver_mentions}"

            # Verify actionable context is provided
            actionable_terms = ["context", "analysis", "sentiment", "narratives", "themes"]
            actionable_mentions = sum(1 for term in actionable_terms if term in content)
            assert actionable_mentions >= 2, f"Expected actionable context, got {actionable_mentions} terms"

    @patch('crypto_news_aggregator.api.openai_compatibility.get_price_service')
    @patch('crypto_news_aggregator.api.openai_compatibility.get_correlation_service')
    def test_crash_query_should_sell_bitcoin(self, mock_correlation_service, mock_price_service):
        """Test 'Should I sell Bitcoin?' query with balanced analysis."""
        # Mock services
        mock_price_service_instance = AsyncMock()
        mock_price_service_instance.generate_market_analysis_commentary.side_effect = self._create_mock_market_analysis
        mock_price_service.return_value = mock_price_service_instance

        mock_correlation_service_instance = AsyncMock()
        mock_correlation_service_instance.calculate_correlation.return_value = {"ethereum": 0.85}
        mock_correlation_service.return_value = mock_correlation_service_instance

        # Mock article service with crash-related articles
        with patch('crypto_news_aggregator.api.openai_compatibility.article_service') as mock_article_service:
            mock_article_service.get_average_sentiment_for_symbols.return_value = {"BTC": -0.45}

            request_data = {
                "model": "crypto-insight-agent",
                "messages": [{"role": "user", "content": "Should I sell Bitcoin?"}],
                "stream": False
            }

            response = self.client.post(
                "/v1/chat/completions",
                json=request_data,
                headers={"X-API-Key": self.valid_api_keys[0]}
            )

            assert response.status_code == 200
            response_data = response.json()
            content = response_data["choices"][0]["message"]["content"].lower()

            # Verify balanced analysis (not just price reporting)
            assert "choices" in response_data
            assert "bitcoin" in content
            assert any(term in content for term in ["analysis", "context", "sentiment", "narratives"])

            # Should provide context beyond just price
            price_only_terms = ["trading at", "price", "$"]
            context_terms = ["sentiment", "narratives", "themes", "outlook", "analysis"]
            price_mentions = sum(1 for term in price_only_terms if term in content)
            context_mentions = sum(1 for term in context_terms if term in content)

            assert context_mentions >= 1, "Should provide context beyond just price reporting"

    @patch('crypto_news_aggregator.api.openai_compatibility.get_price_service')
    @patch('crypto_news_aggregator.api.openai_compatibility.get_correlation_service')
    def test_crash_query_bear_market_start(self, mock_correlation_service, mock_price_service):
        """Test 'Is this the start of a bear market?' query with historical context."""
        # Mock services
        mock_price_service_instance = AsyncMock()
        mock_price_service_instance.generate_market_analysis_commentary.side_effect = self._create_mock_market_analysis
        mock_price_service.return_value = mock_price_service_instance

        mock_correlation_service_instance = AsyncMock()
        mock_correlation_service_instance.calculate_correlation.return_value = {"ethereum": 0.85, "solana": 0.72}
        mock_correlation_service.return_value = mock_correlation_service_instance

        # Mock article service with crash-related articles
        with patch('crypto_news_aggregator.api.openai_compatibility.article_service') as mock_article_service:
            mock_article_service.get_average_sentiment_for_symbols.return_value = {"BTC": -0.45, "ETH": -0.52}

            request_data = {
                "model": "crypto-insight-agent",
                "messages": [{"role": "user", "content": "Is this the start of a bear market?"}],
                "stream": False
            }

            response = self.client.post(
                "/v1/chat/completions",
                json=request_data,
                headers={"X-API-Key": self.valid_api_keys[0]}
            )

            assert response.status_code == 200
            response_data = response.json()
            content = response_data["choices"][0]["message"]["content"].lower()

            # Verify comprehensive analysis
            assert "choices" in response_data
            assert "bitcoin" in content or "crypto" in content

            # Should mention market context and drivers
            context_indicators = ["sentiment", "narratives", "themes", "analysis", "outlook"]
            context_mentions = sum(1 for indicator in context_indicators if indicator in content)
            assert context_mentions >= 2, "Should provide comprehensive market context"

    @patch('crypto_news_aggregator.api.openai_compatibility.get_price_service')
    @patch('crypto_news_aggregator.api.openai_compatibility.get_correlation_service')
    def test_crash_query_etf_outflows(self, mock_correlation_service, mock_price_service):
        """Test query specifically about ETF outflows."""
        # Mock services
        mock_price_service_instance = AsyncMock()
        mock_price_service_instance.generate_market_analysis_commentary.side_effect = self._create_mock_market_analysis
        mock_price_service.return_value = mock_price_service_instance

        mock_correlation_service_instance = AsyncMock()
        mock_correlation_service_instance.calculate_correlation.return_value = {"ethereum": 0.85}
        mock_correlation_service.return_value = mock_correlation_service_instance

        # Mock article service with crash-related articles
        with patch('crypto_news_aggregator.api.openai_compatibility.article_service') as mock_article_service:
            mock_article_service.get_average_sentiment_for_symbols.return_value = {"BTC": -0.45}

            request_data = {
                "model": "crypto-insight-agent",
                "messages": [{"role": "user", "content": "How are ETF outflows affecting Bitcoin price?"}],
                "stream": False
            }

            response = self.client.post(
                "/v1/chat/completions",
                json=request_data,
                headers={"X-API-Key": self.valid_api_keys[0]}
            )

            assert response.status_code == 200
            response_data = response.json()
            content = response_data["choices"][0]["message"]["content"].lower()

            # Verify ETF-specific analysis
            assert "choices" in response_data
            assert any(term in content for term in ["etf", "outflows", "institutional", "investment"])

            # Should correlate with price movements
            correlation_terms = ["affecting", "impact", "correlation", "relationship", "sentiment"]
            correlation_mentions = sum(1 for term in correlation_terms if term in content)
            assert correlation_mentions >= 1, "Should correlate ETF outflows with price movements"

    @patch('crypto_news_aggregator.api.openai_compatibility.get_price_service')
    @patch('crypto_news_aggregator.api.openai_compatibility.get_correlation_service')
    def test_crash_query_liquidations_impact(self, mock_correlation_service, mock_price_service):
        """Test query about liquidations impact."""
        # Mock services
        mock_price_service_instance = AsyncMock()
        mock_price_service_instance.generate_market_analysis_commentary.side_effect = self._create_mock_market_analysis
        mock_price_service.return_value = mock_price_service_instance

        mock_correlation_service_instance = AsyncMock()
        mock_correlation_service_instance.calculate_correlation.return_value = {"ethereum": 0.85, "solana": 0.72}
        mock_correlation_service.return_value = mock_correlation_service_instance

        # Mock article service with crash-related articles
        with patch('crypto_news_aggregator.api.openai_compatibility.article_service') as mock_article_service:
            mock_article_service.get_average_sentiment_for_symbols.return_value = {"BTC": -0.45, "ETH": -0.52}

            request_data = {
                "model": "crypto-insight-agent",
                "messages": [{"role": "user", "content": "How are whale liquidations affecting the market?"}],
                "stream": False
            }

            response = self.client.post(
                "/v1/chat/completions",
                json=request_data,
                headers={"X-API-Key": self.valid_api_keys[0]}
            )

            assert response.status_code == 200
            response_data = response.json()
            content = response_data["choices"][0]["message"]["content"].lower()

            # Verify liquidations analysis
            assert "choices" in response_data
            assert any(term in content for term in ["liquidations", "whale", "cascade", "selling"])

            # Should explain market mechanics
            mechanics_terms = ["pressure", "momentum", "volatility", "downward", "impact"]
            mechanics_mentions = sum(1 for term in mechanics_terms if term in content)
            assert mechanics_mentions >= 1, "Should explain market mechanics of liquidations"

    def test_crash_context_owl_comprehensive_analysis(self):
        """Test that Context Owl provides comprehensive crash analysis."""
        """This test verifies that Context Owl delivers comprehensive crash analysis
        correlating price movements with news drivers, providing users clear context
        about why markets are down and what it means.
        """
        # Test multiple crash-related queries to ensure comprehensive coverage
        crash_queries = [
            "Why is crypto crashing right now?",
            "What are the main drivers of this market dump?",
            "How are ETF outflows impacting Bitcoin?",
            "Should I be worried about this crash?",
            "Is this a temporary correction or start of bear market?"
        ]

        for query in crash_queries:
            with patch('crypto_news_aggregator.api.openai_compatibility.get_price_service') as mock_price_service, \
                 patch('crypto_news_aggregator.api.openai_compatibility.get_correlation_service') as mock_correlation_service, \
                 patch('crypto_news_aggregator.api.openai_compatibility.article_service') as mock_article_service:

                # Setup mocks
                mock_price_service_instance = AsyncMock()
                mock_price_service_instance.generate_market_analysis_commentary.side_effect = self._create_mock_market_analysis
                mock_price_service.return_value = mock_price_service_instance

                mock_correlation_service_instance = AsyncMock()
                mock_correlation_service_instance.calculate_correlation.return_value = {"ethereum": 0.85, "solana": 0.72}
                mock_correlation_service.return_value = mock_correlation_service_instance

                mock_article_service.get_average_sentiment_for_symbols.return_value = {"BTC": -0.45, "ETH": -0.52}

                request_data = {
                    "model": "crypto-insight-agent",
                    "messages": [{"role": "user", "content": query}],
                    "stream": False
                }

                response = self.client.post(
                    "/v1/chat/completions",
                    json=request_data,
                    headers={"X-API-Key": self.valid_api_keys[0]}
                )

                assert response.status_code == 200, f"Failed for query: {query}"
                response_data = response.json()
                content = response_data["choices"][0]["message"]["content"].lower()

                # Verify comprehensive response structure
                assert "choices" in response_data
                assert len(response_data["choices"]) > 0
                assert "message" in response_data["choices"][0]
                assert "content" in response_data["choices"][0]["message"]
                assert "role" in response_data["choices"][0]["message"]
                assert response_data["choices"][0]["message"]["role"] == "assistant"

                # Verify actionable context is provided
                actionable_indicators = ["sentiment", "narratives", "themes", "analysis", "context", "outlook"]
                actionable_score = sum(1 for indicator in actionable_indicators if indicator in content)

                # Content should be substantial (more than just price reporting)
                content_length = len(content.split())
                assert content_length >= 10, f"Response too short for query: {query}"

                # Should provide context beyond basic price info
                assert actionable_score >= 1, f"Insufficient context for query: {query}"

    def test_crash_context_owl_key_drivers_mentioned(self):
        """Test that Context Owl mentions key crash drivers."""
        """This test specifically verifies that Context Owl mentions key drivers:
        ETF outflows, whale liquidations, Fed policy uncertainty.
        """
        key_drivers = ["etf", "outflows", "whale", "liquidations", "fed", "policy", "federal reserve"]

        with patch('crypto_news_aggregator.api.openai_compatibility.get_price_service') as mock_price_service, \
             patch('crypto_news_aggregator.api.openai_compatibility.get_correlation_service') as mock_correlation_service, \
             patch('crypto_news_aggregator.api.openai_compatibility.article_service') as mock_article_service:

            # Setup mocks
            mock_price_service_instance = AsyncMock()
            mock_price_service_instance.generate_market_analysis_commentary.side_effect = self._create_mock_market_analysis
            mock_price_service.return_value = mock_price_service_instance

            mock_correlation_service_instance = AsyncMock()
            mock_correlation_service_instance.calculate_correlation.return_value = {"ethereum": 0.85}
            mock_correlation_service.return_value = mock_correlation_service_instance

            mock_article_service.get_average_sentiment_for_symbols.return_value = {"BTC": -0.45}

            request_data = {
                "model": "crypto-insight-agent",
                "messages": [{"role": "user", "content": "Why is the crypto market dumping so hard?"}],
                "stream": False
            }

            response = self.client.post(
                "/v1/chat/completions",
                json=request_data,
                headers={"X-API-Key": self.valid_api_keys[0]}
            )

            assert response.status_code == 200
            response_data = response.json()
            content = response_data["choices"][0]["message"]["content"].lower()

            # Check that key drivers are mentioned
            driver_mentions = sum(1 for driver in key_drivers if driver in content)
            assert driver_mentions >= 2, f"Expected at least 2 key drivers mentioned, got {driver_mentions}: {content}"

            # Verify specific driver categories
            institutional_drivers = ["etf", "outflows", "institutional"]
            institutional_mentions = sum(1 for driver in institutional_drivers if driver in content)
            assert institutional_mentions >= 1, "Should mention institutional/ETF drivers"

            liquidation_drivers = ["whale", "liquidations", "cascade"]
            liquidation_mentions = sum(1 for driver in liquidation_drivers if driver in content)
            assert liquidation_mentions >= 1, "Should mention liquidation drivers"

            policy_drivers = ["fed", "policy", "federal", "reserve"]
            policy_mentions = sum(1 for driver in policy_drivers if driver in content)
            assert policy_mentions >= 1, "Should mention policy drivers"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
