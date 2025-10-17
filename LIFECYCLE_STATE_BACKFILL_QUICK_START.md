# Lifecycle State Backfill - Quick Start

## Problem
36 narratives are missing the `lifecycle_state` field, which is required for proper narrative tracking and API responses.

## Solution
Run the backfill script to calculate and set `lifecycle_state` for all missing narratives.

## Quick Commands

```bash
# Navigate to project directory
cd /Users/mc/dev-projects/crypto-news-aggregator

# 1. Check current coverage (optional)
poetry run python scripts/check_lifecycle_state_coverage.py

# 2. Test backfill logic without changes (optional dry run)
poetry run python scripts/test_lifecycle_state_backfill.py

# 3. Run the backfill
poetry run python scripts/backfill_lifecycle_state.py

# 4. Verify results
poetry run python scripts/check_lifecycle_state_coverage.py
```

## Expected Results

**Before backfill:**
- 36 narratives missing `lifecycle_state`
- Coverage: ~XX%

**After backfill:**
- 0 narratives missing `lifecycle_state`
- Coverage: 100%
- All narratives have initialized `lifecycle_history` array

## What Gets Updated

For each narrative missing `lifecycle_state`:

1. **`lifecycle_state`** - Calculated based on:
   - Article count
   - Mention velocity (articles/day)
   - Days since last update
   - Possible values: `emerging`, `rising`, `hot`, `cooling`, `dormant`

2. **`lifecycle_history`** - Initialized with first entry:
   ```json
   [{
     "state": "hot",
     "timestamp": "2025-10-16T22:00:00Z",
     "article_count": 12,
     "mention_velocity": 3.5
   }]
   ```

## Safety

- ✅ **Read-only test available** - Use `test_lifecycle_state_backfill.py` for dry run
- ✅ **Idempotent** - Safe to run multiple times (skips narratives that already have the field)
- ✅ **No data loss** - Only adds fields, doesn't modify existing data
- ✅ **Error handling** - Continues processing even if individual narratives fail
- ✅ **Progress logging** - Shows updates every 5 narratives

## Lifecycle State Logic

The script uses the same logic as `narrative_service.py`:

| Condition | State |
|-----------|-------|
| 7+ days since update | `dormant` |
| 3-7 days since update | `cooling` |
| ≥7 articles OR ≥3.0/day velocity | `hot` |
| ≥1.5/day velocity AND <7 articles | `rising` |
| <4 articles | `emerging` |

## Troubleshooting

**Issue:** Script fails with MongoDB connection error
- **Fix:** Ensure MongoDB is running and `MONGODB_URI` is set in environment

**Issue:** No narratives found to backfill
- **Fix:** All narratives already have `lifecycle_state` - nothing to do!

**Issue:** Some narratives fail to update
- **Fix:** Check logs for specific error messages. Script continues with remaining narratives.

## Files Created

1. `scripts/backfill_lifecycle_state.py` - Main backfill script
2. `scripts/check_lifecycle_state_coverage.py` - Coverage verification
3. `scripts/test_lifecycle_state_backfill.py` - Dry run test
4. `LIFECYCLE_STATE_BACKFILL.md` - Detailed documentation

## Next Steps After Backfill

1. ✅ Verify 100% coverage with check script
2. ✅ Test API endpoints that filter by `lifecycle_state`
3. ✅ Monitor lifecycle transitions in production
4. ✅ Consider adding database index: `db.narratives.createIndex({lifecycle_state: 1})`
