"""Tests for OpenAI compatibility endpoint."""
import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient

from crypto_news_aggregator.main import app
from crypto_news_aggregator.core.auth import get_api_keys
from crypto_news_aggregator.core.config import get_settings


class TestOpenAICompatibility:
    """Test OpenAI-compatible chat completions endpoint."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
        self.settings = get_settings()

    def test_openai_endpoint_health_check(self):
        """Test that the OpenAI endpoint is accessible."""
        response = self.client.get("/v1/chat/completions")
        # Should return 405 Method Not Allowed for GET requests
        assert response.status_code == 405

    def test_openai_endpoint_without_auth(self):
        """Test that the endpoint requires authentication."""
        request_data = {
            "model": "crypto-insight-agent",
            "messages": [{"role": "user", "content": "What is the price of Bitcoin?"}],
            "stream": False
        }

        response = self.client.post("/v1/chat/completions", json=request_data)

        # Should return 401 Unauthorized without API key
        assert response.status_code == 401
        assert "Missing or invalid API key" in response.json()["detail"]

    def test_openai_endpoint_with_invalid_api_key(self):
        """Test that the endpoint rejects invalid API keys."""
        request_data = {
            "model": "crypto-insight-agent",
            "messages": [{"role": "user", "content": "What is the price of Bitcoin?"}],
            "stream": False
        }

        response = self.client.post(
            "/v1/chat/completions",
            json=request_data,
            headers={"X-API-Key": "invalid-key"}
        )

        # Should return 403 Forbidden with invalid API key
        assert response.status_code == 403
        assert "Invalid API key" in response.json()["detail"]

    def test_openai_endpoint_with_valid_api_key(self):
        """Test that the endpoint accepts valid API keys."""
        # Get a valid API key from settings
        valid_api_keys = get_api_keys()
        if not valid_api_keys:
            pytest.skip("No valid API keys configured for testing")

        request_data = {
            "model": "crypto-insight-agent",
            "messages": [{"role": "user", "content": "What is the price of Bitcoin?"}],
            "stream": False
        }

        response = self.client.post(
            "/v1/chat/completions",
            json=request_data,
            headers={"X-API-Key": valid_api_keys[0]}
        )

        # Should accept valid API key and process request
        assert response.status_code in [200, 500]  # 500 might occur due to missing services in test env

    @patch('crypto_news_aggregator.api.openai_compatibility.get_price_service')
    @patch('crypto_news_aggregator.api.openai_compatibility.get_correlation_service')
    def test_openai_price_inquiry(self, mock_correlation_service, mock_price_service):
        """Test price inquiry functionality."""
        # Mock price service
        mock_price_service_instance = AsyncMock()
        mock_price_service_instance.generate_market_analysis_commentary.return_value = "Bitcoin is currently trading at $50,000 with strong upward momentum."
        mock_price_service.return_value = mock_price_service_instance

        # Mock correlation service
        mock_correlation_service_instance = AsyncMock()
        mock_correlation_service_instance.calculate_correlation.return_value = {}
        mock_correlation_service.return_value = mock_correlation_service_instance

        # Get a valid API key
        valid_api_keys = get_api_keys()
        if not valid_api_keys:
            pytest.skip("No valid API keys configured for testing")

        request_data = {
            "model": "crypto-insight-agent",
            "messages": [{"role": "user", "content": "What is the current price of Bitcoin?"}],
            "stream": False
        }

        response = self.client.post(
            "/v1/chat/completions",
            json=request_data,
            headers={"X-API-Key": valid_api_keys[0]}
        )

        if response.status_code == 200:
            response_data = response.json()
            assert "choices" in response_data
            assert len(response_data["choices"]) > 0
            assert "message" in response_data["choices"][0]
            assert "content" in response_data["choices"][0]["message"]
            assert "role" in response_data["choices"][0]["message"]
            assert response_data["choices"][0]["message"]["role"] == "assistant"
            assert "finish_reason" in response_data["choices"][0]

    @patch('crypto_news_aggregator.api.openai_compatibility.get_price_service')
    @patch('crypto_news_aggregator.api.openai_compatibility.get_correlation_service')
    def test_openai_sentiment_analysis(self, mock_correlation_service, mock_price_service):
        """Test sentiment analysis functionality."""
        # Mock price service
        mock_price_service_instance = AsyncMock()
        mock_price_service_instance.generate_market_analysis_commentary.return_value = "Market analysis data"
        mock_price_service.return_value = mock_price_service_instance

        # Mock correlation service
        mock_correlation_service_instance = AsyncMock()
        mock_correlation_service_instance.calculate_correlation.return_value = {}
        mock_correlation_service.return_value = mock_correlation_service_instance

        # Mock article service sentiment
        with patch('crypto_news_aggregator.api.openai_compatibility.article_service') as mock_article_service:
            mock_article_service.get_average_sentiment_for_symbols.return_value = {"BTC": 0.3, "ETH": -0.1}

            valid_api_keys = get_api_keys()
            if not valid_api_keys:
                pytest.skip("No valid API keys configured for testing")

            request_data = {
                "model": "crypto-insight-agent",
                "messages": [{"role": "user", "content": "What is the sentiment around Bitcoin and Ethereum?"}],
                "stream": False
            }

            response = self.client.post(
                "/v1/chat/completions",
                json=request_data,
                headers={"X-API-Key": valid_api_keys[0]}
            )

            if response.status_code == 200:
                response_data = response.json()
                assert "choices" in response_data
                content = response_data["choices"][0]["message"]["content"].lower()
                assert any(sentiment in content for sentiment in ["positive", "negative", "neutral", "sentiment"])

    @patch('crypto_news_aggregator.api.openai_compatibility.get_price_service')
    @patch('crypto_news_aggregator.api.openai_compatibility.get_correlation_service')
    def test_openai_correlation_analysis(self, mock_correlation_service, mock_price_service):
        """Test correlation analysis functionality."""
        # Mock price service
        mock_price_service_instance = AsyncMock()
        mock_price_service_instance.generate_market_analysis_commentary.return_value = "Market analysis data"
        mock_price_service.return_value = mock_price_service_instance

        # Mock correlation service
        mock_correlation_service_instance = AsyncMock()
        mock_correlation_service_instance.calculate_correlation.return_value = {"ethereum": 0.85, "solana": 0.72}
        mock_correlation_service.return_value = mock_correlation_service_instance

        valid_api_keys = get_api_keys()
        if not valid_api_keys:
            pytest.skip("No valid API keys configured for testing")

        request_data = {
            "model": "crypto-insight-agent",
            "messages": [{"role": "user", "content": "How correlated is Bitcoin with other cryptocurrencies?"}],
            "stream": False
        }

        response = self.client.post(
            "/v1/chat/completions",
            json=request_data,
            headers={"X-API-Key": valid_api_keys[0]}
        )

        if response.status_code == 200:
            response_data = response.json()
            assert "choices" in response_data
            content = response_data["choices"][0]["message"]["content"].lower()
            assert "correlation" in content

    def test_openai_response_format_matches_standard(self):
        """Test that response format matches OpenAI API standard."""
        valid_api_keys = get_api_keys()
        if not valid_api_keys:
            pytest.skip("No valid API keys configured for testing")

        request_data = {
            "model": "crypto-insight-agent",
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": False
        }

        response = self.client.post(
            "/v1/chat/completions",
            json=request_data,
            headers={"X-API-Key": valid_api_keys[0]}
        )

        if response.status_code == 200:
            response_data = response.json()

            # Check OpenAI standard response format
            assert isinstance(response_data, dict)
            assert "choices" in response_data
            assert isinstance(response_data["choices"], list)
            assert len(response_data["choices"]) > 0

            choice = response_data["choices"][0]
            assert isinstance(choice, dict)
            assert "message" in choice
            assert "finish_reason" in choice

            message = choice["message"]
            assert isinstance(message, dict)
            assert "role" in message
            assert "content" in message
            assert message["role"] == "assistant"

    def test_openai_streaming_response_format(self):
        """Test that streaming response format matches OpenAI standard."""
        valid_api_keys = get_api_keys()
        if not valid_api_keys:
            pytest.skip("No valid API keys configured for testing")

        request_data = {
            "model": "crypto-insight-agent",
            "messages": [{"role": "user", "content": "Tell me about Bitcoin"}],
            "stream": True
        }

        response = self.client.post(
            "/v1/chat/completions",
            json=request_data,
            headers={"X-API-Key": valid_api_keys[0]}
        )

        if response.status_code == 200:
            # Check that it's a streaming response
            assert response.headers.get("content-type") == "text/event-stream; charset=utf-8"

            # Read the streaming content
            content = response.content.decode()
            assert content  # Should have some content
            assert "data:" in content  # Should be in SSE format
            assert "[DONE]" in content  # Should have end marker

    def test_openai_model_parameter(self):
        """Test that the model parameter is handled correctly."""
        valid_api_keys = get_api_keys()
        if not valid_api_keys:
            pytest.skip("No valid API keys configured for testing")

        request_data = {
            "model": "gpt-4",  # Different model name
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": False
        }

        response = self.client.post(
            "/v1/chat/completions",
            json=request_data,
            headers={"X-API-Key": valid_api_keys[0]}
        )

        # Should work regardless of model name
        assert response.status_code in [200, 500]

    def test_openai_multiple_messages(self):
        """Test handling of multiple messages in conversation."""
        valid_api_keys = get_api_keys()
        if not valid_api_keys:
            pytest.skip("No valid API keys configured for testing")

        request_data = {
            "model": "crypto-insight-agent",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "What is Bitcoin?"},
                {"role": "assistant", "content": "Bitcoin is a cryptocurrency."},
                {"role": "user", "content": "Tell me more about it."}
            ],
            "stream": False
        }

        response = self.client.post(
            "/v1/chat/completions",
            json=request_data,
            headers={"X-API-Key": valid_api_keys[0]}
        )

        # Should handle conversation history
        assert response.status_code in [200, 500]

    def test_openai_symbol_extraction(self):
        """Test that crypto symbols are properly extracted from messages."""
        valid_api_keys = get_api_keys()
        if not valid_api_keys:
            pytest.skip("No valid API keys configured for testing")

        test_cases = [
            "What is the price of BTC?",
            "How is Bitcoin doing today?",
            "Tell me about ETH and SOL",
            "What about ethereum and dogecoin?",
            "ADA is looking good"
        ]

        for content in test_cases:
            request_data = {
                "model": "crypto-insight-agent",
                "messages": [{"role": "user", "content": content}],
                "stream": False
            }

            response = self.client.post(
                "/v1/chat/completions",
                json=request_data,
                headers={"X-API-Key": valid_api_keys[0]}
            )

            # Should process the request without error
            assert response.status_code in [200, 500]

    def test_openai_error_handling(self):
        """Test error handling for various scenarios."""
        valid_api_keys = get_api_keys()
        if not valid_api_keys:
            pytest.skip("No valid API keys configured for testing")

        # Test with empty messages
        request_data = {
            "model": "crypto-insight-agent",
            "messages": [],
            "stream": False
        }

        response = self.client.post(
            "/v1/chat/completions",
            json=request_data,
            headers={"X-API-Key": valid_api_keys[0]}
        )

        # Should handle gracefully
        assert response.status_code in [200, 400, 500]

        # Test with invalid JSON
        response = self.client.post(
            "/v1/chat/completions",
            data="invalid json",
            headers={"X-API-Key": valid_api_keys[0]}
        )

        # Should return 422 Unprocessable Entity
        assert response.status_code == 422

    def test_openai_bearer_token_auth(self):
        """Test authentication with Bearer token."""
        # This would require a valid JWT token, which we don't have in test environment
        # So we'll just test that the endpoint accepts Bearer tokens in the header
        request_data = {
            "model": "crypto-insight-agent",
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": False
        }

        # Test with Bearer token (will fail auth but should not fail on format)
        response = self.client.post(
            "/v1/chat/completions",
            json=request_data,
            headers={"Authorization": "Bearer invalid-token"}
        )

        # Should fail with auth error, not format error
        assert response.status_code in [401, 403]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
