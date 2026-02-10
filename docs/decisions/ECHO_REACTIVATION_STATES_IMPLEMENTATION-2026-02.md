# Echo and Reactivation Lifecycle States Implementation

## Overview
Added two new lifecycle states to the narrative system to track narratives that return after going dormant, creating a "heartbeat" pattern.

## New States

### Echo State
- **Trigger**: Dormant narrative receives light activity
- **Criteria**: 
  - Previous state must be `dormant`
  - 1-3 articles in last 24 hours
  - Less than 4 articles in last 48 hours (to distinguish from reactivated)
- **Meaning**: A brief "pulse" of activity - the narrative is mentioned again but not yet showing sustained interest

### Reactivated State
- **Trigger**: Dormant or echo narrative receives sustained activity
- **Criteria**:
  - Previous state must be `echo` or `dormant`
  - 4 or more articles in last 48 hours
- **Meaning**: The narrative has returned with sustained coverage after being dormant

## Implementation Details

### Function Changes

#### `determine_lifecycle_state()` in `narrative_service.py`
- Added optional `previous_state` parameter to enable state-aware transitions
- Added logic to check for echo and reactivated states before other state checks
- Echo check: `previous_state == 'dormant' and 1 <= articles_last_24h <= 3 and articles_last_48h < 4`
- Reactivated check: `previous_state in ['echo', 'dormant'] and articles_last_48h >= 4`

### Call Site Updates
Updated all three calls to `determine_lifecycle_state()` to pass `previous_state`:

1. **Salience clustering - existing narrative update** (line ~588):
   - Extracts previous state from `lifecycle_history` before calling function
   
2. **Salience clustering - new narrative creation** (line ~680):
   - Passes `previous_state=None` for new narratives
   
3. **Theme-based clustering** (line ~826):
   - Extracts previous state from existing narrative's `lifecycle_history`

### Active Status List
Updated `find_matching_narrative()` to include new states in `active_statuses`:
```python
active_statuses = ['emerging', 'rising', 'hot', 'cooling', 'dormant', 'echo', 'reactivated']
```

## State Transition Flow

```
dormant → echo (1-3 articles/24h, <4 in 48h)
       ↘
         reactivated (4+ articles/48h)

echo → reactivated (4+ articles/48h)
```

## Testing

### Unit Tests Added
Added 9 new unit tests in `test_lifecycle_state.py`:
- `test_echo_state_from_dormant` - Basic echo state detection
- `test_echo_state_boundary_lower` - Lower boundary (1 article/day)
- `test_echo_state_boundary_upper` - Upper boundary (1.9 articles/day)
- `test_no_echo_without_dormant_previous_state` - Echo requires dormant state
- `test_reactivated_state_from_dormant` - Direct dormant → reactivated
- `test_reactivated_state_from_echo` - Echo → reactivated transition
- `test_reactivated_state_boundary` - Exact boundary (4 articles in 48h)
- `test_no_reactivated_without_echo_or_dormant` - Reactivated requires echo/dormant
- `test_echo_to_reactivated_transition` - Full transition sequence

### Integration Tests Updated
Updated 3 integration tests to include new states in assertions:
- `test_new_narrative_includes_lifecycle_state`
- `test_updated_narrative_recalculates_lifecycle_state`
- `test_theme_based_narratives_include_lifecycle_state`

### Test Results
All 25 tests pass successfully:
```
tests/services/test_lifecycle_state.py::TestDetermineLifecycleState - 22 passed
tests/services/test_lifecycle_state.py::TestLifecycleStateIntegration - 3 passed
```

## Key Design Decisions

1. **Check Order**: Reactivated is checked before echo to ensure sustained activity takes priority
2. **Velocity Approximation**: Uses `mention_velocity * 1.0` for 24h and `* 2.0` for 48h as approximation
3. **Echo Threshold**: Echo requires < 4 articles in 48h to distinguish from reactivated
4. **State Awareness**: Previous state is extracted from `lifecycle_history` array's last entry

## Files Modified

1. `src/crypto_news_aggregator/services/narrative_service.py`
   - Updated `determine_lifecycle_state()` function
   - Updated 3 call sites
   - Updated `find_matching_narrative()` active_statuses

2. `tests/services/test_lifecycle_state.py`
   - Added 9 new unit tests
   - Updated 3 integration test assertions

## Usage Example

```python
# Extract previous state from lifecycle history
lifecycle_history = narrative.get('lifecycle_history', [])
previous_state = lifecycle_history[-1].get('state') if lifecycle_history else None

# Determine new state with previous state awareness
lifecycle_state = determine_lifecycle_state(
    article_count=12,
    mention_velocity=1.5,  # 1.5 articles/day = 3 in 48h
    first_seen=first_seen,
    last_updated=last_updated,
    previous_state=previous_state  # e.g., 'dormant'
)
# Result: 'echo' (light activity after dormant)
```

## Benefits

1. **Heartbeat Detection**: Captures narratives that pulse back to life after dormancy
2. **Transition Tracking**: Distinguishes between brief mentions (echo) and sustained returns (reactivated)
3. **Historical Context**: Uses previous state to make smarter lifecycle decisions
4. **User Insight**: Helps users understand if a narrative is truly returning or just briefly mentioned

## Next Steps

Consider future enhancements:
- Track number of echo cycles before reactivation
- Add metrics for echo-to-reactivated conversion rate
- Visualize heartbeat patterns in UI timeline
- Alert users when dormant narratives reactivate
