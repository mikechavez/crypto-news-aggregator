# Reversed Timestamp Fix - Deployment Guide

## Problem Fixed
Narratives were being created with `first_seen > last_updated`, causing invisible timeline bars in the UI and data corruption.

## Root Cause
In `src/crypto_news_aggregator/services/narrative_service.py`, the create path for new narratives was setting both timestamps to `datetime.now()` instead of using article publication dates:

```python
# BEFORE (BUGGY)
first_seen = datetime.now(timezone.utc)
last_updated = datetime.now(timezone.utc)
```

This meant if articles were published in the past, `first_seen` would be set to the current time, creating reversed timestamps.

## Solution Implemented

### 1. Fixed Timestamp Calculation (lines 864-870)
Now uses article dates for new narratives:

```python
# AFTER (FIXED)
if article_dates:
    first_seen = min(article_dates)      # Earliest article publication
    last_updated = max(article_dates)    # Latest article publication
else:
    # Fallback to now() if no article dates available
    first_seen = datetime.now(timezone.utc)
    last_updated = datetime.now(timezone.utc)
```

### 2. Added Debug Logging
Comprehensive logging before each `upsert_narrative()` call to track:
- All article publication dates being used
- Calculated `first_seen` and `last_updated` values
- Whether `first_seen > last_updated` (the bug condition)
- Timestamp sources (existing narrative, now(), article dates)

**Log prefixes**:
- `[CREATE NARRATIVE DEBUG]` - new narrative creation
- `[MERGE NARRATIVE DEBUG]` - existing narrative merges

## Deployment Steps

### Step 1: Deploy Code
Deploy the updated `src/crypto_news_aggregator/services/narrative_service.py` with:
- ✅ Fix: Use article dates for timestamps
- ✅ Debug logging: Track timestamp sources

### Step 2: Monitor Logs
After deployment, monitor Railway logs for:

```
[CREATE NARRATIVE DEBUG] ========== CREATE UPSERT START ==========
[CREATE NARRATIVE DEBUG] Theme: <theme>
[CREATE NARRATIVE DEBUG] Article dates (sorted):
[CREATE NARRATIVE DEBUG]   [1] <earliest_date>
[CREATE NARRATIVE DEBUG]   [2] <latest_date>
[CREATE NARRATIVE DEBUG] Earliest article: <earliest>
[CREATE NARRATIVE DEBUG] Latest article: <latest>
[CREATE NARRATIVE DEBUG] Calculated first_seen: <first_seen>
[CREATE NARRATIVE DEBUG] Calculated last_updated: <last_updated>
[CREATE NARRATIVE DEBUG] Is first_seen > last_updated? False
```

**Expected**: `Is first_seen > last_updated? False` for all new narratives

### Step 3: Fix Existing Data
After confirming new narratives are created correctly, fix corrupted existing data:

```bash
# Dry run to see what would be fixed
python scripts/fix_reversed_narrative_timestamps.py --dry-run

# Actually fix the data
python scripts/fix_reversed_narrative_timestamps.py
```

### Step 4: Verify Fix
Check MongoDB for remaining reversed timestamps:

```javascript
db.narratives.aggregate([
  {$addFields: {isReversed: {$gt: ["$first_seen", "$last_updated"]}}},
  {$match: {isReversed: true}},
  {$count: "count"}
])
```

Expected result: `{ "count": 0 }`

## Validation Checklist

- [ ] Deploy code with fix and debug logging
- [ ] Monitor Railway logs for `[CREATE NARRATIVE DEBUG]` entries
- [ ] Verify `Is first_seen > last_updated? False` in logs
- [ ] Create a few new narratives and verify timestamps in MongoDB
- [ ] Run data fix script with `--dry-run` first
- [ ] Run data fix script to fix existing corrupted data
- [ ] Verify no reversed timestamps remain in MongoDB
- [ ] Check UI: timeline bars should render correctly (not invisible)
- [ ] Verify no errors in Railway logs

## Files Modified

- `src/crypto_news_aggregator/services/narrative_service.py`
  - Commit 861b647: Added debug logging
  - Commit 80b7f5c: Fixed timestamp calculation

## Rollback Plan

If issues arise, rollback to previous version:

```bash
git revert 80b7f5c  # Revert the fix
git revert 861b647  # Revert the debug logging (optional)
```

Note: Debug logging can remain in place for future troubleshooting.

## Related Documentation

- `TIMESTAMP_DEBUG_GUIDE.md` - Detailed debug logging analysis
- `scripts/fix_reversed_narrative_timestamps.py` - Data fix script
- `NARRATIVE_TIMESTAMP_FIX.md` - Frontend and backend validation (previous fix)
