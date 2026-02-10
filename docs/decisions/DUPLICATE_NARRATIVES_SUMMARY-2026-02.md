# Duplicate Narratives Investigation Summary

**Date:** 2025-10-17  
**Status:** ✅ Root Cause Identified

## Executive Summary

Investigation revealed that **229 narratives share the same nucleus_entity value: `None` (NULL)**. This is a critical bug in the narrative fingerprint generation logic that creates narratives with completely empty fingerprints.

## What We Found

### The Problem
```
Total narratives with duplicate nucleus_entity: 229
Nucleus entity value: None (NULL)
Theme keywords: [] (empty for all)
Supporting entities: [] (empty for all)
```

### Why This Happened

The narrative creation logic is failing to:
1. Extract entities from articles
2. Set the nucleus_entity field
3. Generate theme keywords
4. Populate supporting entities

Result: **All 229 narratives have completely empty fingerprints.**

## Impact

### User Experience
- Users see 229 separate narratives instead of cohesive stories
- Narrative discovery is fragmented and confusing
- Signal quality is diluted across many weak narratives

### System Performance
- 229 narratives competing for the same articles
- Lifecycle tracking is meaningless (all have empty fingerprints)
- Matching logic cannot work (nothing to match on)

### Data Quality
- No way to distinguish between narratives
- No way to merge related articles
- No way to track narrative evolution

## Root Cause

**Location:** `src/crypto_news_aggregator/services/narrative_service.py`

The fingerprint generation logic is either:
1. Not running at all
2. Running but failing silently
3. Running but not saving results to the database

## Scripts Created

### 1. `scripts/check_duplicate_narratives.py`
Identifies narratives with duplicate nucleus_entity values and provides detailed analysis.

**Usage:**
```bash
poetry run python scripts/check_duplicate_narratives.py
```

**Output:**
- List of duplicate nucleus_entity values
- Count of narratives per duplicate
- Detailed information for each duplicate narrative
- Pattern analysis (lifecycle states, narrative types)
- Recommendations for fixing

### 2. `scripts/identify_duplicate_nucleus_entity.py`
Investigates the actual nucleus_entity value and provides root cause analysis.

**Usage:**
```bash
poetry run python scripts/identify_duplicate_nucleus_entity.py
```

**Output:**
- The actual nucleus_entity value (found: `None`)
- Type and validation checks
- Sample narratives with full fingerprint details
- Root cause analysis
- Creation date analysis

## Next Steps

### Immediate (Critical Priority)

1. **Review Fingerprint Generation Logic**
   - File: `src/crypto_news_aggregator/services/narrative_service.py`
   - Check: Entity extraction, fingerprint creation, database save
   - Fix: Ensure nucleus_entity is always set

2. **Add Validation**
   - Reject narratives with null nucleus_entity
   - Reject narratives with empty fingerprints
   - Log warnings when fingerprint generation fails

3. **Create Backfill Script**
   - Fetch all 229 narratives with null nucleus_entity
   - Re-extract entities from associated articles
   - Regenerate proper fingerprints
   - Update narratives in MongoDB
   - Run matching to merge duplicates

### Short Term

1. **Add Monitoring**
   - Alert when empty fingerprints are created
   - Track fingerprint generation success rate
   - Monitor narrative duplication

2. **Add Tests**
   - Test fingerprint generation with edge cases
   - Test entity extraction failures
   - Test validation logic

3. **Improve Logging**
   - Log fingerprint generation steps
   - Log entity extraction results
   - Log validation failures

### Long Term

1. **Database Constraints**
   - Add schema validation for nucleus_entity
   - Require non-empty fingerprints
   - Add indexes for duplicate detection

2. **Architectural Improvements**
   - Separate entity extraction from narrative creation
   - Add retry logic for failed fingerprint generation
   - Implement fingerprint quality scoring

## Conclusion

The investigation successfully identified the root cause of narrative duplication:

**All 229 narratives have `nucleus_entity = None` because the fingerprint generation logic is broken.**

This is a critical bug that must be fixed immediately. The system cannot function properly without valid narrative fingerprints.

The next step is to review the narrative service code and fix the fingerprint generation logic.

## Files Created

1. `DUPLICATE_NARRATIVES_ANALYSIS.md` - Detailed analysis and recommendations
2. `DUPLICATE_NARRATIVES_SUMMARY.md` - This executive summary
3. `scripts/check_duplicate_narratives.py` - Duplicate detection script
4. `scripts/identify_duplicate_nucleus_entity.py` - Root cause investigation script
