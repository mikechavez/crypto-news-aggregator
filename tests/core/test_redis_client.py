import pytest
from unittest.mock import patch, MagicMock
from src.crypto_news_aggregator.core.redis_rest_client import RedisRESTClient


def test_redis_client_initialization():
    """Test that the Redis client initializes with correct settings."""
    client = RedisRESTClient(
        base_url="https://test-redis.upstash.io", token="test-token-123"
    )

    assert client.base_url == "https://test-redis.upstash.io"
    assert client.token == "test-token-123"
    assert "Authorization" in client.headers
    assert "Content-Type" in client.headers


@patch("requests.request")
def test_redis_client_ping(mock_request):
    """Test the ping method of Redis client."""
    # Setup mock response
    mock_response = MagicMock()
    mock_response.json.return_value = {"result": "PONG"}
    mock_request.return_value = mock_response

    # Test
    client = RedisRESTClient("https://test-redis.upstash.io", "test-token")
    result = client.ping()

    # Verify
    assert result is True
    mock_request.assert_called_once_with(
        "GET",
        "https://test-redis.upstash.io/ping",
        headers={
            "Authorization": "Bearer test-token",
            "Content-Type": "application/json",
        },
    )


@patch("requests.request")
def test_redis_client_set_get(mock_request):
    """Test set and get operations of Redis client."""
    # Setup mock responses
    mock_set_response = MagicMock()
    mock_set_response.json.return_value = {"result": "OK"}

    mock_get_response = MagicMock()
    mock_get_response.json.return_value = {"result": "test-value"}

    mock_request.side_effect = [mock_set_response, mock_get_response]

    # Test
    client = RedisRESTClient("https://test-redis.upstash.io", "test-token")
    set_result = client.set("test-key", "test-value")
    get_result = client.get("test-key")

    # Verify
    assert set_result is True
    assert get_result == "test-value"

    # Verify set was called correctly
    set_call = mock_request.call_args_list[0]
    assert set_call[0][0] == "POST"
    assert set_call[0][1] == "https://test-redis.upstash.io/set/test-key/test-value"

    # Verify get was called correctly
    get_call = mock_request.call_args_list[1]
    assert get_call[0][0] == "GET"
    assert get_call[0][1] == "https://test-redis.upstash.io/get/test-key"


@patch("requests.request")
def test_redis_client_delete(mock_request):
    """Test delete operation of Redis client."""
    # Setup mock response
    mock_response = MagicMock()
    mock_response.json.return_value = {"result": 1}  # 1 key deleted
    mock_request.return_value = mock_response

    # Test
    client = RedisRESTClient("https://test-redis.upstash.io", "test-token")
    result = client.delete("test-key")

    # Verify
    assert result == 1
    mock_request.assert_called_once_with(
        "POST",
        "https://test-redis.upstash.io/del/test-key",
        headers={
            "Authorization": "Bearer test-token",
            "Content-Type": "application/json",
        },
    )


def test_redis_client_singleton():
    """Test that the redis_client is a singleton instance."""
    from src.crypto_news_aggregator.core.redis_rest_client import redis_client

    # First import
    client1 = redis_client

    # Re-import to get the same instance
    from src.crypto_news_aggregator.core.redis_rest_client import (
        redis_client as client2,
    )

    assert client1 is client2
