"""
Tests for lifecycle history tracking in narrative service.
"""

import pytest
from datetime import datetime, timezone
from src.crypto_news_aggregator.services.narrative_service import update_lifecycle_history


def test_update_lifecycle_history_empty_narrative():
    """Test lifecycle history initialization for new narrative."""
    narrative = {}
    lifecycle_state = 'emerging'
    article_count = 3
    mention_velocity = 1.2
    
    history = update_lifecycle_history(narrative, lifecycle_state, article_count, mention_velocity)
    
    assert len(history) == 1
    assert history[0]['state'] == 'emerging'
    assert history[0]['article_count'] == 3
    assert history[0]['mention_velocity'] == 1.2
    assert 'timestamp' in history[0]
    assert isinstance(history[0]['timestamp'], datetime)


def test_update_lifecycle_history_no_change():
    """Test that no new entry is added when state hasn't changed."""
    existing_timestamp = datetime.now(timezone.utc)
    narrative = {
        'lifecycle_history': [
            {
                'state': 'emerging',
                'timestamp': existing_timestamp,
                'article_count': 3,
                'mention_velocity': 1.2
            }
        ]
    }
    
    lifecycle_state = 'emerging'  # Same state
    article_count = 4
    mention_velocity = 1.5
    
    history = update_lifecycle_history(narrative, lifecycle_state, article_count, mention_velocity)
    
    # Should not add new entry since state hasn't changed
    assert len(history) == 1
    assert history[0]['state'] == 'emerging'
    assert history[0]['timestamp'] == existing_timestamp


def test_update_lifecycle_history_state_transition():
    """Test that new entry is added when state changes."""
    existing_timestamp = datetime.now(timezone.utc)
    narrative = {
        'lifecycle_history': [
            {
                'state': 'emerging',
                'timestamp': existing_timestamp,
                'article_count': 3,
                'mention_velocity': 1.2
            }
        ]
    }
    
    lifecycle_state = 'rising'  # State changed
    article_count = 5
    mention_velocity = 2.3
    
    history = update_lifecycle_history(narrative, lifecycle_state, article_count, mention_velocity)
    
    # Should add new entry since state changed
    assert len(history) == 2
    assert history[0]['state'] == 'emerging'
    assert history[1]['state'] == 'rising'
    assert history[1]['article_count'] == 5
    assert history[1]['mention_velocity'] == 2.3
    assert history[1]['timestamp'] > existing_timestamp


def test_update_lifecycle_history_multiple_transitions():
    """Test tracking multiple state transitions."""
    narrative = {}
    
    # First state: emerging
    history = update_lifecycle_history(narrative, 'emerging', 3, 1.2)
    assert len(history) == 1
    
    # Update narrative with history
    narrative['lifecycle_history'] = history
    
    # Second state: rising
    history = update_lifecycle_history(narrative, 'rising', 5, 2.3)
    assert len(history) == 2
    
    # Update narrative again
    narrative['lifecycle_history'] = history
    
    # Third state: hot
    history = update_lifecycle_history(narrative, 'hot', 8, 3.5)
    assert len(history) == 3
    
    # Verify all states are tracked
    assert history[0]['state'] == 'emerging'
    assert history[1]['state'] == 'rising'
    assert history[2]['state'] == 'hot'
    
    # Verify metrics are tracked
    assert history[0]['article_count'] == 3
    assert history[1]['article_count'] == 5
    assert history[2]['article_count'] == 8


def test_update_lifecycle_history_velocity_rounding():
    """Test that mention_velocity is rounded to 2 decimal places."""
    narrative = {}
    lifecycle_state = 'emerging'
    article_count = 3
    mention_velocity = 1.23456789
    
    history = update_lifecycle_history(narrative, lifecycle_state, article_count, mention_velocity)
    
    assert history[0]['mention_velocity'] == 1.23


def test_update_lifecycle_history_preserves_existing_entries():
    """Test that existing history entries are preserved."""
    ts1 = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    ts2 = datetime(2024, 1, 2, 12, 0, 0, tzinfo=timezone.utc)
    
    narrative = {
        'lifecycle_history': [
            {'state': 'emerging', 'timestamp': ts1, 'article_count': 3, 'mention_velocity': 1.2},
            {'state': 'rising', 'timestamp': ts2, 'article_count': 5, 'mention_velocity': 2.3}
        ]
    }
    
    # Add new state
    history = update_lifecycle_history(narrative, 'hot', 8, 3.5)
    
    # All previous entries should be preserved
    assert len(history) == 3
    assert history[0]['state'] == 'emerging'
    assert history[0]['timestamp'] == ts1
    assert history[1]['state'] == 'rising'
    assert history[1]['timestamp'] == ts2
    assert history[2]['state'] == 'hot'
