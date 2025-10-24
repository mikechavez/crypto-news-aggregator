# Timestamp Bug - RESOLVED ✅

## Problem
UI was showing negative timeline bar widths:
- Error: `width: -0.37873720925534826`
- Data showed: `first_seen: 2025-10-23T06:01:36` > `last_article_at: 2025-10-23T04:56:04`

## Root Cause
**136 narratives had wrong `first_seen` values** - they were created with `first_seen = now()` instead of `first_seen = min(article_dates)`.

Example:
- Narrative "Hyperliquid Strategies"
- `first_seen: 2025-10-23T06:01:36` (when created)
- Earliest article: `2025-10-23T02:29:56` (3.5 hours earlier!)
- This caused `first_seen > last_article_at`, resulting in negative widths

## Solution Implemented

### 1. Backend Fix (Prevents Future Issues)
**File**: `src/crypto_news_aggregator/services/narrative_service.py`

Changed the create path (lines 870-878) to use article dates instead of `now()`:

```python
if article_dates:
    first_seen = min(article_dates)      # Earliest article publication
    last_updated = max(article_dates)    # Latest article publication
else:
    first_seen = datetime.now(timezone.utc)
    last_updated = datetime.now(timezone.utc)
```

**Commits**:
- 80b7f5c: Fixed timestamp calculation
- 80831f1: Added debug logging

### 2. Data Fix Script (Corrects Existing Data)
**File**: `scripts/fix_narrative_first_seen.py`

New script that:
- Finds all narratives where `first_seen > earliest_article_published_at`
- Fixes by setting `first_seen` to earliest article date
- Includes dry-run mode for safety
- Validates fix after completion

**Commit**: 91c323a

**Results**: ✅ Fixed 136 narratives

### 3. API Debugging (Helps Identify Issues)
**File**: `src/crypto_news_aggregator/api/v1/endpoints/narratives.py`

Added logging to track timestamp ordering:
- `[API TIMESTAMP BUG]` - When first_seen > last_updated
- `[API DEBUG]` - When article lookup differs from last_updated

**Commit**: 65843f8

## Verification

### Before Fix
```json
{
  "first_seen": "2025-10-23T06:01:36.857000",
  "last_article_at": "2025-10-23T04:56:04",
  "width": -0.37873720925534826  // ❌ NEGATIVE
}
```

### After Fix
```json
{
  "first_seen": "2025-10-23T02:29:56",
  "last_article_at": "2025-10-23T04:56:04",
  "width": 0.45  // ✅ POSITIVE
}
```

## Deployment Checklist

- [x] Deploy backend fix to prevent future issues
- [x] Run data fix script: `poetry run python scripts/fix_narrative_first_seen.py`
- [x] Verify API returns correct timestamps
- [x] UI now shows timeline bars with positive widths

## Files Modified

1. **src/crypto_news_aggregator/services/narrative_service.py**
   - Commit 80b7f5c: Fixed timestamp calculation
   - Commit 80831f1: Added debug logging

2. **src/crypto_news_aggregator/api/v1/endpoints/narratives.py**
   - Commit 65843f8: Added timestamp ordering validation

3. **scripts/fix_narrative_first_seen.py** (NEW)
   - Commit 91c323a: Data fix script

## Testing

### Manual Test
```bash
# Check API response
curl 'http://localhost:8000/api/v1/narratives/active?limit=3' | jq '.[] | {first_seen, last_article_at}'

# Expected: first_seen < last_article_at for all narratives
```

### Automated Test
```bash
# Run the fix script with dry-run
poetry run python scripts/fix_narrative_first_seen.py --dry-run

# Run the actual fix
poetry run python scripts/fix_narrative_first_seen.py
```

## Impact

- ✅ **136 narratives fixed** - All now have correct timestamps
- ✅ **Timeline bars render correctly** - No more negative widths
- ✅ **Future narratives protected** - Backend fix prevents recurrence
- ✅ **UI displays properly** - All narrative timeline bars visible

## Related Documentation

- `TIMESTAMP_DEBUG_GUIDE.md` - Original debug logging setup
- `TIMESTAMP_FIX_DEPLOYMENT.md` - Backend fix deployment guide
- `TIMESTAMP_FIX_SUMMARY.md` - Complete fix summary
- `TIMESTAMP_BUG_INVESTIGATION.md` - Investigation notes
- `TIMESTAMP_BUG_CURRENT_STATUS.md` - Previous status tracking
