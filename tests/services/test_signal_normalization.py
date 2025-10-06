"""
Tests for signal calculation with entity normalization.

Verifies that signal scores are calculated using canonical entity names,
preventing duplicate signals for variants like "$DOGE" and "Dogecoin".
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch

from crypto_news_aggregator.services.signal_service import (
    calculate_signal_score,
    calculate_velocity,
    calculate_source_diversity,
)


@pytest.mark.asyncio
async def test_calculate_signal_score_normalizes_entity():
    """Test that calculate_signal_score normalizes entity names."""
    
    # Mock the component functions
    with patch('crypto_news_aggregator.services.signal_service.calculate_velocity', new_callable=AsyncMock) as mock_velocity, \
         patch('crypto_news_aggregator.services.signal_service.calculate_source_diversity', new_callable=AsyncMock) as mock_diversity, \
         patch('crypto_news_aggregator.services.signal_service.calculate_sentiment_metrics', new_callable=AsyncMock) as mock_sentiment:
        
        mock_velocity.return_value = 5.0
        mock_diversity.return_value = 10
        mock_sentiment.return_value = {
            "avg": 0.5,
            "min": -1.0,
            "max": 1.0,
            "divergence": 0.3,
        }
        
        # Call with variant name
        result = await calculate_signal_score("$DOGE")
        
        # Verify it called component functions with canonical name
        mock_velocity.assert_called_once_with("Dogecoin")
        mock_diversity.assert_called_once_with("Dogecoin")
        mock_sentiment.assert_called_once_with("Dogecoin")
        
        # Verify result structure
        assert "score" in result
        assert "velocity" in result
        assert "source_count" in result
        assert "sentiment" in result


@pytest.mark.asyncio
async def test_calculate_signal_score_with_canonical_name():
    """Test that canonical names pass through unchanged."""
    
    with patch('crypto_news_aggregator.services.signal_service.calculate_velocity', new_callable=AsyncMock) as mock_velocity, \
         patch('crypto_news_aggregator.services.signal_service.calculate_source_diversity', new_callable=AsyncMock) as mock_diversity, \
         patch('crypto_news_aggregator.services.signal_service.calculate_sentiment_metrics', new_callable=AsyncMock) as mock_sentiment:
        
        mock_velocity.return_value = 3.0
        mock_diversity.return_value = 8
        mock_sentiment.return_value = {
            "avg": 0.2,
            "min": -0.5,
            "max": 0.8,
            "divergence": 0.2,
        }
        
        # Call with canonical name
        result = await calculate_signal_score("Dogecoin")
        
        # Verify it used canonical name (no change)
        mock_velocity.assert_called_once_with("Dogecoin")
        mock_diversity.assert_called_once_with("Dogecoin")
        mock_sentiment.assert_called_once_with("Dogecoin")


@pytest.mark.asyncio
async def test_multiple_variants_normalize_to_same_entity():
    """Test that different variants all normalize to the same canonical name."""
    
    variants = ["$DOGE", "DOGE", "doge", "Dogecoin", "dogecoin"]
    
    for variant in variants:
        with patch('crypto_news_aggregator.services.signal_service.calculate_velocity', new_callable=AsyncMock) as mock_velocity, \
             patch('crypto_news_aggregator.services.signal_service.calculate_source_diversity', new_callable=AsyncMock) as mock_diversity, \
             patch('crypto_news_aggregator.services.signal_service.calculate_sentiment_metrics', new_callable=AsyncMock) as mock_sentiment:
            
            mock_velocity.return_value = 1.0
            mock_diversity.return_value = 1
            mock_sentiment.return_value = {
                "avg": 0.0,
                "min": 0.0,
                "max": 0.0,
                "divergence": 0.0,
            }
            
            await calculate_signal_score(variant)
            
            # All variants should normalize to "Dogecoin"
            mock_velocity.assert_called_once_with("Dogecoin")
            mock_diversity.assert_called_once_with("Dogecoin")
            mock_sentiment.assert_called_once_with("Dogecoin")


@pytest.mark.asyncio
async def test_bitcoin_variants_normalize():
    """Test Bitcoin variant normalization."""
    
    variants = ["BTC", "$BTC", "btc", "Bitcoin", "bitcoin"]
    
    for variant in variants:
        with patch('crypto_news_aggregator.services.signal_service.calculate_velocity', new_callable=AsyncMock) as mock_velocity, \
             patch('crypto_news_aggregator.services.signal_service.calculate_source_diversity', new_callable=AsyncMock) as mock_diversity, \
             patch('crypto_news_aggregator.services.signal_service.calculate_sentiment_metrics', new_callable=AsyncMock) as mock_sentiment:
            
            mock_velocity.return_value = 1.0
            mock_diversity.return_value = 1
            mock_sentiment.return_value = {
                "avg": 0.0,
                "min": 0.0,
                "max": 0.0,
                "divergence": 0.0,
            }
            
            await calculate_signal_score(variant)
            
            # All variants should normalize to "Bitcoin"
            mock_velocity.assert_called_once_with("Bitcoin")


@pytest.mark.asyncio
async def test_unknown_entity_passes_through():
    """Test that unknown entities pass through unchanged."""
    
    with patch('crypto_news_aggregator.services.signal_service.calculate_velocity', new_callable=AsyncMock) as mock_velocity, \
         patch('crypto_news_aggregator.services.signal_service.calculate_source_diversity', new_callable=AsyncMock) as mock_diversity, \
         patch('crypto_news_aggregator.services.signal_service.calculate_sentiment_metrics', new_callable=AsyncMock) as mock_sentiment:
        
        mock_velocity.return_value = 1.0
        mock_diversity.return_value = 1
        mock_sentiment.return_value = {
            "avg": 0.0,
            "min": 0.0,
            "max": 0.0,
            "divergence": 0.0,
        }
        
        # Unknown entity should pass through unchanged
        await calculate_signal_score("UnknownCoin")
        
        mock_velocity.assert_called_once_with("UnknownCoin")
        mock_diversity.assert_called_once_with("UnknownCoin")
        mock_sentiment.assert_called_once_with("UnknownCoin")
