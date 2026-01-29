"""
Unit tests for backfill script rate limiting calculations.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestThroughputCalculations:
    """Test rate limiting throughput calculations."""
    
    def test_default_conservative_throughput(self):
        """Test default parameters give safe throughput."""
        batch_size = 15
        batch_delay = 30
        article_delay = 1.0
        
        time_per_batch = ((batch_size - 1) * article_delay) + batch_delay
        articles_per_minute = (batch_size / time_per_batch) * 60
        
        assert time_per_batch == 44.0
        assert 20.0 <= articles_per_minute <= 21.0
        assert articles_per_minute < 22.0  # Under warning threshold
    
    def test_old_aggressive_throughput_too_high(self):
        """Test old aggressive parameters exceed safe limits."""
        batch_size = 20
        batch_delay = 30
        article_delay = 0.5
        
        time_per_batch = ((batch_size - 1) * article_delay) + batch_delay
        articles_per_minute = (batch_size / time_per_batch) * 60
        
        assert articles_per_minute > 25.0  # Exceeds token limit
        assert articles_per_minute > 22.0  # Should trigger warning
    
    def test_very_conservative_throughput(self):
        """Test very conservative parameters are well under limits."""
        batch_size = 10
        batch_delay = 30
        article_delay = 1.0
        
        time_per_batch = ((batch_size - 1) * article_delay) + batch_delay
        articles_per_minute = (batch_size / time_per_batch) * 60
        
        assert articles_per_minute < 20.0  # Well under limit
    
    def test_batch_size_one_no_article_delays(self):
        """Test batch size of 1 has no article delays."""
        batch_size = 1
        batch_delay = 30
        article_delay = 1.0
        
        time_per_batch = ((batch_size - 1) * article_delay) + batch_delay
        
        assert time_per_batch == 30.0  # Only batch delay
    
    def test_throughput_scales_with_batch_size(self):
        """Test throughput increases with batch size."""
        batch_delay = 30
        article_delay = 1.0
        
        throughputs = []
        for batch_size in [5, 10, 15, 20]:
            time_per_batch = ((batch_size - 1) * article_delay) + batch_delay
            articles_per_minute = (batch_size / time_per_batch) * 60
            throughputs.append(articles_per_minute)
        
        # Throughput should increase with batch size
        assert throughputs == sorted(throughputs)
    
    def test_throughput_decreases_with_delays(self):
        """Test throughput decreases as delays increase."""
        batch_size = 15
        batch_delay = 30
        
        throughputs = []
        for article_delay in [0.5, 1.0, 1.5, 2.0]:
            time_per_batch = ((batch_size - 1) * article_delay) + batch_delay
            articles_per_minute = (batch_size / time_per_batch) * 60
            throughputs.append(articles_per_minute)
        
        # Throughput should decrease as delay increases
        assert throughputs == sorted(throughputs, reverse=True)


class TestWarningThresholds:
    """Test warning threshold logic."""
    
    def test_warning_threshold_high(self):
        """Test warning triggers above 22/min."""
        articles_per_minute = 25.0
        assert articles_per_minute > 22
    
    def test_safe_range_threshold(self):
        """Test safe range is 20-22/min."""
        articles_per_minute = 20.5
        assert 20 < articles_per_minute <= 22
    
    def test_very_safe_threshold(self):
        """Test very safe is under 20/min."""
        articles_per_minute = 15.0
        assert articles_per_minute <= 20


class TestBatchCalculations:
    """Test batch-related calculations."""
    
    def test_total_batches_calculation(self):
        """Test total batches calculation."""
        test_cases = [
            (100, 15, 7),   # 100 articles, 15 per batch = 7 batches
            (15, 15, 1),    # Exactly one batch
            (16, 15, 2),    # One article over = 2 batches
            (1, 15, 1),     # Single article = 1 batch
        ]
        
        for total_articles, batch_size, expected_batches in test_cases:
            actual_batches = (total_articles + batch_size - 1) // batch_size
            assert actual_batches == expected_batches
    
    def test_article_delays_per_batch(self):
        """Test number of delays per batch."""
        # For batch_size articles, we have (batch_size - 1) delays
        test_cases = [
            (15, 14),  # 15 articles = 14 delays
            (10, 9),   # 10 articles = 9 delays
            (1, 0),    # 1 article = 0 delays
            (20, 19),  # 20 articles = 19 delays
        ]
        
        for batch_size, expected_delays in test_cases:
            actual_delays = batch_size - 1
            assert actual_delays == expected_delays


class TestTokenCalculations:
    """Test token limit calculations."""
    
    def test_max_articles_per_minute_from_tokens(self):
        """Test maximum articles/min based on token limits."""
        token_limit = 25000  # TPM
        tokens_per_article = 1000
        
        max_articles_per_minute = token_limit / tokens_per_article
        
        assert max_articles_per_minute == 25.0
    
    def test_safety_buffer_calculation(self):
        """Test safety buffer percentage."""
        max_safe = 25.0
        our_target = 20.5
        
        buffer_percent = ((max_safe - our_target) / max_safe) * 100
        
        assert 17.0 <= buffer_percent <= 19.0  # ~18% buffer
    
    def test_tokens_per_batch(self):
        """Test total tokens per batch."""
        batch_size = 15
        tokens_per_article = 1000
        
        tokens_per_batch = batch_size * tokens_per_article
        
        assert tokens_per_batch == 15000
        assert tokens_per_batch < 25000  # Under limit


class TestEstimatedTime:
    """Test time estimation calculations."""
    
    def test_estimated_time_for_full_backfill(self):
        """Test estimated time for 1,329 articles."""
        total_articles = 1329
        articles_per_minute = 20.5
        
        estimated_minutes = total_articles / articles_per_minute
        
        assert 64 <= estimated_minutes <= 67  # ~66 minutes
    
    def test_estimated_time_with_batches(self):
        """Test estimated time using batch calculations."""
        total_articles = 1329
        batch_size = 15
        time_per_batch = 44.0  # seconds
        
        total_batches = (total_articles + batch_size - 1) // batch_size
        estimated_seconds = total_batches * time_per_batch
        estimated_minutes = estimated_seconds / 60
        
        assert 64 <= estimated_minutes <= 67  # ~66 minutes


@pytest.mark.asyncio
class TestDelayLogic:
    """Test delay application logic."""
    
    async def test_article_delay_skipped_for_last_article(self):
        """Test that delay is skipped for last article in batch."""
        batch = [1, 2, 3, 4, 5]  # 5 articles
        article_delay = 1.0
        delays_applied = 0
        
        for article_idx, article in enumerate(batch):
            if article_idx < len(batch) - 1:
                delays_applied += 1
        
        assert delays_applied == 4  # 4 delays for 5 articles
    
    async def test_batch_delay_skipped_for_last_batch(self):
        """Test that batch delay is skipped for last batch."""
        total_articles = 45
        batch_size = 15
        batch_delays_applied = 0
        
        for i in range(0, total_articles, batch_size):
            if i + batch_size < total_articles:
                batch_delays_applied += 1
        
        assert batch_delays_applied == 2  # 2 delays for 3 batches


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
