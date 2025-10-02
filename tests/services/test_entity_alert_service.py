"""
Tests for entity alert service.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from crypto_news_aggregator.services.entity_alert_service import (
    check_new_entity_alert,
    check_velocity_spike_alert,
    check_sentiment_divergence_alert,
    detect_alerts
)


class TestNewEntityAlert:
    """Tests for new entity alert detection."""
    
    def test_new_entity_alert_triggered(self):
        """Test that new entity alert is triggered for recent entity."""
        signal_data = {
            "entity": "TEST_TOKEN",
            "entity_type": "ticker",
            "score": 7.5,
            "first_seen": datetime.now(timezone.utc) - timedelta(hours=3),
            "source_count": 5,
            "velocity": 12.0
        }
        
        alert = check_new_entity_alert("TEST_TOKEN", signal_data)
        
        assert alert is not None
        assert alert["type"] == "NEW_ENTITY"
        assert alert["entity"] == "TEST_TOKEN"
        assert alert["severity"] == "high"
        assert alert["signal_score"] == 7.5
        assert alert["details"]["source_count"] == 5
    
    def test_new_entity_alert_too_old(self):
        """Test that alert is not triggered for old entity."""
        signal_data = {
            "entity": "OLD_TOKEN",
            "entity_type": "ticker",
            "score": 7.5,
            "first_seen": datetime.now(timezone.utc) - timedelta(hours=10),
            "source_count": 5,
            "velocity": 12.0
        }
        
        alert = check_new_entity_alert("OLD_TOKEN", signal_data)
        
        assert alert is None
    
    def test_new_entity_alert_not_enough_sources(self):
        """Test that alert is not triggered with too few sources."""
        signal_data = {
            "entity": "LOW_SOURCE_TOKEN",
            "entity_type": "ticker",
            "score": 7.5,
            "first_seen": datetime.now(timezone.utc) - timedelta(hours=2),
            "source_count": 2,
            "velocity": 12.0
        }
        
        alert = check_new_entity_alert("LOW_SOURCE_TOKEN", signal_data)
        
        assert alert is None
    
    def test_new_entity_alert_no_first_seen(self):
        """Test that alert is not triggered without first_seen."""
        signal_data = {
            "entity": "NO_DATE_TOKEN",
            "entity_type": "ticker",
            "score": 7.5,
            "source_count": 5,
            "velocity": 12.0
        }
        
        alert = check_new_entity_alert("NO_DATE_TOKEN", signal_data)
        
        assert alert is None


class TestVelocitySpikeAlert:
    """Tests for velocity spike alert detection."""
    
    def test_velocity_spike_no_baseline(self):
        """Test velocity spike with no baseline (absolute threshold)."""
        signal_data = {
            "entity": "SPIKE_TOKEN",
            "entity_type": "ticker",
            "score": 6.0,
            "velocity": 15.0
        }
        
        alert = check_velocity_spike_alert("SPIKE_TOKEN", signal_data)
        
        assert alert is not None
        assert alert["type"] == "VELOCITY_SPIKE"
        assert alert["severity"] == "medium"
        assert alert["details"]["velocity"] == 15.0
        assert alert["details"]["baseline"] is None
    
    def test_velocity_spike_with_baseline(self):
        """Test velocity spike with baseline (5x threshold)."""
        signal_data = {
            "entity": "SPIKE_TOKEN",
            "entity_type": "ticker",
            "score": 6.0,
            "velocity": 25.0,
            "baseline_velocity": 4.0
        }
        
        alert = check_velocity_spike_alert("SPIKE_TOKEN", signal_data)
        
        assert alert is not None
        assert alert["type"] == "VELOCITY_SPIKE"
        assert alert["details"]["velocity"] == 25.0
        assert alert["details"]["baseline"] == 4.0
        assert alert["details"]["spike_multiplier"] == 6.25
    
    def test_velocity_spike_below_threshold(self):
        """Test that no alert is triggered below threshold."""
        signal_data = {
            "entity": "LOW_VELOCITY_TOKEN",
            "entity_type": "ticker",
            "score": 6.0,
            "velocity": 8.0
        }
        
        alert = check_velocity_spike_alert("LOW_VELOCITY_TOKEN", signal_data)
        
        assert alert is None
    
    def test_velocity_spike_baseline_not_exceeded(self):
        """Test that no alert is triggered when baseline not exceeded."""
        signal_data = {
            "entity": "NORMAL_TOKEN",
            "entity_type": "ticker",
            "score": 6.0,
            "velocity": 12.0,
            "baseline_velocity": 10.0
        }
        
        alert = check_velocity_spike_alert("NORMAL_TOKEN", signal_data)
        
        assert alert is None


class TestSentimentDivergenceAlert:
    """Tests for sentiment divergence alert detection."""
    
    def test_sentiment_divergence_triggered(self):
        """Test that sentiment divergence alert is triggered."""
        signal_data = {
            "entity": "DIVERGENT_TOKEN",
            "entity_type": "ticker",
            "score": 6.5,
            "sentiment": {
                "divergence": 0.75,
                "avg": 0.2,
                "positive_count": 3,
                "negative_count": 4
            }
        }
        
        alert = check_sentiment_divergence_alert("DIVERGENT_TOKEN", signal_data)
        
        assert alert is not None
        assert alert["type"] == "SENTIMENT_DIVERGENCE"
        assert alert["severity"] == "medium"
        assert alert["details"]["divergence"] == 0.75
    
    def test_sentiment_divergence_below_threshold(self):
        """Test that no alert is triggered below threshold."""
        signal_data = {
            "entity": "NORMAL_TOKEN",
            "entity_type": "ticker",
            "score": 6.5,
            "sentiment": {
                "divergence": 0.4,
                "avg": 0.5
            }
        }
        
        alert = check_sentiment_divergence_alert("NORMAL_TOKEN", signal_data)
        
        assert alert is None
    
    def test_sentiment_divergence_no_sentiment_data(self):
        """Test that no alert is triggered without sentiment data."""
        signal_data = {
            "entity": "NO_SENTIMENT_TOKEN",
            "entity_type": "ticker",
            "score": 6.5
        }
        
        alert = check_sentiment_divergence_alert("NO_SENTIMENT_TOKEN", signal_data)
        
        assert alert is None


@pytest.mark.asyncio
class TestDetectAlerts:
    """Tests for the main detect_alerts function."""
    
    async def test_detect_alerts_success(self):
        """Test successful alert detection."""
        mock_entities = [
            {
                "entity": "NEW_TOKEN",
                "entity_type": "ticker",
                "score": 8.0,
                "first_seen": datetime.now(timezone.utc) - timedelta(hours=2),
                "source_count": 5,
                "velocity": 15.0,
                "sentiment": {"divergence": 0.3}
            },
            {
                "entity": "SPIKE_TOKEN",
                "entity_type": "project",
                "score": 7.0,
                "first_seen": datetime.now(timezone.utc) - timedelta(days=2),
                "source_count": 3,
                "velocity": 20.0,
                "sentiment": {"divergence": 0.2}
            }
        ]
        
        with patch("crypto_news_aggregator.services.entity_alert_service.get_trending_entities", new_callable=AsyncMock) as mock_get_trending:
            with patch("crypto_news_aggregator.services.entity_alert_service.alert_exists", new_callable=AsyncMock) as mock_alert_exists:
                with patch("crypto_news_aggregator.services.entity_alert_service.create_alert", new_callable=AsyncMock) as mock_create_alert:
                    mock_get_trending.return_value = mock_entities
                    mock_alert_exists.return_value = False
                    mock_create_alert.return_value = "alert_id_123"
                    
                    alerts = await detect_alerts()
                    
                    # Should trigger NEW_ENTITY for NEW_TOKEN and VELOCITY_SPIKE for both
                    assert len(alerts) >= 2
                    assert any(a["type"] == "NEW_ENTITY" for a in alerts)
                    assert any(a["type"] == "VELOCITY_SPIKE" for a in alerts)
    
    async def test_detect_alerts_no_trending_entities(self):
        """Test detect_alerts with no trending entities."""
        with patch("crypto_news_aggregator.services.entity_alert_service.get_trending_entities", new_callable=AsyncMock) as mock_get_trending:
            mock_get_trending.return_value = []
            
            alerts = await detect_alerts()
            
            assert alerts == []
    
    async def test_detect_alerts_duplicate_prevention(self):
        """Test that duplicate alerts are not created."""
        mock_entities = [
            {
                "entity": "TEST_TOKEN",
                "entity_type": "ticker",
                "score": 8.0,
                "first_seen": datetime.now(timezone.utc) - timedelta(hours=2),
                "source_count": 5,
                "velocity": 15.0,
                "sentiment": {"divergence": 0.3}
            }
        ]
        
        with patch("crypto_news_aggregator.services.entity_alert_service.get_trending_entities", new_callable=AsyncMock) as mock_get_trending:
            with patch("crypto_news_aggregator.services.entity_alert_service.alert_exists", new_callable=AsyncMock) as mock_alert_exists:
                with patch("crypto_news_aggregator.services.entity_alert_service.create_alert", new_callable=AsyncMock) as mock_create_alert:
                    mock_get_trending.return_value = mock_entities
                    mock_alert_exists.return_value = True  # Alert already exists
                    
                    alerts = await detect_alerts()
                    
                    # No alerts should be created
                    assert alerts == []
                    mock_create_alert.assert_not_called()
