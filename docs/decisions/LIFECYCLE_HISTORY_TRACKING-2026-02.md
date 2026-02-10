# Lifecycle History Tracking Implementation

## Overview
Implemented lifecycle history tracking to visualize narrative evolution over time by recording state transitions with timestamps and metrics.

## Implementation Details

### Core Function: `update_lifecycle_history`
**Location:** `src/crypto_news_aggregator/services/narrative_service.py`

**Purpose:** Track when narratives transition between lifecycle states.

**Behavior:**
- Checks if current `lifecycle_state` differs from the last entry in `lifecycle_history` array
- If different or if `lifecycle_history` doesn't exist, appends a new entry
- Each entry contains:
  - `state`: The lifecycle state value (emerging, rising, hot, cooling, dormant)
  - `timestamp`: Current datetime in UTC
  - `article_count`: Number of articles in the narrative
  - `mention_velocity`: Articles per day rate (rounded to 2 decimals)

**Function Signature:**
```python
def update_lifecycle_history(
    narrative: Dict[str, Any],
    lifecycle_state: str,
    article_count: int,
    mention_velocity: float
) -> List[Dict[str, Any]]
```

### Integration Points

#### 1. New Narratives (Salience-Based Clustering)
**Location:** `detect_narratives()` function, lines 593-599

When creating a new narrative:
- Initializes `lifecycle_history` with first entry
- Passes empty dict `{}` to `update_lifecycle_history`
- Adds history to both `narrative_data` dict and database document

#### 2. Updated Narratives (Salience-Based Clustering)
**Location:** `detect_narratives()` function, lines 505-511

When updating an existing narrative:
- Calls `update_lifecycle_history` with existing narrative
- Only adds new entry if state has changed
- Updates database with new history

#### 3. Theme-Based Clustering (Fallback Path)
**Location:** `detect_narratives()` function, lines 730-737

When using legacy theme-based clustering:
- Retrieves existing narrative from `existing_narratives` dict
- Calls `update_lifecycle_history` to track state changes
- Includes history in narrative document

### Database Integration

Updated `upsert_narrative()` function in `src/crypto_news_aggregator/db/operations/narratives.py`:

**Changes:**
- Added `lifecycle_history` parameter (optional)
- Saves `lifecycle_history` to database for both new and updated narratives
- History is preserved across narrative updates

**Function Signature:**
```python
async def upsert_narrative(
    ...,
    lifecycle_history: Optional[List[Dict[str, Any]]] = None
) -> str
```

## Data Structure

### Lifecycle History Entry Format
```json
{
  "state": "rising",
  "timestamp": "2024-10-15T19:37:00.000Z",
  "article_count": 5,
  "mention_velocity": 2.3
}
```

### Example Narrative with History
```json
{
  "_id": "...",
  "title": "SEC Regulatory Actions",
  "lifecycle_state": "hot",
  "lifecycle_history": [
    {
      "state": "emerging",
      "timestamp": "2024-10-13T10:00:00.000Z",
      "article_count": 3,
      "mention_velocity": 1.2
    },
    {
      "state": "rising",
      "timestamp": "2024-10-14T15:30:00.000Z",
      "article_count": 5,
      "mention_velocity": 2.3
    },
    {
      "state": "hot",
      "timestamp": "2024-10-15T19:37:00.000Z",
      "article_count": 8,
      "mention_velocity": 3.5
    }
  ]
}
```

## Testing

**Test File:** `tests/services/test_lifecycle_history.py`

**Test Coverage:**
- ✅ Empty narrative initialization
- ✅ No change when state remains the same
- ✅ State transition tracking
- ✅ Multiple transitions
- ✅ Velocity rounding to 2 decimals
- ✅ Preservation of existing entries

**Test Results:** All 6 tests passing

## Use Cases

### 1. Visualization
The lifecycle history enables:
- Timeline charts showing narrative evolution
- State transition graphs
- Growth/decline patterns over time

### 2. Analytics
Track metrics like:
- Time spent in each lifecycle state
- Velocity changes during transitions
- Article accumulation patterns

### 3. Insights
Identify:
- Fast-rising narratives (quick transitions)
- Sustained narratives (long time in "hot" state)
- Declining narratives (transitions to cooling/dormant)

## API Integration

The `lifecycle_history` field is now available in:
- `GET /api/narratives` - List all narratives with history
- `GET /api/narratives/{id}` - Get specific narrative with full history
- Narrative detection results from `detect_narratives()`

## Future Enhancements

Potential improvements:
1. **Transition Analysis**: Calculate average time between state transitions
2. **Prediction**: Use history patterns to predict next state
3. **Alerts**: Notify when narratives transition to specific states
4. **Visualization**: Build UI components to display history timeline
5. **Aggregation**: Analyze common transition patterns across all narratives

## Files Modified

1. `src/crypto_news_aggregator/services/narrative_service.py`
   - Added `update_lifecycle_history()` function
   - Integrated into `detect_narratives()` for all code paths

2. `src/crypto_news_aggregator/db/operations/narratives.py`
   - Updated `upsert_narrative()` to accept and save `lifecycle_history`

3. `tests/services/test_lifecycle_history.py`
   - New test file with comprehensive coverage

## Summary

Lifecycle history tracking is now fully integrated into the narrative detection system. Every narrative will automatically track state transitions with timestamps and metrics, enabling rich visualization and analysis of narrative evolution over time.
