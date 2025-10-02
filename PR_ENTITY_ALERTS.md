# Entity Alert Detection System

## Overview

Implemented a comprehensive entity alert detection system that monitors trending crypto entities and triggers alerts based on specific patterns. The system runs as a background worker task and exposes alerts via REST API.

## Implementation Summary

### 1. Alert Service (`src/crypto_news_aggregator/services/entity_alert_service.py`)

**Alert Detection Functions:**

- `check_new_entity_alert()`: Detects newly appearing entities
  - Criteria: First seen < 6 hours ago AND mentioned in >= 3 sources
  - Severity: **high**
  
- `check_velocity_spike_alert()`: Detects sudden mention spikes
  - Criteria: velocity > 10 (no baseline) OR velocity > 5x baseline
  - Severity: **medium**
  
- `check_sentiment_divergence_alert()`: Detects sentiment conflicts
  - Criteria: sentiment divergence > 0.6
  - Severity: **medium**

- `detect_alerts()`: Main entry point
  - Queries signal scores >= 5.0
  - Runs all alert checks
  - Prevents duplicate alerts within 24 hours
  - Returns list of triggered alerts

### 2. Database Operations (`src/crypto_news_aggregator/db/operations/entity_alerts.py`)

**MongoDB Collection:** `entity_alerts`

**Functions:**
- `create_alert()`: Store new alert with type, entity, severity, details
- `get_recent_alerts()`: Retrieve alerts with filtering (hours, severity, resolved status)
- `resolve_alert()`: Mark alert as resolved
- `alert_exists()`: Check for duplicate alerts
- `ensure_indexes()`: Create indexes on triggered_at, entity+type, severity

**Schema:**
```python
{
    "type": str,              # NEW_ENTITY, VELOCITY_SPIKE, SENTIMENT_DIVERGENCE
    "entity": str,            # Entity name
    "entity_type": str,       # ticker, project, event
    "severity": str,          # high, medium, low
    "details": dict,          # Alert-specific details
    "signal_score": float,    # Current signal score
    "triggered_at": datetime, # When alert was triggered
    "resolved_at": datetime,  # When alert was resolved (null if unresolved)
    "created_at": datetime
}
```

### 3. Worker Integration (`src/crypto_news_aggregator/worker.py`)

**New Functions:**
- `check_alerts()`: Runs alert detection cycle
- `schedule_alert_checks()`: Continuous monitoring loop

**Schedule:** Every **2 minutes** (120 seconds)

**Logging:**
- "Starting alert detection cycle..."
- "Triggered N new alerts" (when alerts found)
- "No new alerts triggered in this cycle" (when no alerts)

### 4. API Endpoints (`src/crypto_news_aggregator/api/v1/endpoints/entity_alerts.py`)

**Endpoints:**

#### `GET /api/v1/entity-alerts/recent`
Retrieve recent entity alerts with filtering.

**Query Parameters:**
- `hours` (int, 1-168): Time window to look back (default: 24)
- `severity` (str): Filter by severity: high|medium|low (optional)
- `unresolved_only` (bool): Only unresolved alerts (default: true)

**Response:** List of alert objects
```json
[
  {
    "_id": "alert_id",
    "type": "NEW_ENTITY",
    "entity": "TEST_TOKEN",
    "entity_type": "ticker",
    "severity": "high",
    "signal_score": 8.0,
    "details": {
      "first_seen": "2025-10-01T20:00:00Z",
      "hours_since_first_seen": 2.5,
      "source_count": 5,
      "velocity": 15.0
    },
    "triggered_at": "2025-10-01T22:30:00Z",
    "resolved_at": null
  }
]
```

**Caching:** 30-second TTL for performance

#### `GET /api/v1/entity-alerts/stats`
Get alert statistics.

**Query Parameters:**
- `hours` (int, 1-168): Time window (default: 24)

**Response:**
```json
{
  "total": 10,
  "unresolved": 7,
  "resolved": 3,
  "by_type": {
    "NEW_ENTITY": 4,
    "VELOCITY_SPIKE": 5,
    "SENTIMENT_DIVERGENCE": 1
  },
  "by_severity": {
    "high": 4,
    "medium": 6
  },
  "by_entity_type": {
    "ticker": 7,
    "project": 3
  }
}
```

### 5. Test Coverage

