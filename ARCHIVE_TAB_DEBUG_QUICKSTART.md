# Archive Tab Debug - Quick Start

## The Problem
Archive tab shows "2 articles" but no narrative cards are displayed.

## Quick Diagnosis (30 seconds)

Run this single command:
```bash
cd /Users/mc/dev-projects/crypto-news-aggregator
poetry run python scripts/analyze_archive_issue.py
```

This will tell you **exactly** what the issue is.

## What the Script Checks

1. **Database**: How many dormant narratives exist?
2. **API**: What does the endpoint return?
3. **Date Range**: Are dormant narratives within the 30-day window?
4. **The "2 articles" mystery**: Which narrative has 2 articles?

## Expected Output

### ✅ If Working
```
Dormant narratives: 5
Dormant narratives (last 30 days): 3
API returned: 3 narratives
Total articles across all narratives: 12

✓ Database has dormant narratives
```

### ❌ If Broken - Scenario 1: No Dormant Narratives
```
Dormant narratives: 0
API returned: 0 narratives

❌ ISSUE IDENTIFIED: No dormant narratives in database

Solution:
  - Check lifecycle transition logic
  - Run lifecycle state backfill if needed
```

**Fix:**
```bash
# Check what lifecycle states exist
poetry run python scripts/check_dormant_narratives.py

# If narratives exist but aren't marked dormant, run migration
# (You may need to create this migration script)
```

### ❌ If Broken - Scenario 2: Dormant But Outside Window
```
Dormant narratives: 5
Dormant narratives (last 30 days): 0
API returned: 0 narratives

❌ ISSUE IDENTIFIED: Dormant narratives exist but none in last 30 days

Solution:
  - Increase the 'days' parameter in the frontend
```

**Fix:** Edit `context-owl-ui/src/pages/Narratives.tsx` line 63:
```typescript
// Change from 30 to 90 days
const result = viewMode === 'archive' 
  ? await narrativesAPI.getArchivedNarratives(50, 90)  // Changed from 30
  : await narrativesAPI.getNarratives();
```

### ❌ If Broken - Scenario 3: Old Schema
```
Lifecycle state distribution:
  null/missing: 150
  emerging: 20
  dormant: 5

⚠ WARNING: Some narratives missing lifecycle_state field

Solution:
  - Run migration to add lifecycle_state to old narratives
```

**Fix:**
```bash
# Run the lifecycle state backfill
poetry run python scripts/backfill_lifecycle_states.py
```

## Additional Debug Steps

### Check Frontend Logs
1. Open the frontend in browser
2. Open DevTools Console (F12)
3. Click Archive tab
4. Look for these messages:
   ```
   [DEBUG] archive API returned: X narratives
   [DEBUG] Archive narratives lifecycle_state values: [...]
   ```

### Check Backend Logs
If deployed on Railway:
```bash
# Check Railway logs for these messages:
[DEBUG] Total narratives in database: X
[DEBUG] Lifecycle state distribution: [...]
[DEBUG] Found X archived narratives
```

### Check API Directly
```bash
# Test the API endpoint directly
curl "http://localhost:8000/api/v1/narratives/archived?limit=50&days=30" | jq '.'

# Or if deployed:
curl "https://your-app.railway.app/api/v1/narratives/archived?limit=50&days=30" | jq '.'
```

## All Debug Scripts

1. **`scripts/analyze_archive_issue.py`** - ⭐ **Start here** - Comprehensive analysis
2. **`scripts/check_dormant_narratives.py`** - Database-only check
3. **`scripts/test_archive_api.py`** - API endpoint test
4. **`scripts/run_archive_debug.sh`** - Run all scripts

## Common Issues & Fixes

| Issue | Symptom | Fix |
|-------|---------|-----|
| No dormant narratives | API returns 0 | Run lifecycle migration |
| Outside date window | Dormant exists but not recent | Increase days parameter |
| Old schema | Missing lifecycle_state field | Run backfill script |
| Frontend filtering | API returns data but UI empty | Check browser console |

## Files Created for Debugging

- ✅ `scripts/analyze_archive_issue.py` - Main diagnostic script
- ✅ `scripts/check_dormant_narratives.py` - MongoDB query script
- ✅ `scripts/test_archive_api.py` - API test script
- ✅ `scripts/run_archive_debug.sh` - Run all tests
- ✅ `scripts/debug_archive_tab.md` - Detailed guide
- ✅ `ARCHIVE_TAB_DEBUG_SUMMARY.md` - Complete analysis
- ✅ `ARCHIVE_TAB_DEBUG_QUICKSTART.md` - This file

## Need More Help?

See `ARCHIVE_TAB_DEBUG_SUMMARY.md` for:
- Complete data flow analysis
- Code location references
- Detailed debugging steps
- Expected vs actual behavior

## TL;DR

```bash
# Run this one command to diagnose the issue:
poetry run python scripts/analyze_archive_issue.py

# Then follow the diagnosis output to fix it
```
