"""Test velocity calculation fix."""

from datetime import datetime, timedelta, timezone
import pytest
from crypto_news_aggregator.services.narrative_service import calculate_recent_velocity


class TestVelocityCalculation:
    """Test suite for velocity calculation bug fix."""
    
    def test_velocity_with_3_articles_from_1_5_days_ago(self):
        """Test that 3 articles from 1.5 days ago = 0.43 articles/day, not 2.0."""
        now = datetime.now(timezone.utc)
        article_dates = [now - timedelta(days=1.5)] * 3
        
        velocity = calculate_recent_velocity(article_dates, lookback_days=7)
        
        # Should be 3/7 = 0.43, NOT 3/1.5 = 2.0
        assert abs(velocity - 0.43) < 0.01, f"Expected ~0.43, got {velocity}"
    
    def test_velocity_with_5_articles_from_2_days_ago(self):
        """Test that 5 articles from 2 days ago = 0.71 articles/day, not 2.5."""
        now = datetime.now(timezone.utc)
        article_dates = [now - timedelta(days=2)] * 5
        
        velocity = calculate_recent_velocity(article_dates, lookback_days=7)
        
        # Should be 5/7 = 0.71, NOT 5/2 = 2.5
        assert abs(velocity - 0.71) < 0.01, f"Expected ~0.71, got {velocity}"
    
    def test_velocity_with_5_articles_showing_10_per_day_bug(self):
        """Test the reported bug: 5 articles showing +10 articles/day."""
        now = datetime.now(timezone.utc)
        # If velocity is 10 for 5 articles, it means dividing by 0.5 days
        # So articles must be from ~12 hours ago
        article_dates = [now - timedelta(hours=12)] * 5
        
        velocity = calculate_recent_velocity(article_dates, lookback_days=7)
        
        # Should be 5/7 = 0.71, NOT 5/0.5 = 10.0
        assert abs(velocity - 0.71) < 0.01, f"Expected ~0.71, got {velocity}"
        assert velocity < 1.0, f"Velocity should be less than 1.0, got {velocity}"
    
    def test_velocity_with_7_articles_over_7_days(self):
        """Test that 7 articles spread over 7 days = 1.0 articles/day."""
        now = datetime.now(timezone.utc)
        article_dates = [now - timedelta(days=i) for i in range(7)]
        
        velocity = calculate_recent_velocity(article_dates, lookback_days=7)
        
        assert abs(velocity - 1.0) < 0.01, f"Expected 1.0, got {velocity}"
    
    def test_velocity_with_14_articles_in_last_3_days(self):
        """Test that 14 articles from last 3 days = 2.0 articles/day."""
        now = datetime.now(timezone.utc)
        article_dates = [now - timedelta(days=i % 3) for i in range(14)]
        
        velocity = calculate_recent_velocity(article_dates, lookback_days=7)
        
        assert abs(velocity - 2.0) < 0.01, f"Expected 2.0, got {velocity}"
    
    def test_velocity_with_no_articles(self):
        """Test that empty article list returns 0.0."""
        velocity = calculate_recent_velocity([], lookback_days=7)
        assert velocity == 0.0
    
    def test_velocity_with_articles_outside_window(self):
        """Test that articles older than 7 days are excluded."""
        now = datetime.now(timezone.utc)
        # All articles are 10 days old (outside the 7-day window)
        article_dates = [now - timedelta(days=10)] * 5
        
        velocity = calculate_recent_velocity(article_dates, lookback_days=7)
        
        # Should be 0 since no articles are within the 7-day window
        assert velocity == 0.0
    
    def test_velocity_with_mixed_dates(self):
        """Test velocity with articles both inside and outside the window."""
        now = datetime.now(timezone.utc)
        article_dates = [
            now - timedelta(days=1),   # Inside window
            now - timedelta(days=3),   # Inside window
            now - timedelta(days=5),   # Inside window
            now - timedelta(days=10),  # Outside window
            now - timedelta(days=15),  # Outside window
        ]
        
        velocity = calculate_recent_velocity(article_dates, lookback_days=7)
        
        # Should count only 3 articles (the ones within 7 days)
        # 3/7 = 0.43
        assert abs(velocity - 0.43) < 0.01, f"Expected ~0.43, got {velocity}"
    
    def test_velocity_always_divides_by_lookback_days(self):
        """Verify that velocity ALWAYS divides by lookback_days, not article span."""
        now = datetime.now(timezone.utc)
        
        # Test with different lookback periods
        article_dates = [now - timedelta(days=1)] * 10
        
        velocity_7 = calculate_recent_velocity(article_dates, lookback_days=7)
        velocity_14 = calculate_recent_velocity(article_dates, lookback_days=14)
        velocity_30 = calculate_recent_velocity(article_dates, lookback_days=30)
        
        # All should have same article count (10) but different denominators
        assert abs(velocity_7 - 10/7) < 0.01
        assert abs(velocity_14 - 10/14) < 0.01
        assert abs(velocity_30 - 10/30) < 0.01
