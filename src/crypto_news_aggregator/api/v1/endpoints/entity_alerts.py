"""
Entity alert endpoints for the Crypto News Aggregator API.

Provides access to entity trend alerts including:
- New entity alerts
- Velocity spike alerts
- Sentiment divergence alerts
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Query, HTTPException, status
from fastapi.responses import JSONResponse
import time
import logging

from ....db.operations.entity_alerts import get_recent_alerts

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/entity-alerts", tags=["entity-alerts"])


# Simple in-memory cache for recent alerts (30 second TTL)
_alert_cache: Dict[str, Any] = {}
CACHE_TTL = 30  # seconds


def _get_cache_key(hours: int, severity: Optional[str], unresolved_only: bool) -> str:
    """Generate cache key for alert queries."""
    return f"alerts_{hours}_{severity}_{unresolved_only}"


def _get_cached_alerts(cache_key: str) -> Optional[List[Dict[str, Any]]]:
    """Get alerts from cache if not expired."""
    if cache_key in _alert_cache:
        cached_data = _alert_cache[cache_key]
        if time.time() - cached_data["timestamp"] < CACHE_TTL:
            logger.debug(f"Cache hit for {cache_key}")
            return cached_data["data"]
    return None


def _set_cached_alerts(cache_key: str, data: List[Dict[str, Any]]) -> None:
    """Store alerts in cache with timestamp."""
    _alert_cache[cache_key] = {
        "data": data,
        "timestamp": time.time()
    }


@router.get(
    "/recent",
    response_model=List[Dict[str, Any]],
    summary="Get recent entity alerts",
    description="Get recent entity trend alerts with optional filtering by severity and time window."
)
async def get_recent_entity_alerts(
    hours: int = Query(24, ge=1, le=168, description="Number of hours to look back (1-168)"),
    severity: Optional[str] = Query(None, pattern="^(high|medium|low)$", description="Filter by severity"),
    unresolved_only: bool = Query(True, description="Only return unresolved alerts")
) -> List[Dict[str, Any]]:
    """
    Get recent entity alerts.
    
    Returns alerts triggered within the specified time window, optionally filtered
    by severity and resolution status.
    
    **Alert Types:**
    - `NEW_ENTITY`: New entity detected with high mention velocity
    - `VELOCITY_SPIKE`: Sudden spike in entity mentions
    - `SENTIMENT_DIVERGENCE`: High sentiment divergence across sources
    
    **Severity Levels:**
    - `high`: Critical alerts requiring immediate attention
    - `medium`: Important alerts worth monitoring
    - `low`: Informational alerts
    
    **Response includes:**
    - `type`: Alert type
    - `entity`: Entity name
    - `entity_type`: Type of entity (ticker, project, event)
    - `severity`: Alert severity
    - `signal_score`: Current signal score
    - `details`: Additional alert-specific details
    - `triggered_at`: When the alert was triggered
    - `resolved_at`: When the alert was resolved (null if unresolved)
    """
    try:
        # Check cache first
        cache_key = _get_cache_key(hours, severity, unresolved_only)
        cached_alerts = _get_cached_alerts(cache_key)
        
        if cached_alerts is not None:
            return cached_alerts
        
        # Fetch from database
        alerts = await get_recent_alerts(
            hours=hours,
            severity=severity,
            unresolved_only=unresolved_only
        )
        
        # Cache the results
        _set_cached_alerts(cache_key, alerts)
        
        logger.info(f"Retrieved {len(alerts)} entity alerts (hours={hours}, severity={severity}, unresolved_only={unresolved_only})")
        
        return alerts
    
    except Exception as e:
        logger.exception(f"Error fetching recent entity alerts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching entity alerts"
        )


@router.get(
    "/stats",
    response_model=Dict[str, Any],
    summary="Get alert statistics",
    description="Get statistics about recent entity alerts."
)
async def get_alert_stats(
    hours: int = Query(24, ge=1, le=168, description="Number of hours to look back (1-168)")
) -> Dict[str, Any]:
    """
    Get statistics about recent entity alerts.
    
    Returns counts by alert type, severity, and resolution status.
    """
    try:
        # Get all alerts in the time window
        all_alerts = await get_recent_alerts(hours=hours, unresolved_only=False)
        
        # Calculate statistics
        stats = {
            "total": len(all_alerts),
            "unresolved": sum(1 for a in all_alerts if a.get("resolved_at") is None),
            "resolved": sum(1 for a in all_alerts if a.get("resolved_at") is not None),
            "by_type": {},
            "by_severity": {},
            "by_entity_type": {}
        }
        
        # Count by type
        for alert in all_alerts:
            alert_type = alert.get("type", "unknown")
            stats["by_type"][alert_type] = stats["by_type"].get(alert_type, 0) + 1
            
            severity = alert.get("severity", "unknown")
            stats["by_severity"][severity] = stats["by_severity"].get(severity, 0) + 1
            
            entity_type = alert.get("entity_type", "unknown")
            stats["by_entity_type"][entity_type] = stats["by_entity_type"].get(entity_type, 0) + 1
        
        return stats
    
    except Exception as e:
        logger.exception(f"Error fetching alert statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching alert statistics"
        )
