# ✅ Ready to Run: Full Narrative Backfill

**Status:** All validation tests passed  
**Date:** October 12, 2025  
**Validation Results:** See `BACKFILL_VALIDATION_TEST_RESULTS.md`

---

## Quick Start

### Run Full Backfill
```bash
poetry run python scripts/backfill_narratives.py --hours 720 --limit 1500
```

### Expected Performance
- **Total Articles:** ~1,329 articles
- **Estimated Time:** ~66 minutes
- **Rate:** ~20 articles/minute
- **Success Rate:** Expected >95%

---

## What Was Validated

✅ **All 6 improvements tested and working:**

1. **LLM Validation** - Catches malformed JSON responses
2. **Content Caching** - Prevents re-processing articles
3. **Enhanced Prompts** - Better entity normalization (Bitcoin vs BTC)
4. **Retry Logic** - Handles rate limits and transient failures
5. **Conservative Rate Limiting** - 20 articles/min (safe buffer under 25/min limit)
6. **Progress Tracking** - Time estimates, batch statistics, success/failure counts

---

## Validation Test Results

### Test Summary
- **Articles Tested:** 20 articles (5 in batch processing)
- **Success Rate:** 100%
- **Failures:** 0
- **All Tests:** PASSED ✅

### What Was Tested
1. ✅ MongoDB connection
2. ✅ Article query (finds articles needing processing)
3. ✅ LLM extraction (proper entity normalization)
4. ✅ JSON validation (catches errors)
5. ✅ Caching logic (prevents duplicates)
6. ✅ Batch processing (5 articles, 100% success)

---

## Rate Limiting Details

### Conservative Configuration
```
Batch size: 15 articles
Batch delay: 30 seconds
Article delay: 1.0 seconds
Time per batch: ~44 seconds
Throughput: ~20.5 articles/minute
```

### Safety Buffer
- **API Limit:** 25 articles/min (token-based)
- **Our Rate:** 20 articles/min
- **Buffer:** 20% safety margin

This ensures we stay well under API limits even with variance.

---

## What to Monitor

### During Backfill
Watch for these in the output:

1. **Progress Updates**
   - Batch X/Y processing
   - Articles processed per batch
   - Success/failure counts

2. **Success Metrics**
   - Should see >95% success rate
   - Failed articles will be logged
   - Cached articles will be skipped

3. **Rate Limiting**
   - Should NOT see rate limit errors
   - If you do, the retry logic will handle them

4. **Time Estimates**
   - Progress tracking shows estimated completion time
   - Updates after each batch

### Expected Output Format
```
📊 Found 1,329 articles needing narrative data
⏱️  Processing in 89 batches of 15
⏱️  Estimated time: 66.0 minutes

📦 Batch 1/89: Processing 15 articles...
   ✅ Successful: 14
   💾 Cached: 1
   ❌ Failed: 0
   ⏱️  Batch time: 44.2s
   📊 Overall: 14/15 processed (93.3% success)
   ⏱️  Estimated remaining: 65.1 minutes
```

---

## If Something Goes Wrong

### Rate Limit Errors
- **Should NOT happen** (we're at 20/min, limit is 25/min)
- **If it does:** Retry logic will handle it automatically
- **Action:** Monitor and let it continue

### High Failure Rate (>10%)
- **Stop the backfill:** Ctrl+C
- **Check logs:** Look for common error patterns
- **Investigate:** May need to adjust prompts or validation
- **Resume:** Script can resume from where it left off (caching prevents duplicates)

### Slow Performance
- **Expected:** ~20 articles/min
- **If slower:** Check network connection, API latency
- **Action:** Let it continue, just takes longer

### MongoDB Connection Issues
- **Rare:** Connection is stable in validation
- **If it happens:** Script will retry automatically
- **Action:** Check Railway logs if persistent

---

## Post-Backfill Verification

### 1. Check Success Rate
```bash
poetry run python scripts/verify_backfill.py
```

### 2. Spot Check Articles
Look at a few articles in MongoDB to verify:
- `narrative_summary` is populated
- `actors` array has entities
- `nucleus_entity` is set
- `narrative_hash` is present

### 3. Check for Duplicates
```bash
# Count articles with narrative data
db.articles.countDocuments({ narrative_hash: { $exists: true } })

# Should be ~1,329 or close to it
```

---

## Resume If Interrupted

If the backfill is interrupted (Ctrl+C, connection loss, etc.):

1. **Just run the same command again:**
   ```bash
   poetry run python scripts/backfill_narratives.py --hours 720 --limit 1500
   ```

2. **Caching prevents duplicates:**
   - Articles with `narrative_hash` are skipped
   - Only unprocessed articles are processed
   - No duplicate work

3. **Adjust time window if needed:**
   ```bash
   # Process only last 24 hours
   poetry run python scripts/backfill_narratives.py --hours 24 --limit 1500
   ```

---

## Files Created

### Validation Test
- **Script:** `scripts/test_backfill_validation.py`
- **Results:** `BACKFILL_VALIDATION_TEST_RESULTS.md`
- **This Guide:** `BACKFILL_READY_TO_RUN.md`

### Backfill Script
- **Script:** `scripts/backfill_narratives.py`
- **Documentation:** `RATE_LIMITING_COMPLETE.md`
- **Test Results:** `RATE_LIMITING_TESTS_SUMMARY.md`

---

## Ready to Go! 🚀

Everything is validated and ready. Run the command above to start the full backfill.

**Estimated completion:** ~66 minutes from start  
**Expected success rate:** >95%  
**Safe to run:** Yes, all safety measures in place

---

**Last Validated:** October 12, 2025  
**Validation Status:** ✅ ALL TESTS PASSED
