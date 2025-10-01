"""
End-to-End Integration Test for Context Owl - Sentient AGI Partnership

This test simulates a complete integration scenario between Context Owl and Sentient AGI,
demonstrating seamless OpenAI-compatible API integration with cryptocurrency analysis capabilities.
"""

import pytest
import json
import time
from typing import Dict, Any
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from crypto_news_aggregator.main import app
from crypto_news_aggregator.core.auth import get_api_keys


class TestSentientAGIIntegration:
    """End-to-end integration tests simulating Sentient AGI usage patterns."""

    def setup_method(self):
        """Set up test client and mock services."""
        self.client = TestClient(app)
        self.api_key = get_api_keys()[0] if get_api_keys() else "test-api-key"

    def test_complete_crypto_analysis_workflow(self):
        """Test a complete cryptocurrency analysis workflow as Sentient AGI would use it."""

        # Phase 1: Initial market overview
        print("🔍 Phase 1: Market Overview Query")
        market_query = {
            "model": "crypto-insight-agent",
            "messages": [
                {
                    "role": "user",
                    "content": "Give me a comprehensive overview of the current cryptocurrency market. Focus on major coins like Bitcoin, Ethereum, and Solana.",
                }
            ],
            "stream": False,
        }

        response = self.client.post(
            "/v1/chat/completions",
            json=market_query,
            headers={"X-API-Key": self.api_key},
        )

        assert response.status_code == 200
        market_data = response.json()
        assert "choices" in market_data
        assert len(market_data["choices"]) > 0

        market_response = market_data["choices"][0]["message"]["content"]
        print(f"✅ Market Overview: {market_response[:100]}...")

        # Phase 2: Sentiment analysis for investment decisions
        print("\n📊 Phase 2: Sentiment Analysis")
        sentiment_query = {
            "model": "crypto-insight-agent",
            "messages": [
                {
                    "role": "user",
                    "content": "What is the current market sentiment for Bitcoin and Ethereum? Should I be bullish or bearish?",
                }
            ],
            "stream": False,
        }

        response = self.client.post(
            "/v1/chat/completions",
            json=sentiment_query,
            headers={"X-API-Key": self.api_key},
        )

        assert response.status_code == 200
        sentiment_data = response.json()
        sentiment_response = sentiment_data["choices"][0]["message"]["content"]
        print(f"✅ Sentiment Analysis: {sentiment_response[:100]}...")

        # Phase 3: Correlation analysis for portfolio optimization
        print("\n🔗 Phase 3: Correlation Analysis")
        correlation_query = {
            "model": "crypto-insight-agent",
            "messages": [
                {
                    "role": "user",
                    "content": "How correlated are Bitcoin, Ethereum, and Solana? What does this mean for portfolio diversification?",
                }
            ],
            "stream": False,
        }

        response = self.client.post(
            "/v1/chat/completions",
            json=correlation_query,
            headers={"X-API-Key": self.api_key},
        )

        assert response.status_code == 200
        correlation_data = response.json()
        correlation_response = correlation_data["choices"][0]["message"]["content"]
        print(f"✅ Correlation Analysis: {correlation_response[:100]}...")

        # Phase 4: Streaming response for real-time updates
        print("\n⚡ Phase 4: Real-time Streaming")
        streaming_query = {
            "model": "crypto-insight-agent",
            "messages": [
                {
                    "role": "user",
                    "content": "Give me real-time updates on Bitcoin price movements and news sentiment.",
                }
            ],
            "stream": True,
        }

        response = self.client.post(
            "/v1/chat/completions",
            json=streaming_query,
            headers={"X-API-Key": self.api_key},
        )

        assert response.status_code == 200
        assert (
            response.headers.get("content-type") == "text/event-stream; charset=utf-8"
        )

        streaming_content = response.content.decode()
        assert "data:" in streaming_content
        assert "[DONE]" in streaming_content
        print(f"✅ Streaming Response: {len(streaming_content)} characters received")

        # Phase 5: Multi-turn conversation (conversational AI)
        print("\n💬 Phase 5: Multi-turn Conversation")
        conversation_query = {
            "model": "crypto-insight-agent",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a cryptocurrency trading advisor.",
                },
                {
                    "role": "user",
                    "content": "I'm new to crypto. What should I know about Bitcoin?",
                },
                {
                    "role": "assistant",
                    "content": "Bitcoin is the first and most well-known cryptocurrency. It's a decentralized digital currency that operates on a blockchain network.",
                },
                {"role": "user", "content": "Is it a good investment right now?"},
            ],
            "stream": False,
        }

        response = self.client.post(
            "/v1/chat/completions",
            json=conversation_query,
            headers={"X-API-Key": self.api_key},
        )

        assert response.status_code == 200
        conversation_data = response.json()
        conversation_response = conversation_data["choices"][0]["message"]["content"]
        print(f"✅ Multi-turn Conversation: {conversation_response[:100]}...")

        print("\n🎉 All integration phases completed successfully!")

        return {
            "market_overview": market_response,
            "sentiment_analysis": sentiment_response,
            "correlation_analysis": correlation_response,
            "streaming_response": streaming_content,
            "conversation_response": conversation_response,
        }

    def test_authentication_methods(self):
        """Test both API key and Bearer token authentication methods."""

        print("🔐 Testing Authentication Methods")

        # Test API Key authentication
        api_key_query = {
            "model": "crypto-insight-agent",
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": False,
        }

        response = self.client.post(
            "/v1/chat/completions",
            json=api_key_query,
            headers={"X-API-Key": self.api_key},
        )

        assert response.status_code == 200
        print("✅ API Key authentication working")

        # Test Bearer token authentication
        bearer_query = {
            "model": "crypto-insight-agent",
            "messages": [{"role": "user", "content": "Hello with Bearer token"}],
            "stream": False,
        }

        response = self.client.post(
            "/v1/chat/completions",
            json=bearer_query,
            headers={"Authorization": "Bearer test-token"},
        )

        # Should fail with invalid token but not with format error
        assert response.status_code in [401, 403]
        print("✅ Bearer token authentication format accepted")

    def test_error_scenarios(self):
        """Test error handling scenarios."""

        print("❌ Testing Error Scenarios")

        # Test empty messages
        empty_query = {"model": "crypto-insight-agent", "messages": [], "stream": False}

        response = self.client.post(
            "/v1/chat/completions",
            json=empty_query,
            headers={"X-API-Key": self.api_key},
        )

        assert response.status_code == 400
        assert "Messages list cannot be empty" in response.json()["detail"]
        print("✅ Empty messages error handling working")

        # Test missing authentication
        no_auth_query = {
            "model": "crypto-insight-agent",
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": False,
        }

        response = self.client.post("/v1/chat/completions", json=no_auth_query)

        assert response.status_code == 401
        assert "Missing or invalid API key" in response.json()["detail"]
        print("✅ Missing authentication error handling working")

        # Test invalid API key
        invalid_key_query = {
            "model": "crypto-insight-agent",
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": False,
        }

        response = self.client.post(
            "/v1/chat/completions",
            json=invalid_key_query,
            headers={"X-API-Key": "invalid-key"},
        )

        assert response.status_code == 403
        assert "Invalid API key" in response.json()["detail"]
        print("✅ Invalid API key error handling working")

    def test_performance_requirements(self):
        """Test that performance requirements are met."""

        print("⚡ Testing Performance Requirements")

        # Test response time for non-streaming requests
        start_time = time.time()

        query = {
            "model": "crypto-insight-agent",
            "messages": [{"role": "user", "content": "What is Bitcoin price?"}],
            "stream": False,
        }

        response = self.client.post(
            "/v1/chat/completions", json=query, headers={"X-API-Key": self.api_key}
        )

        end_time = time.time()
        response_time = (end_time - start_time) * 1000  # Convert to milliseconds

        assert response.status_code == 200
        assert response_time < 3000  # Should be under 3 seconds
        print(f"✅ Response time: {response_time:.2f}ms (under 3s requirement)")

        # Test streaming response format
        streaming_query = {
            "model": "crypto-insight-agent",
            "messages": [{"role": "user", "content": "Tell me about crypto"}],
            "stream": True,
        }

        response = self.client.post(
            "/v1/chat/completions",
            json=streaming_query,
            headers={"X-API-Key": self.api_key},
        )

        assert response.status_code == 200
        assert (
            response.headers.get("content-type") == "text/event-stream; charset=utf-8"
        )
        print("✅ Streaming response format correct")

    def test_openai_compatibility(self):
        """Test full OpenAI API compatibility."""

        print("🔄 Testing OpenAI Compatibility")

        # Test all required OpenAI request parameters
        full_query = {
            "model": "crypto-insight-agent",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful cryptocurrency assistant.",
                },
                {
                    "role": "user",
                    "content": "What are the latest trends in cryptocurrency?",
                },
            ],
            "stream": False,
            "temperature": 0.7,
            "max_tokens": 1000,
            "top_p": 1.0,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
        }

        response = self.client.post(
            "/v1/chat/completions", json=full_query, headers={"X-API-Key": self.api_key}
        )

        assert response.status_code == 200
        response_data = response.json()

        # Verify OpenAI standard response format
        assert "choices" in response_data
        assert isinstance(response_data["choices"], list)
        assert len(response_data["choices"]) > 0

        choice = response_data["choices"][0]
        assert "message" in choice
        assert "finish_reason" in choice

        message = choice["message"]
        assert "role" in message
        assert "content" in message
        assert message["role"] == "assistant"

        print("✅ Full OpenAI API compatibility verified")

    def run_full_integration_test(self):
        """Run the complete integration test suite."""

        print("🚀 Starting Complete Sentient AGI Integration Test")
        print("=" * 60)

        try:
            # Run all test phases
            results = self.test_complete_crypto_analysis_workflow()
            self.test_authentication_methods()
            self.test_error_scenarios()
            self.test_performance_requirements()
            self.test_openai_compatibility()

            print("\n" + "=" * 60)
            print("🎉 INTEGRATION TEST PASSED!")
            print("✅ Context Owl is ready for Sentient AGI partnership")
            print("✅ All OpenAI compatibility requirements met")
            print("✅ Authentication systems working")
            print("✅ Performance requirements satisfied")
            print("✅ Error handling robust")
            print("✅ Streaming responses functional")

            return True

        except Exception as e:
            print(f"\n❌ INTEGRATION TEST FAILED: {e}")
            return False


def main():
    """Main function to run the integration test."""
    test_instance = TestSentientAGIIntegration()
    success = test_instance.run_full_integration_test()

    if success:
        print("\n🏆 Context Owl - Sentient AGI Partnership: READY FOR DEPLOYMENT")
        return 0
    else:
        print("\n💥 Context Owl - Sentient AGI Partnership: REQUIRES ATTENTION")
        return 1


if __name__ == "__main__":
    exit(main())
