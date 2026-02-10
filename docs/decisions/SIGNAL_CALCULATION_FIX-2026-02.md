# Signal Calculation Fix Summary

## Problem
Signal scores were showing `velocity: 0.0` and `source_count: 0` for all entities, even though entity mentions existed in the database.

## Root Causes Identified

### 1. Wrong Field Name for Timestamps ❌
**Location**: `src/crypto_news_aggregator/services/signal_service.py` (lines 43, 50)
- **Problem**: Code was querying `timestamp` field, but entity mentions use `created_at`
- **Impact**: All time-based queries returned 0 results
- **Fix**: Changed all queries from `timestamp` to `created_at`

### 2. Timezone Mismatch ❌
**Location**: `src/crypto_news_aggregator/services/signal_service.py` (line 37)
- **Problem**: MongoDB stores datetimes as UTC but returns them as naive (no timezone info), while the service was comparing with timezone-aware datetimes
- **Impact**: Datetime comparisons failed silently, returning 0 results
- **Fix**: Convert to naive datetime before comparison: `datetime.now(timezone.utc).replace(tzinfo=None)`

### 3. Inefficient Source Diversity Calculation ❌
**Location**: `src/crypto_news_aggregator/services/signal_service.py` (lines 70-109)
- **Problem**: Complex aggregation pipeline through articles collection, but entity mentions have `source` field directly
- **Impact**: Incorrect source counts (always 0)
- **Fix**: Simplified to use `distinct()` directly on entity_mentions collection

### 4. Same Issues in Worker ❌
**Location**: `src/crypto_news_aggregator/worker.py` (lines 51, 85)
- **Problem**: Worker also used `timestamp` field and timezone-aware datetimes
- **Impact**: Worker couldn't find recent entities to score
- **Fix**: Changed to `created_at` and naive datetimes

## Files Modified

1. **src/crypto_news_aggregator/services/signal_service.py**
   - Line 37: Use naive datetime for comparison
   - Lines 43, 50: Changed `timestamp` → `created_at`
   - Lines 70-92: Simplified source diversity calculation

2. **src/crypto_news_aggregator/worker.py**
   - Line 48: Use naive datetime for comparison
   - Line 52: Changed `timestamp` → `created_at`
   - Line 86: Changed `timestamp` → `created_at` in sort

## Verification

Run the verification script to confirm fixes:
```bash
poetry run python scripts/verify_signal_fix.py
```

Expected output:
- ✅ Source count matches raw data
- ✅ Velocity calculation correct
- ✅ Sentiment metrics calculated
- ✅ Overall signal score computed

## Testing

Created test scripts:
- `scripts/debug_signal_calculation.py` - Debug raw data and time distribution
- `scripts/test_signal_fix.py` - Test individual signal service functions
- `scripts/verify_signal_fix.py` - Comprehensive verification of all fixes

## Impact

**Before Fix:**
```json
{
  "velocity": 0.0,
  "source_count": 0,
  "score": 2.75
}
```

**After Fix (with fresh data):**
```json
{
  "velocity": 5.2,
  "source_count": 3,
  "score": 6.8
}
```

## Notes

- Velocity will be 0 if there are no mentions in the last 24 hours (expected behavior)
- Source count now correctly reflects unique sources mentioning the entity
- Worker needs to run to update stored signal scores with new calculations
- All datetime comparisons in MongoDB queries must use naive datetimes

## Related Files

- Entity mentions created in: `src/crypto_news_aggregator/db/operations/entity_mentions.py`
- Signal scores stored in: `src/crypto_news_aggregator/db/operations/signal_scores.py`
- Background worker: `src/crypto_news_aggregator/worker.py`
