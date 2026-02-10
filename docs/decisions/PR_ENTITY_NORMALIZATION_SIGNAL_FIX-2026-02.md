# PR: Fix Entity Normalization in Signal Calculation

## Problem Statement

**Production Issue:** The Context Owl UI displays duplicate entities that should be merged:
- #3: "$DOGE" (998% score)
- #6: "Dogecoin" (998% score)

These should appear as ONE entity, not two separate signals.

## Root Cause Analysis

Entity normalization was implemented in `rss_fetcher.py` to normalize entity mentions when they're created. However, the **signal calculation pipeline** in `worker.py` was grouping by raw entity names from the database, not by canonical names.

**The Bug:**
```python
# worker.py (lines 50-62) - OLD CODE
pipeline = [
    {"$match": {"created_at": {"$gte": thirty_min_ago}, "is_primary": True}},
    {"$group": {
        "_id": {
            "entity": "$entity",  # ❌ Groups by raw name from DB
            "entity_type": "$entity_type"
        }
    }},
]
```

Even though `entity_mentions` were being normalized when created, if any old data existed with variants like "$DOGE", the signal calculation would create separate scores for "$DOGE" and "Dogecoin".

## Solution

### 1. **Fix Signal Calculation Pipeline** (`worker.py`)

Changed from MongoDB aggregation to Python-based normalization:

```python
# Fetch all recent primary entity mentions
cursor = entity_mentions_collection.find({
    "created_at": {"$gte": thirty_min_ago},
    "is_primary": True
})

# Normalize entities and group by canonical name
entity_map = {}  # canonical_name -> entity_type
async for mention in cursor:
    raw_entity = mention.get("entity")
    canonical_entity = normalize_entity_name(raw_entity)  # ✅ Normalize
    
    if canonical_entity not in entity_map:
        entity_map[canonical_entity] = entity_type
```

**Why this works:** All variants ("$DOGE", "DOGE", "doge", "Dogecoin") normalize to "Dogecoin" before grouping, ensuring only one signal score is created.

### 2. **Add Defensive Normalization** (`signal_service.py`)

Added normalization in `calculate_signal_score()` as a defensive measure:

```python
async def calculate_signal_score(entity: str) -> Dict[str, Any]:
    # Normalize entity name to canonical form (defensive measure)
    canonical_entity = normalize_entity_name(entity)
    if canonical_entity != entity:
        logger.info(f"Signal score calculation: normalized '{entity}' -> '{canonical_entity}'")
    
    # Get all component metrics using canonical name
    velocity = await calculate_velocity(canonical_entity)
    diversity = await calculate_source_diversity(canonical_entity)
    sentiment_metrics = await calculate_sentiment_metrics(canonical_entity)
```

### 3. **Production Migration Script**

Created `scripts/migrate_signal_scores_normalization.py` to:
1. Verify `entity_mentions` are normalized
2. Delete all existing `signal_scores` (they'll be regenerated)
3. Recalculate signal scores using canonical entity names

**Usage:**
```bash
# Dry run (safe, shows what would happen)
python scripts/migrate_signal_scores_normalization.py --dry-run

# Production execution
python scripts/migrate_signal_scores_normalization.py --production
```

### 4. **Comprehensive Tests**

Added `tests/services/test_signal_normalization.py` with 5 test cases:
- ✅ Verify signal calculation normalizes entity names
- ✅ Verify canonical names pass through unchanged
- ✅ Verify multiple variants normalize to same entity
- ✅ Verify Bitcoin variants normalize correctly
- ✅ Verify unknown entities pass through unchanged

**All tests pass:** `5 passed in 0.05s`

## Files Changed

### Modified
- `src/crypto_news_aggregator/worker.py` - Fixed signal calculation pipeline
- `src/crypto_news_aggregator/services/signal_service.py` - Added defensive normalization

### Added
- `scripts/migrate_signal_scores_normalization.py` - Production migration script
- `tests/services/test_signal_normalization.py` - Test coverage for normalization

## Deployment Plan

Following development practices rules, this fix requires:

### Pre-Deployment Checklist
- [x] Feature branch created: `fix/entity-normalization-signal-calculation`
- [x] Code changes implemented and tested
- [x] Tests written and passing (5/5 tests pass)
- [x] Migration script created with dry-run capability
- [ ] Run full test suite locally
- [ ] Merge to main via PR
- [ ] Deploy to Railway
- [ ] Run migration script in production
- [ ] Verify in production UI

### Post-Deployment Verification

**Step 1: Deploy Code Changes**
```bash
# Merge PR to main
# Railway auto-deploys from main branch
# Monitor Railway logs for successful deployment
```

**Step 2: Run Migration Script in Production**
```bash
# SSH into Railway or run via Railway CLI
python scripts/migrate_signal_scores_normalization.py --production
```

**Step 3: Verify Fix**
1. Wait 2 minutes for signal worker to run
2. Check UI at https://context-owl.vercel.app
3. Verify "$DOGE" and "Dogecoin" are merged into ONE entity
4. Check Railway logs for normalization messages:
   ```
   Signal calculation: normalized '$DOGE' -> 'Dogecoin'
   ```

**Step 4: Monitor Production**
- Check for any errors in Railway logs
- Verify signal scores are being calculated correctly
- Confirm no duplicate entities appear in UI

## Expected Impact

### Before Fix
```
Top Signals:
#3: "$DOGE" (998% score)
#6: "Dogecoin" (998% score)
#8: "$BTC" (850% score)
#12: "Bitcoin" (850% score)
```

### After Fix
```
Top Signals:
#1: "Dogecoin" (998% score)  ← Merged from $DOGE + Dogecoin
#2: "Bitcoin" (850% score)   ← Merged from $BTC + Bitcoin
```

## Rollback Plan

If issues occur in production:

1. **Immediate:** Revert the PR merge
2. **Railway:** Will auto-deploy previous version
3. **Database:** Signal scores will regenerate automatically (no permanent damage)

## Testing Evidence

```bash
$ poetry run pytest tests/services/test_signal_normalization.py -v

tests/services/test_signal_normalization.py::test_calculate_signal_score_normalizes_entity PASSED
tests/services/test_signal_normalization.py::test_calculate_signal_score_with_canonical_name PASSED
tests/services/test_signal_normalization.py::test_multiple_variants_normalize_to_same_entity PASSED
tests/services/test_signal_normalization.py::test_bitcoin_variants_normalize PASSED
tests/services/test_signal_normalization.py::test_unknown_entity_passes_through PASSED

=============== 5 passed in 0.05s ===============
```

## Related Issues

This fix completes the entity normalization work:
- ✅ Entity normalization service created
- ✅ RSS fetcher normalizes entities when creating mentions
- ✅ **Signal calculation now uses canonical names** (this PR)

## Notes

- The fix is **backward compatible** - old entity mentions will be normalized during signal calculation
- The migration script is **idempotent** - safe to run multiple times
- The fix includes **defensive normalization** at multiple layers for robustness
- All changes follow the development practices rules (feature branch, tests, migration script)
