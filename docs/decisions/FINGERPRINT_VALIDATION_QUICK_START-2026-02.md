# Fingerprint Validation - Quick Start Guide

## What Was Added

✓ **Application-level validation** in `narrative_service.py` (lines 880-883)  
✓ **Database unique index** on `fingerprint.nucleus_entity`  
✓ **Test suite** to verify validation works correctly

## Quick Commands

### 1. Test Validation Logic
```bash
poetry run python scripts/test_fingerprint_validation.py
```
**Expected**: All 6 tests pass ✓

### 2. Check for Duplicate Narratives
```bash
poetry run python scripts/check_duplicate_narratives.py
```
**Expected**: Zero duplicates (or list of duplicates to clean)

### 3. Clean Duplicates (if needed)
```bash
poetry run python scripts/clean_duplicate_narratives.py
```
**Expected**: Duplicates merged or removed

### 4. Create Database Index
```bash
poetry run python scripts/add_fingerprint_validation_index.py
```
**Expected**: Index `idx_fingerprint_nucleus_entity_unique` created

## What It Does

### Prevents
- ❌ NULL `nucleus_entity` values
- ❌ Missing `nucleus_entity` key
- ❌ Empty fingerprints
- ❌ Duplicate narratives

### Allows
- ✅ Valid narratives with proper `nucleus_entity`
- ✅ Backward compatibility (sparse index)

## Error Messages

### If validation fails:
```
ERROR: Cannot create narrative - invalid fingerprint: {...}
ValueError: Narrative fingerprint must have a valid nucleus_entity
```

### If duplicates exist when creating index:
```
✗ Error: Cannot create unique index - duplicate values exist!
```
**Action**: Run duplicate cleanup scripts first

## Deployment Order

1. ✅ Deploy code changes (validation in `narrative_service.py`)
2. ✅ Check for duplicates
3. ✅ Clean duplicates (if any)
4. ✅ Create database index
5. ✅ Monitor logs

## Monitoring

```bash
# Check for validation errors
grep "Cannot create narrative" app.log

# Check narrative creation
grep "Created new narrative" app.log | tail -20

# Verify index exists (MongoDB shell)
db.narratives.getIndexes()
```

## Files Changed

- `src/crypto_news_aggregator/services/narrative_service.py` - Validation logic
- `scripts/add_fingerprint_validation_index.py` - Index creation
- `scripts/test_fingerprint_validation.py` - Test suite

## Rollback

If needed, remove validation:
```python
# Comment out lines 880-883 in narrative_service.py
# if not fingerprint or not fingerprint.get('nucleus_entity'):
#     logger.error(f"Cannot create narrative - invalid fingerprint: {fingerprint}")
#     raise ValueError("Narrative fingerprint must have a valid nucleus_entity")
```

Remove index:
```javascript
db.narratives.dropIndex("idx_fingerprint_nucleus_entity_unique")
```

## Success Indicators

- ✓ All tests pass
- ✓ Index created successfully
- ✓ No validation errors in logs
- ✓ No duplicate narratives
- ✓ Narrative creation continues normally

## Full Documentation

See `FINGERPRINT_VALIDATION_IMPLEMENTATION.md` for complete details.
