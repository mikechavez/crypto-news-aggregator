# Signal Calculation Debug Summary

## Issue
Velocity and source_count were showing 0 for all signals, even though entity mentions existed in the database.

## Root Causes & Fixes

### 1. ❌ Wrong Field Name: `timestamp` vs `created_at`

**Files affected:**
- `src/crypto_news_aggregator/services/signal_service.py` (lines 43, 50)
- `src/crypto_news_aggregator/worker.py` (lines 52, 86)

**Problem:**
```python
# ❌ WRONG - querying non-existent field
"timestamp": {"$gte": one_hour_ago}
```

**Fix:**
```python
# ✅ CORRECT - using actual field name
"created_at": {"$gte": one_hour_ago}
```

**Impact:** All time-based queries returned 0 results because the field didn't exist.

---

### 2. ❌ Timezone Mismatch

**File:** `src/crypto_news_aggregator/services/signal_service.py` (line 37)

**Problem:**
MongoDB stores datetimes as UTC but returns them as **naive** (no timezone), while the service was comparing with **timezone-aware** datetimes. This causes silent comparison failures.

```python
# ❌ WRONG - timezone-aware datetime
now = datetime.now(timezone.utc)  # Has tzinfo=UTC
# MongoDB returns: datetime(2025, 10, 4, 18, 30)  # tzinfo=None
# Comparison fails silently
```

**Fix:**
```python
# ✅ CORRECT - naive datetime to match MongoDB
now = datetime.now(timezone.utc).replace(tzinfo=None)
```

**Impact:** Datetime comparisons failed, returning 0 results even when data existed.

---

### 3. ❌ Inefficient Source Diversity Calculation

**File:** `src/crypto_news_aggregator/services/signal_service.py` (lines 70-92)

**Problem:**
Complex aggregation pipeline that looked up articles collection, but entity mentions already have `source` field directly.

```python
# ❌ WRONG - complex lookup through articles
pipeline = [
    {"$match": {"entity": entity, "is_primary": True}},
    {"$group": {"_id": "$article_id"}},
]
article_ids = [...]
# Then query articles collection for sources
```

**Fix:**
```python
# ✅ CORRECT - direct distinct query
sources = await entity_mentions_collection.distinct(
    "source",
    {"entity": entity, "is_primary": True}
)
return len(sources)
```

**Impact:** Source count was always 0 due to incorrect aggregation logic.

---

## Verification Results

### Before Fix:
```json
{
  "velocity": 0.0,
  "source_count": 0,
  "score": 2.75
}
```

### After Fix:
```json
{
  "velocity": 0.0,  // Correct (no recent mentions)
  "source_count": 1,  // ✅ Fixed!
  "score": 2.82
}
```

**Note:** Velocity is 0 because all mentions are from 3 days ago. This is expected behavior.

---

## Files Modified

1. **src/crypto_news_aggregator/services/signal_service.py**
   - Line 37: Use naive datetime
   - Lines 43, 50: Changed `timestamp` → `created_at`
   - Lines 70-92: Simplified source diversity calculation

2. **src/crypto_news_aggregator/worker.py**
   - Line 48: Use naive datetime
   - Line 52: Changed `timestamp` → `created_at`
   - Line 86: Changed `timestamp` → `created_at` in sort

3. **tests/services/test_signal_service.py**
   - Updated tests to reflect new source diversity logic
   - Removed dependency on articles collection

---

## Testing & Verification

### Run Verification Script:
```bash
poetry run python scripts/verify_signal_fix.py
```

### Expected Output:
```
✅ FIXES VERIFIED:
   1. Field name: 'timestamp' → 'created_at' ✓
   2. Timezone handling: naive datetime comparison ✓
   3. Source diversity: direct distinct() query ✓
```

### Debug Scripts Created:
- `scripts/debug_signal_calculation.py` - Inspect raw data
- `scripts/test_signal_fix.py` - Test individual functions
- `scripts/verify_signal_fix.py` - Comprehensive verification

---

## Key Learnings

### MongoDB Datetime Behavior:
- MongoDB stores datetimes as UTC timestamps
- Motor (async driver) returns them as **naive** Python datetimes
- Always use naive datetimes for MongoDB queries: `datetime.now(timezone.utc).replace(tzinfo=None)`

### Entity Mention Schema:
- Entity mentions have `created_at` field (not `timestamp`)
- Entity mentions have `source` field directly (no need to lookup articles)
- Primary entities are marked with `is_primary: True`

### Signal Calculation Logic:
- **Velocity** = (mentions in last 1h) / (mentions in last 24h / 24)
- **Source diversity** = count of unique sources
- **Sentiment** = average, min, max, and divergence of sentiment scores

---

## Next Steps

1. **Update stored signals**: Run the worker to recalculate all signal scores
   ```bash
   poetry run python -m crypto_news_aggregator.worker
   ```

2. **Fetch fresh data**: Run RSS fetcher to get recent articles
   ```bash
   # Worker will automatically trigger RSS fetching
   ```

3. **Monitor**: Check that velocity increases when new mentions arrive

---

## Related Documentation

- Entity mentions: `src/crypto_news_aggregator/db/operations/entity_mentions.py`
- Signal service: `src/crypto_news_aggregator/services/signal_service.py`
- Background worker: `src/crypto_news_aggregator/worker.py`
- Full fix details: `SIGNAL_CALCULATION_FIX.md`
