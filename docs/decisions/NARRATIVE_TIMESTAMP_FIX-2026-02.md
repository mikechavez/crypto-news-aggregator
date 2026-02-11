# Narrative Timestamp Data Corruption Fix

## Problem Summary

Narratives in the database had data corruption where `first_seen` timestamps were sometimes **after** `last_updated` timestamps, which is logically impossible. This caused:

- **Frontend**: Negative timeline bar widths (e.g., -0.128 pixels) causing invisible bars
- **Backend**: Invalid data state that violates business logic

### Root Cause

The issue occurred in two places:

1. **New narrative creation** (`narrative_service.py` lines 830-831):
   - Both `first_seen` and `last_updated` were set to `datetime.now(timezone.utc)`
   - If articles had future-dated timestamps (parsing errors or clock skew), this could cause issues
   - More likely: timestamp parsing from cluster data was setting `first_seen` to a later time

2. **Narrative updates** (direct database operations):
   - When updating existing narratives, `last_updated` was always set to `now`
   - But `first_seen` could be pulled from cluster data with incorrect timestamps
   - No validation prevented `last_updated < first_seen`

## Solution Implemented

### 1. Frontend Temporary Fix (Narratives.tsx)

Added graceful handling in the `TimelineBar` component:

```typescript
// Fix reversed dates: ensure last_updated >= first_seen
if (lastUpdatedDate < firstSeenDate) {
  console.warn('[TimelineBar] Detected reversed dates, swapping them');
  [firstSeenDate, lastUpdatedDate] = [lastUpdatedDate, firstSeenDate];
}
```

**Purpose**: Prevent invisible timeline bars while backend fix is deployed

### 2. Backend Validation (narratives.py)

Added validation in `upsert_narrative()` function:

```python
# Ensure last_updated >= first_seen (prevent data corruption)
if now < first_seen_date:
    logger.warning(f"[NARRATIVE VALIDATION] Detected reversed timestamps...")
    last_updated_date = first_seen_date
else:
    last_updated_date = now

# For existing narratives:
if last_updated_date < existing_first_seen:
    logger.warning(f"[NARRATIVE VALIDATION] Update would create reversed timestamps...")
    first_seen_date = existing_first_seen
    last_updated_date = existing_first_seen
```

**Purpose**: Prevent future data corruption at the source

### 3. Data Fix Script

Created `scripts/fix_reversed_narrative_timestamps.py` to:

- Find all narratives where `first_seen > last_updated`
- Swap the timestamps to restore logical consistency
- Validate the fix
- Support dry-run mode for safety

## Deployment Steps

### Step 1: Deploy Backend Validation (Required)

```bash
# Create a feature branch
git checkout -b fix/narrative-timestamp-validation

# Changes are in:
# - src/crypto_news_aggregator/db/operations/narratives.py

# Commit and push
git add src/crypto_news_aggregator/db/operations/narratives.py
git commit -m "feat: add timestamp validation to prevent narrative data corruption

- Validate first_seen <= last_updated in upsert_narrative()
- Prevent reversed timestamps when creating new narratives
- Prevent reversed timestamps when updating existing narratives
- Log warnings when validation catches issues"

git push origin fix/narrative-timestamp-validation
```

### Step 2: Deploy Frontend Fix (Recommended)

```bash
# Create a feature branch
git checkout -b fix/timeline-bar-reversed-date-handling

# Changes are in:
# - context-owl-ui/src/pages/Narratives.tsx

# Commit and push
git add context-owl-ui/src/pages/Narratives.tsx
git commit -m "fix: handle reversed narrative timestamps in TimelineBar

- Detect when first_seen > last_updated
- Swap timestamps to render valid timeline bars
- Add comprehensive debug logging for troubleshooting
- Render placeholder bars for invalid data"

git push origin fix/timeline-bar-reversed-date-handling
```

### Step 3: Fix Existing Data (After Backend Deployment)

```bash
# Create a feature branch for the data fix
git checkout -b fix/fix-reversed-narrative-timestamps

# Add the fix script
git add scripts/fix_reversed_narrative_timestamps.py
git commit -m "chore: add script to fix reversed narrative timestamps

- Identifies narratives with first_seen > last_updated
- Swaps timestamps to restore logical consistency
- Includes dry-run mode for safety
- Validates fix after completion"

git push origin fix/fix-reversed-narrative-timestamps

# After merging to main, run the fix script:
python scripts/fix_reversed_narrative_timestamps.py --dry-run
# Review output, then run without --dry-run:
python scripts/fix_reversed_narrative_timestamps.py
```

## Validation

### Frontend Validation

1. Open the Narratives page in the browser
2. Check browser console for `[TimelineBar]` logs
3. Verify timeline bars are now visible (not invisible)
4. Check for any `Invalid bar width` warnings (should be gone after backend fix)

### Backend Validation

```bash
# Check for remaining reversed timestamps
python scripts/fix_reversed_narrative_timestamps.py --dry-run

# Expected output:
# ✓ No narratives with reversed timestamps found
```

### Database Query

```javascript
// In MongoDB shell:
db.narratives.aggregate([
  {
    $addFields: {
      isReversed: { $gt: ["$first_seen", "$last_updated"] }
    }
  },
  {
    $match: { isReversed: true }
  },
  {
    $count: "count"
  }
])

// Expected result: { count: 0 }
```

## Monitoring

After deployment, monitor for:

1. **Warning logs** with `[NARRATIVE VALIDATION]` prefix
   - Indicates validation caught an issue
   - Should be rare after fix is deployed

2. **Frontend console logs** with `[TimelineBar]` prefix
   - Should show valid bar dimensions
   - No more "Invalid bar width" warnings

3. **Timeline bar rendering**
   - All narratives should show visible timeline bars
   - No more invisible/missing bars

## Files Modified

### Backend
- `src/crypto_news_aggregator/db/operations/narratives.py` - Added timestamp validation

### Frontend
- `context-owl-ui/src/pages/Narratives.tsx` - Added reversed date handling and debug logging

### Scripts
- `scripts/fix_reversed_narrative_timestamps.py` - Data fix script (new file)

## Testing Checklist

- [ ] Backend validation prevents new reversed timestamps
- [ ] Frontend gracefully handles any remaining reversed timestamps
- [ ] Data fix script successfully identifies reversed narratives
- [ ] Data fix script successfully swaps timestamps
- [ ] Timeline bars render correctly after fix
- [ ] No "Invalid bar width" warnings in browser console
- [ ] No `[NARRATIVE VALIDATION]` warnings in backend logs (after data fix)

## References

- Frontend debug logs: `[TimelineBar]` prefix in browser console
- Backend validation logs: `[NARRATIVE VALIDATION]` prefix in server logs
- Data corruption example: `first_seen: 2025-10-24T03:53:02`, `last_updated: 2025-10-24T03:30:48`