**Service Tests** (`tests/services/test_entity_alert_service.py`): 14 tests
- New entity alert detection (4 tests)
- Velocity spike detection (4 tests)
- Sentiment divergence detection (3 tests)
- Main detect_alerts function (3 tests)

**API Tests** (`tests/api/test_entity_alerts.py`): 9 tests
- Recent alerts retrieval with filters
- Statistics endpoint
- Cache behavior
- Validation errors

**All tests passing:** ✅ 14/14 service tests

## Alert Types

### 1. NEW_ENTITY
**Trigger:** Entity first seen < 6 hours ago with >= 3 sources  
**Severity:** High  
**Use Case:** Catch emerging tokens/projects early

### 2. VELOCITY_SPIKE
**Trigger:** Mention velocity > 10 OR > 5x baseline  
**Severity:** Medium  
**Use Case:** Detect sudden interest surges

### 3. SENTIMENT_DIVERGENCE
**Trigger:** Sentiment divergence > 0.6  
**Severity:** Medium  
**Use Case:** Identify controversial topics

## Architecture

```
Worker (every 2 min)
    ↓
detect_alerts()
    ↓
get_trending_entities(score >= 5.0)
    ↓
For each entity:
    ├─ check_new_entity_alert()
    ├─ check_velocity_spike_alert()
    └─ check_sentiment_divergence_alert()
    ↓
alert_exists() → Skip if duplicate
    ↓
create_alert() → Store in MongoDB
    ↓
API: GET /entity-alerts/recent
```

## Database Indexes

```python
# entity_alerts collection
- triggered_at (for time-based queries)
- (entity, type, triggered_at) (for duplicate detection)
- severity (for filtering)
- resolved_at (for filtering unresolved)
```

## Usage Examples

### API Requests

```bash
# Get all unresolved alerts from last 24 hours
curl "http://localhost:8000/api/v1/entity-alerts/recent"

# Get high severity alerts from last 12 hours
curl "http://localhost:8000/api/v1/entity-alerts/recent?hours=12&severity=high"

# Get all alerts including resolved
curl "http://localhost:8000/api/v1/entity-alerts/recent?unresolved_only=false"

# Get alert statistics
curl "http://localhost:8000/api/v1/entity-alerts/stats"
```

### Programmatic Usage

```python
from crypto_news_aggregator.services.entity_alert_service import detect_alerts
from crypto_news_aggregator.db.operations.entity_alerts import get_recent_alerts

# Detect alerts
alerts = await detect_alerts()

# Get recent high-severity alerts
high_alerts = await get_recent_alerts(hours=24, severity="high")

# Get all alerts from last week
all_alerts = await get_recent_alerts(hours=168, unresolved_only=False)
```

## Configuration

No configuration required. Alert thresholds are hardcoded based on requirements:
- New entity: < 6 hours, >= 3 sources
- Velocity spike: > 10 or > 5x baseline
- Sentiment divergence: > 0.6

## Future Enhancements

Potential improvements (not implemented):
- Webhook notifications for alerts
- User-specific alert subscriptions
- Configurable thresholds
- Alert resolution automation
- Alert history and trends
- Email/Slack notifications

## Files Changed

### New Files
- `src/crypto_news_aggregator/services/entity_alert_service.py` (234 lines)
- `src/crypto_news_aggregator/db/operations/entity_alerts.py` (169 lines)
- `src/crypto_news_aggregator/api/v1/endpoints/entity_alerts.py` (166 lines)
- `tests/services/test_entity_alert_service.py` (319 lines)
- `tests/api/test_entity_alerts.py` (245 lines)

### Modified Files
- `src/crypto_news_aggregator/worker.py` (+38 lines)
- `src/crypto_news_aggregator/api/v1/__init__.py` (+2 lines)

**Total:** 1,133 insertions

## Testing

```bash
# Run service tests
poetry run pytest tests/services/test_entity_alert_service.py -v

# Run API tests
poetry run pytest tests/api/test_entity_alerts.py -v

# Run all tests
poetry run pytest
```

## Deployment Checklist

Before deploying:
- ✅ All tests pass
- ✅ No import errors
- ✅ Worker integration complete
- ✅ API endpoints registered
- ⚠️ MongoDB indexes will be created automatically on first run
- ⚠️ Monitor worker logs for "Starting alert check schedule"

## Branch

Feature branch: `feature/alert-detection`

Ready for merge to main after testing in Railway environment.
