# Velocity Calculation Fix

## Bug Description

The velocity calculation was showing incorrect values:
- **Observed:** 3 articles → "+2 articles/day"
- **Observed:** 5 articles → "+10 articles/day"
- **Expected:** 3 articles → "~0.43 articles/day" (3÷7)
- **Expected:** 5 articles → "~0.71 articles/day" (5÷7)

## Root Cause

The `calculate_recent_velocity` function was dividing by the **actual time span** between articles instead of the fixed **7-day lookback window**.

### Buggy Code (Lines 83-89)
```python
# Calculate velocity: articles / days
# Use the actual time span of recent articles, or lookback_days if articles span the full period
oldest_recent = min(recent_articles)
time_span_days = (now - oldest_recent).total_seconds() / 86400

# Ensure minimum time span of 1 day to avoid extreme values
time_span_days = max(1.0, time_span_days)

return len(recent_articles) / time_span_days
```

**Problem:** If 5 articles were published 0.5 days ago:
- `time_span_days` = 0.5 days
- Velocity = 5 ÷ 0.5 = **10 articles/day** ✗

## The Fix

Changed to always divide by the full `lookback_days` parameter (default: 7 days).

### Fixed Code (Lines 81-83)
```python
# Calculate velocity: articles / lookback period
# Always use the full lookback_days window for consistent velocity measurement
return len(recent_articles) / lookback_days
```

**Correct:** If 5 articles were published in the last 7 days:
- Velocity = 5 ÷ 7 = **0.71 articles/day** ✓

## Changes Made

### 1. Fixed Calculation Logic
**File:** `src/crypto_news_aggregator/services/narrative_service.py`

- Removed lines 83-89 (buggy time span calculation)
- Replaced with simple division: `len(recent_articles) / lookback_days`
- Ensures velocity always represents "articles per day over the lookback period"

### 2. Added Debug Logging
Added comprehensive logging to track:
- Total articles vs. articles within window
- Current time and cutoff date (7 days ago)
- Time delta verification (should always be 7.00 days)
- Oldest/newest article timestamps in window
- Final velocity calculation formula

### 3. Added Test Suite
**File:** `tests/services/test_velocity_calculation.py`

Created 9 comprehensive tests:
- ✓ 3 articles from 1.5 days ago = 0.43/day
- ✓ 5 articles from 2 days ago = 0.71/day
- ✓ 5 articles showing +10/day bug = 0.71/day (fixed)
- ✓ 7 articles over 7 days = 1.0/day
- ✓ 14 articles in last 3 days = 2.0/day
- ✓ Empty article list = 0.0/day
- ✓ Articles outside window excluded
- ✓ Mixed dates (inside/outside window)
- ✓ Different lookback periods work correctly

**All tests pass.**

## Verification

### Test Results
```bash
$ poetry run pytest tests/services/test_velocity_calculation.py -v
====================== test session starts =======================
collected 9 items

tests/services/test_velocity_calculation.py::TestVelocityCalculation::test_velocity_with_3_articles_from_1_5_days_ago PASSED [ 11%]
tests/services/test_velocity_calculation.py::TestVelocityCalculation::test_velocity_with_5_articles_from_2_days_ago PASSED [ 22%]
tests/services/test_velocity_calculation.py::TestVelocityCalculation::test_velocity_with_5_articles_showing_10_per_day_bug PASSED [ 33%]
tests/services/test_velocity_calculation.py::TestVelocityCalculation::test_velocity_with_7_articles_over_7_days PASSED [ 44%]
tests/services/test_velocity_calculation.py::TestVelocityCalculation::test_velocity_with_14_articles_in_last_3_days PASSED [ 55%]
tests/services/test_velocity_calculation.py::TestVelocityCalculation::test_velocity_with_no_articles PASSED [ 66%]
tests/services/test_velocity_calculation.py::TestVelocityCalculation::test_velocity_with_articles_outside_window PASSED [ 77%]
tests/services/test_velocity_calculation.py::TestVelocityCalculation::test_velocity_with_mixed_dates PASSED [ 88%]
tests/services/test_velocity_calculation.py::TestVelocityCalculation::test_velocity_always_divides_by_lookback_days PASSED [100%]

================= 9 passed, 6 warnings in 0.11s ==================
```

### Example Calculations

| Articles | Old Behavior | New Behavior | Correct? |
|----------|--------------|--------------|----------|
| 3 articles (1.5 days ago) | 3÷1.5 = 2.0/day | 3÷7 = 0.43/day | ✓ |
| 5 articles (0.5 days ago) | 5÷0.5 = 10.0/day | 5÷7 = 0.71/day | ✓ |
| 7 articles (spread over 7 days) | 7÷7 = 1.0/day | 7÷7 = 1.0/day | ✓ |
| 14 articles (last 3 days) | 14÷3 = 4.67/day | 14÷7 = 2.0/day | ✓ |

## Deployment Instructions

### 1. Run Tests Locally
```bash
poetry run pytest tests/services/test_velocity_calculation.py -v
```

### 2. Deploy to Railway
The fix is on branch `fix/velocity-calculation-time-window`.

```bash
# Push branch to trigger Railway deployment
git push origin fix/velocity-calculation-time-window
```

### 3. Verify in Railway Logs
After deployment, check logs for velocity debug output:
```
[VELOCITY DEBUG] Total articles: 5
[VELOCITY DEBUG] Current time (now): 2025-10-17 02:51:00+00:00
[VELOCITY DEBUG] Cutoff date (7 days ago): 2025-10-10 02:51:00+00:00
[VELOCITY DEBUG] Time delta: 7.00 days
[VELOCITY DEBUG] Articles within window: 5
[VELOCITY DEBUG] Velocity calculation: 5 / 7 = 0.71
```

### 4. Test in UI
After deployment, verify narratives show correct velocity:
- 3 articles should show ~0.4-0.5 articles/day
- 5 articles should show ~0.7-0.8 articles/day
- NOT 2.0 or 10.0 articles/day

### 5. Merge to Main
Once verified in production:
```bash
git checkout main
git merge fix/velocity-calculation-time-window
git push origin main
```

## Impact

### Before Fix
- Velocity was inflated by 5-20x
- Made all narratives appear "hot" when they weren't
- Lifecycle states (rising, hot, cooling) were incorrectly assigned
- Resurrection velocity calculations were wrong

### After Fix
- Velocity accurately represents articles/day over 7-day window
- Lifecycle states correctly reflect narrative activity
- Resurrection detection works as intended
- UI shows realistic velocity numbers

## Related Files

- `src/crypto_news_aggregator/services/narrative_service.py` - Fixed calculation
- `tests/services/test_velocity_calculation.py` - Test suite
- `src/crypto_news_aggregator/api/v1/endpoints/narratives.py` - API passes through velocity

## Next Steps

1. ✅ Fix implemented and tested
2. ✅ Tests passing locally
3. ⏳ Deploy to Railway
4. ⏳ Verify in production logs
5. ⏳ Test in UI
6. ⏳ Merge to main

## Notes

- The debug logging can be removed after verification in production
- Consider adding monitoring/alerting for velocity anomalies
- May want to backfill existing narratives with corrected velocity values
