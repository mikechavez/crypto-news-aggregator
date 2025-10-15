# Lifecycle State Implementation Summary

## Overview
Added comprehensive lifecycle state tracking for narratives to show progression over time. The new `lifecycle_state` field tracks narratives through five distinct states based on activity patterns and recency.

## Implementation Details

### 1. New Function: `determine_lifecycle_state`
**Location**: `src/crypto_news_aggregator/services/narrative_service.py` (lines 95-136)

**Parameters**:
- `article_count`: Number of articles in the narrative
- `mention_velocity`: Articles per day rate
- `first_seen`: When narrative was first detected
- `last_updated`: When narrative was last updated

**Returns**: One of five lifecycle states:
- `'emerging'`: < 4 articles
- `'rising'`: velocity >= 1.5 and article_count < 7
- `'hot'`: article_count >= 7 OR velocity >= 3.0
- `'cooling'`: No new articles in last 3 days
- `'dormant'`: No new articles in last 7 days

**Logic Priority**:
1. Recency checks first (dormant/cooling override all other states)
2. Activity level checks (hot/rising)
3. Default to emerging for small narratives

### 2. Integration into `detect_narratives`

#### Salience-Based Clustering (New Narratives)
- Lines 497-502: Calculate lifecycle_state for new narratives
- Line 512: Store in narrative_data dict
- Line 530: Save to database

#### Salience-Based Clustering (Updating Existing)
- Lines 427-439: Recalculate lifecycle_state when merging articles
- Line 450: Store in update_data dict
- Updates mention_velocity based on time since first_seen

#### Theme-Based Clustering (Legacy)
- Lines 641-645: Calculate lifecycle_state
- Line 659: Store in narrative dict
- Line 681: Pass to upsert_narrative function

### 3. Database Operations Update
**Location**: `src/crypto_news_aggregator/db/operations/narratives.py`

**Changes**:
- Line 77: Added `lifecycle_state` optional parameter to `upsert_narrative`
- Lines 163-165: Store lifecycle_state when updating narratives
- Lines 200-202: Store lifecycle_state when creating narratives

### 4. Bug Fix
Fixed bug in narrative matching where `cluster.get('article_ids')` was called on a list:
- Line 425: Now extracts article_ids from cluster articles correctly
- Uses list comprehension: `set(str(article.get('_id')) for article in cluster if isinstance(article, dict))`

## Test Coverage

### Unit Tests (13 tests)
**File**: `tests/services/test_lifecycle_state.py`

**Test Cases**:
1. **Emerging State**:
   - Low article count (< 4)
   - Edge case (4-6 articles with low velocity)

2. **Rising State**:
   - Moderate velocity (>= 1.5)
   - Boundary conditions

3. **Hot State**:
   - High article count (>= 7)
   - High velocity (>= 3.0)
   - Both conditions met

4. **Cooling State**:
   - 3+ days since last update
   - Boundary at exactly 3 days

5. **Dormant State**:
   - 7+ days since last update
   - Boundary at exactly 7 days

6. **Priority Tests**:
   - Recency overrides activity level
   - Recent updates prevent cooling/dormant

### Integration Tests (3 tests)
**File**: `tests/services/test_lifecycle_state.py`

**Test Cases**:
1. New narratives include lifecycle_state field
2. Updated narratives recalculate lifecycle_state
3. Theme-based narratives include lifecycle_state

### Test Results
```
✅ All 16 tests passing
✅ Existing narrative service tests still passing (9 tests)
✅ No regressions introduced
```

## Usage Example

```python
from datetime import datetime, timezone, timedelta
from crypto_news_aggregator.services.narrative_service import determine_lifecycle_state

# Example: Hot narrative
now = datetime.now(timezone.utc)
state = determine_lifecycle_state(
    article_count=10,
    mention_velocity=4.0,
    first_seen=now - timedelta(days=2),
    last_updated=now - timedelta(hours=1)
)
# Returns: 'hot'

# Example: Cooling narrative
state = determine_lifecycle_state(
    article_count=15,
    mention_velocity=2.0,
    first_seen=now - timedelta(days=10),
    last_updated=now - timedelta(days=4)
)
# Returns: 'cooling'
```

## Database Schema
Narratives now include the `lifecycle_state` field:

```json
{
  "_id": "...",
  "title": "Bitcoin Adoption Accelerates",
  "lifecycle": "hot",           // Legacy field (kept for compatibility)
  "lifecycle_state": "hot",     // New field (primary going forward)
  "article_count": 12,
  "mention_velocity": 4.5,
  "first_seen": "2025-10-10T00:00:00Z",
  "last_updated": "2025-10-15T12:00:00Z"
}
```

## Benefits
1. **Clear Progression Tracking**: Five distinct states show narrative evolution
2. **Recency Awareness**: Cooling/dormant states identify stale narratives
3. **Activity-Based Classification**: Hot/rising states highlight active narratives
4. **Backward Compatible**: Legacy `lifecycle` field preserved
5. **Well-Tested**: Comprehensive unit and integration tests
6. **Bug Fix Included**: Fixed article_ids extraction bug in narrative matching

## Next Steps
- Consider adding lifecycle_state to API responses
- Add UI indicators for different lifecycle states
- Create analytics dashboard showing state transitions over time
- Add alerts for narratives entering hot/rising states
