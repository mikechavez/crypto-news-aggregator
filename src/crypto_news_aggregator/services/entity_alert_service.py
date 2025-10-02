"""
Entity alert detection service for trending crypto entities.

Detects and triggers alerts based on:
- New entities appearing in multiple articles
- Velocity spikes in entity mentions
- Sentiment divergence across sources
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta

from ..db.operations.signal_scores import get_trending_entities
from ..db.operations.entity_alerts import (
    create_alert,
    get_recent_alerts,
    alert_exists
)

logger = logging.getLogger(__name__)


def check_new_entity_alert(entity: str, signal_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Check if entity qualifies as a new entity alert.
    
    Criteria:
    - First seen < 6 hours ago
    - Mentioned in >= 3 articles (inferred from velocity/source_count)
    
    Args:
        entity: Entity name
        signal_data: Signal score data from MongoDB
    
    Returns:
        Alert dict or None if criteria not met
    """
    try:
        first_seen = signal_data.get("first_seen")
        if not first_seen:
            return None
        
        # Ensure first_seen is timezone-aware
        if first_seen.tzinfo is None:
            first_seen = first_seen.replace(tzinfo=timezone.utc)
        
        # Check if first seen within last 6 hours
        hours_since_first_seen = (datetime.now(timezone.utc) - first_seen).total_seconds() / 3600
        if hours_since_first_seen >= 6:
            return None
        
        # Check if mentioned in enough articles (use source_count as proxy)
        source_count = signal_data.get("source_count", 0)
        if source_count < 3:
            return None
        
        # Entity qualifies as new and trending
        return {
            "type": "NEW_ENTITY",
            "entity": entity,
            "entity_type": signal_data.get("entity_type", "unknown"),
            "severity": "high",
            "signal_score": signal_data.get("score", 0.0),
            "details": {
                "first_seen": first_seen.isoformat(),
                "hours_since_first_seen": round(hours_since_first_seen, 2),
                "source_count": source_count,
                "velocity": signal_data.get("velocity", 0.0)
            }
        }
    
    except Exception as e:
        logger.exception(f"Error checking new entity alert for {entity}: {e}")
        return None


def check_velocity_spike_alert(entity: str, signal_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Check if entity has a velocity spike.
    
    Criteria:
    - If no baseline: velocity > 10
    - If baseline exists: velocity > 5x baseline
    
    Args:
        entity: Entity name
        signal_data: Signal score data from MongoDB
    
    Returns:
        Alert dict or None if criteria not met
    """
    try:
        velocity = signal_data.get("velocity", 0.0)
        
        # Get baseline velocity (could be stored in signal_data or calculated)
        # For now, use a simple threshold approach
        baseline = signal_data.get("baseline_velocity")
        
        if baseline is None:
            # No baseline: use absolute threshold
            if velocity > 10:
                return {
                    "type": "VELOCITY_SPIKE",
                    "entity": entity,
                    "entity_type": signal_data.get("entity_type", "unknown"),
                    "severity": "medium",
                    "signal_score": signal_data.get("score", 0.0),
                    "details": {
                        "velocity": velocity,
                        "baseline": None,
                        "threshold": 10,
                        "message": f"High velocity detected: {velocity:.2f} mentions/hour"
                    }
                }
        else:
            # Has baseline: check for 5x spike
            if velocity > 5 * baseline:
                return {
                    "type": "VELOCITY_SPIKE",
                    "entity": entity,
                    "entity_type": signal_data.get("entity_type", "unknown"),
                    "severity": "medium",
                    "signal_score": signal_data.get("score", 0.0),
                    "details": {
                        "velocity": velocity,
                        "baseline": baseline,
                        "spike_multiplier": round(velocity / baseline, 2),
                        "message": f"Velocity spike: {velocity:.2f} vs baseline {baseline:.2f}"
                    }
                }
        
        return None
    
    except Exception as e:
        logger.exception(f"Error checking velocity spike alert for {entity}: {e}")
        return None


def check_sentiment_divergence_alert(entity: str, signal_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Check if entity has sentiment divergence across sources.
    
    Criteria:
    - Sentiment divergence > 0.6
    
    Args:
        entity: Entity name
        signal_data: Signal score data from MongoDB
    
    Returns:
        Alert dict or None if criteria not met
    """
    try:
        sentiment = signal_data.get("sentiment", {})
        divergence = sentiment.get("divergence", 0.0)
        
        if divergence > 0.6:
            return {
                "type": "SENTIMENT_DIVERGENCE",
                "entity": entity,
                "entity_type": signal_data.get("entity_type", "unknown"),
                "severity": "medium",
                "signal_score": signal_data.get("score", 0.0),
                "details": {
                    "divergence": divergence,
                    "avg_sentiment": sentiment.get("avg", 0.0),
                    "positive_sources": sentiment.get("positive_count", 0),
                    "negative_sources": sentiment.get("negative_count", 0),
                    "message": f"High sentiment divergence: {divergence:.2f}"
                }
            }
        
        return None
    
    except Exception as e:
        logger.exception(f"Error checking sentiment divergence alert for {entity}: {e}")
        return None


async def detect_alerts() -> List[Dict[str, Any]]:
    """
    Detect alerts for trending entities.
    
    Main entry point for alert detection. Queries signal scores
    and runs all alert checks on each qualifying entity.
    
    Returns:
        List of triggered alerts
    """
    try:
        logger.info("Starting alert detection cycle...")
        
        # Get trending entities with score >= 5.0
        trending_entities = await get_trending_entities(limit=50, min_score=5.0)
        
        if not trending_entities:
            logger.info("No trending entities found for alert detection")
            return []
        
        logger.info(f"Checking {len(trending_entities)} trending entities for alerts")
        
        triggered_alerts = []
        
        for signal_data in trending_entities:
            entity = signal_data.get("entity")
            if not entity:
                continue
            
            # Run all alert checks
            alert_checks = [
                check_new_entity_alert(entity, signal_data),
                check_velocity_spike_alert(entity, signal_data),
                check_sentiment_divergence_alert(entity, signal_data)
            ]
            
            # Collect triggered alerts
            for alert in alert_checks:
                if alert:
                    # Check if this alert already exists (avoid duplicates)
                    exists = await alert_exists(
                        alert_type=alert["type"],
                        entity=entity,
                        hours=24
                    )
                    
                    if not exists:
                        # Create new alert
                        alert_id = await create_alert(
                            alert_type=alert["type"],
                            entity=entity,
                            entity_type=alert["entity_type"],
                            severity=alert["severity"],
                            details=alert["details"],
                            signal_score=alert["signal_score"]
                        )
                        
                        alert["_id"] = alert_id
                        triggered_alerts.append(alert)
                        logger.info(f"Triggered {alert['type']} alert for {entity}")
        
        logger.info(f"Triggered {len(triggered_alerts)} new alerts")
        return triggered_alerts
    
    except Exception as e:
        logger.exception(f"Error in detect_alerts: {e}")
        return []
