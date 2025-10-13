"""
Tests for API retry logic with exponential backoff.

Tests rate limit (429) and overload (529) error handling in narrative discovery.
"""

import pytest
from unittest.mock import MagicMock, patch
from crypto_news_aggregator.services.narrative_themes import discover_narrative_from_article


@pytest.fixture
def sample_article():
    """Sample article for testing."""
    return {
        "_id": "test123",
        "title": "SEC Announces New Crypto Regulations",
        "description": "The SEC has announced new regulatory frameworks."
    }


@pytest.mark.asyncio
async def test_rate_limit_error_exponential_backoff(sample_article):
    """Test that rate limit errors (429) trigger exponential backoff."""
    with patch("crypto_news_aggregator.services.narrative_themes.get_llm_provider") as mock_llm, \
         patch("crypto_news_aggregator.services.narrative_themes.asyncio.sleep") as mock_sleep:
        
        # Mock LLM provider to raise rate limit error
        mock_provider = MagicMock()
        mock_provider._get_completion.side_effect = Exception("Error 429: Too Many Requests")
        mock_llm.return_value = mock_provider
        
        # Call function (should retry and fail)
        result = await discover_narrative_from_article(sample_article, max_retries=4)
        
        # Assertions
        assert result is None
        assert mock_provider._get_completion.call_count == 4  # All retries exhausted
        
        # Verify exponential backoff: 5s, 10s, 20s, 40s
        assert mock_sleep.call_count == 4  # Sleep after each failed attempt
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert sleep_calls == [5, 10, 20, 40]  # Exponential: (2^0)*5, (2^1)*5, (2^2)*5, (2^3)*5


@pytest.mark.asyncio
async def test_rate_limit_error_with_rate_limit_text(sample_article):
    """Test rate limit detection with 'rate_limit' in error message."""
    with patch("crypto_news_aggregator.services.narrative_themes.get_llm_provider") as mock_llm, \
         patch("crypto_news_aggregator.services.narrative_themes.asyncio.sleep") as mock_sleep:
        
        # Mock LLM provider to raise rate limit error
        mock_provider = MagicMock()
        mock_provider._get_completion.side_effect = Exception("rate_limit_error: API quota exceeded")
        mock_llm.return_value = mock_provider
        
        # Call function
        result = await discover_narrative_from_article(sample_article, max_retries=2)
        
        # Assertions
        assert result is None
        assert mock_provider._get_completion.call_count == 2
        
        # Verify exponential backoff was applied
        assert mock_sleep.call_count == 2
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert sleep_calls == [5, 10]  # Exponential: (2^0)*5, (2^1)*5


@pytest.mark.asyncio
async def test_overload_error_linear_backoff(sample_article):
    """Test that overload errors (529) trigger linear backoff."""
    with patch("crypto_news_aggregator.services.narrative_themes.get_llm_provider") as mock_llm, \
         patch("crypto_news_aggregator.services.narrative_themes.asyncio.sleep") as mock_sleep:
        
        # Mock LLM provider to raise overload error
        mock_provider = MagicMock()
        mock_provider._get_completion.side_effect = Exception("Error 529: Service Overloaded")
        mock_llm.return_value = mock_provider
        
        # Call function
        result = await discover_narrative_from_article(sample_article, max_retries=4)
        
        # Assertions
        assert result is None
        assert mock_provider._get_completion.call_count == 4
        
        # Verify linear backoff: 10s, 20s, 30s, 40s
        assert mock_sleep.call_count == 4
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert sleep_calls == [10, 20, 30, 40]  # Linear: 10*1, 10*2, 10*3, 10*4


@pytest.mark.asyncio
async def test_overload_error_with_overloaded_text(sample_article):
    """Test overload detection with 'overloaded' in error message."""
    with patch("crypto_news_aggregator.services.narrative_themes.get_llm_provider") as mock_llm, \
         patch("crypto_news_aggregator.services.narrative_themes.asyncio.sleep") as mock_sleep:
        
        # Mock LLM provider to raise overload error
        mock_provider = MagicMock()
        mock_provider._get_completion.side_effect = Exception("API is currently overloaded")
        mock_llm.return_value = mock_provider
        
        # Call function
        result = await discover_narrative_from_article(sample_article, max_retries=2)
        
        # Assertions
        assert result is None
        assert mock_provider._get_completion.call_count == 2
        
        # Verify linear backoff was applied
        assert mock_sleep.call_count == 2
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert sleep_calls == [10, 20]  # Linear: 10*1, 10*2


@pytest.mark.asyncio
async def test_unexpected_error_no_retry(sample_article):
    """Test that unexpected errors don't trigger retries."""
    with patch("crypto_news_aggregator.services.narrative_themes.get_llm_provider") as mock_llm, \
         patch("crypto_news_aggregator.services.narrative_themes.asyncio.sleep") as mock_sleep:
        
        # Mock LLM provider to raise unexpected error
        mock_provider = MagicMock()
        mock_provider._get_completion.side_effect = Exception("Connection timeout")
        mock_llm.return_value = mock_provider
        
        # Call function
        result = await discover_narrative_from_article(sample_article, max_retries=4)
        
        # Assertions
        assert result is None
        assert mock_provider._get_completion.call_count == 1  # No retries
        assert mock_sleep.call_count == 0  # No backoff


@pytest.mark.asyncio
async def test_rate_limit_recovery_after_retry(sample_article):
    """Test successful recovery after rate limit error."""
    with patch("crypto_news_aggregator.services.narrative_themes.get_llm_provider") as mock_llm, \
         patch("crypto_news_aggregator.services.narrative_themes.asyncio.sleep") as mock_sleep:
        
        # Mock LLM provider: fail twice, then succeed
        mock_provider = MagicMock()
        valid_response = '''{
            "actors": ["SEC", "Binance"],
            "actor_salience": {"SEC": 5, "Binance": 4},
            "nucleus_entity": "SEC",
            "actions": ["Filed charges"],
            "tensions": ["Regulation vs Innovation"],
            "narrative_summary": "The SEC is taking enforcement action against major exchanges."
        }'''
        
        mock_provider._get_completion.side_effect = [
            Exception("Error 429: Too Many Requests"),
            Exception("Error 429: Too Many Requests"),
            valid_response  # Success on third attempt
        ]
        mock_llm.return_value = mock_provider
        
        # Call function
        result = await discover_narrative_from_article(sample_article, max_retries=4)
        
        # Assertions
        assert result is not None
        assert "actors" in result
        assert result["nucleus_entity"] == "SEC"
        assert mock_provider._get_completion.call_count == 3
        assert mock_sleep.call_count == 2  # Two retries before success


@pytest.mark.asyncio
async def test_overload_recovery_after_retry(sample_article):
    """Test successful recovery after overload error."""
    with patch("crypto_news_aggregator.services.narrative_themes.get_llm_provider") as mock_llm, \
         patch("crypto_news_aggregator.services.narrative_themes.asyncio.sleep") as mock_sleep:
        
        # Mock LLM provider: fail once, then succeed
        mock_provider = MagicMock()
        valid_response = '''{
            "actors": ["SEC"],
            "actor_salience": {"SEC": 5},
            "nucleus_entity": "SEC",
            "actions": ["Announced regulations"],
            "tensions": ["Regulation vs Innovation"],
            "narrative_summary": "Regulatory framework is evolving."
        }'''
        
        mock_provider._get_completion.side_effect = [
            Exception("Error 529: Service Overloaded"),
            valid_response  # Success on second attempt
        ]
        mock_llm.return_value = mock_provider
        
        # Call function
        result = await discover_narrative_from_article(sample_article, max_retries=4)
        
        # Assertions
        assert result is not None
        assert "actors" in result
        assert mock_provider._get_completion.call_count == 2
        assert mock_sleep.call_count == 1  # One retry before success


@pytest.mark.asyncio
async def test_max_retries_increased_to_4(sample_article):
    """Test that max_retries default is now 4."""
    with patch("crypto_news_aggregator.services.narrative_themes.get_llm_provider") as mock_llm:
        
        # Mock LLM provider to always fail
        mock_provider = MagicMock()
        mock_provider._get_completion.side_effect = Exception("Error 429: Rate limited")
        mock_llm.return_value = mock_provider
        
        # Call function with default max_retries
        result = await discover_narrative_from_article(sample_article)
        
        # Should attempt 4 times (default max_retries=4)
        assert result is None
        assert mock_provider._get_completion.call_count == 4


@pytest.mark.asyncio
async def test_json_decode_error_still_retries(sample_article):
    """Test that JSON decode errors still use simple retry (not backoff)."""
    with patch("crypto_news_aggregator.services.narrative_themes.get_llm_provider") as mock_llm, \
         patch("crypto_news_aggregator.services.narrative_themes.asyncio.sleep") as mock_sleep:
        
        # Mock LLM provider to return invalid JSON
        mock_provider = MagicMock()
        mock_provider._get_completion.return_value = "not valid json at all"
        mock_llm.return_value = mock_provider
        
        # Call function
        result = await discover_narrative_from_article(sample_article, max_retries=3)
        
        # Assertions
        assert result is None
        assert mock_provider._get_completion.call_count == 3
        
        # JSON errors use 1s delay (not exponential/linear backoff)
        assert mock_sleep.call_count == 2
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert all(delay == 1 for delay in sleep_calls)  # All 1s delays
