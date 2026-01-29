# "Unknown" Entity Bug - Diagnostic Report

## Executive Summary

**Bug Confirmed**: 110 out of 110 narratives (100%) have **missing `nucleus_entity` field** in the database.

**Root Cause**: The `nucleus_entity` field is being computed correctly but **NOT saved to the narrative document** in MongoDB. It's only stored inside the `fingerprint` subdocument, not as a top-level field.

**Impact**: 
- Narrative matching is severely degraded (can't match on nucleus_entity)
- Quality audits show "Unknown" for 94% of narratives
- Frontend/API queries can't filter or group by nucleus_entity
- Duplicate narratives are not being detected properly

---

## Diagnostic Findings

### 1. Database State Analysis

**Query Results** (from `diagnose_unknown_entity_bug.py`):
- Total narratives: 110
- nucleus_entity field MISSING: 110 (100%)
- nucleus_entity with actual values: 0 (0%)

**Sample Narrative**:
- Title: "Defi Adoption Narrative"
- nucleus_entity: FIELD DOES NOT EXIST (BUG)
- fingerprint.nucleus_entity: "defi_adoption" (CORRECT)

**Sample Article** (from same narrative):
- Title: "Senate Democrats' DeFi gambit..."
- nucleus_entity: "Senate Democrats" (Articles have it correctly)

### 2. Code Flow Analysis

#### Path 1: Narrative Creation (NEW narratives)

**File**: `src/crypto_news_aggregator/services/narrative_service.py`

**Line 779-786**: Generate narrative from cluster
- `generate_narrative_from_cluster()` correctly sets `nucleus_entity` in the returned dict
- Fingerprint is added with correct nucleus_entity

**Line 862-888**: Save to database
```python
narrative_doc = {
    "theme": theme,
    "title": narrative_data["title"],
    "summary": narrative_data["summary"],
    "entities": narrative_data.get("actors", [])[:10],
    "fingerprint": fingerprint,
    # BUG: No "nucleus_entity" field here!
}
```

**The Problem**: The `narrative_doc` dictionary being inserted into MongoDB does NOT include `nucleus_entity` as a top-level field.

#### Path 2: Narrative Updates (EXISTING narratives)

**Line 747-756**: Update existing narrative
```python
update_data = {
    'article_ids': combined_article_ids,
    'fingerprint': fingerprint,
    # BUG: No 'nucleus_entity' field here either!
}
```

**The Problem**: Updates also don't include `nucleus_entity` as a top-level field.

### 3. Why This Breaks Matching

The fingerprint similarity calculation (line 166-176 in narrative_themes.py) relies on comparing `nucleus_entity` between fingerprints:

```python
nucleus1 = fingerprint1.get('nucleus_entity', '')
nucleus2 = fingerprint2.get('nucleus_entity', '')
nucleus_match_score = 1.0 if nucleus1 and nucleus2 and nucleus1 == nucleus2 else 0.0
```

This works because fingerprints DO have nucleus_entity. However:
- Database queries can't filter by nucleus_entity (field doesn't exist)
- Audit scripts show "Unknown" (using `.get('nucleus_entity', 'Unknown')`)
- API responses don't include nucleus_entity
- Frontend can't display or group by nucleus_entity

---

## Comparison: Working vs Broken Narratives

### All Narratives (Broken)
- Created: 2025-10-12 to 2025-10-19
- nucleus_entity field: MISSING
- fingerprint.nucleus_entity: Present and correct
- Pattern: 100% of narratives affected

### Expected Behavior
Each narrative should have:
```json
{
  "nucleus_entity": "SEC",  // Top-level field
  "fingerprint": {
    "nucleus_entity": "SEC",  // Also in fingerprint
    "top_actors": ["SEC", "Binance"],
    "key_actions": ["filed lawsuit"]
  }
}
```

---

## Root Cause

The bug was introduced when the fingerprint-based matching system was implemented. The code:

1. ✅ Correctly extracts nucleus_entity from articles
2. ✅ Correctly aggregates nucleus_entity in clusters
3. ✅ Correctly sets nucleus_entity in `generate_narrative_from_cluster()`
4. ✅ Correctly includes nucleus_entity in fingerprint
5. ❌ **FAILS to include nucleus_entity in the database document**

The field exists in memory (in the `narrative` dict returned by `generate_narrative_from_cluster`) but is never written to MongoDB.

---

## Fix Required

### Code Changes

**File**: `src/crypto_news_aggregator/services/narrative_service.py`

#### Fix 1: Add nucleus_entity to new narrative creation (line 862-888)

```python
narrative_doc = {
    "theme": theme,
    "title": narrative_data["title"],
    "summary": narrative_data["summary"],
    "nucleus_entity": narrative_data.get("nucleus_entity", ""),  # ADD THIS
    "entities": narrative_data.get("actors", [])[:10],
    "article_ids": narrative_data["article_ids"],
    # ... rest of fields ...
    "fingerprint": fingerprint,
}
```

#### Fix 2: Add nucleus_entity to narrative updates (line 747-756)

```python
update_data = {
    'article_ids': combined_article_ids,
    'article_count': updated_article_count,
    'nucleus_entity': fingerprint.get('nucleus_entity', ''),  # ADD THIS
    # ... rest of fields ...
    'fingerprint': fingerprint,
}
```

### Data Migration

After code fix, run migration to backfill existing narratives:

```python
# For each narrative in database:
# 1. Extract nucleus_entity from fingerprint
# 2. Set it as top-level field
# 3. Update document
```

---

## Testing Plan

1. **Unit Test**: Verify narrative_doc includes nucleus_entity
2. **Integration Test**: Create narrative and verify field in database
3. **Migration Test**: Backfill existing narratives and verify
4. **Audit Test**: Re-run quality audit and verify "Unknown" count drops to 0

---

## Impact Assessment

### Before Fix
- 110/110 narratives missing nucleus_entity (100%)
- Audit shows 125/133 "Unknown" (94%)
- Narrative matching degraded
- Cannot query/filter by entity

### After Fix
- All new narratives will have nucleus_entity
- After migration: 0/110 narratives missing nucleus_entity
- Audit will show actual entity distribution
- Narrative matching will improve significantly
- Can query/filter/group by entity

---

## Next Steps

1. **Immediate**: Fix code in narrative_service.py (2 locations)
2. **Immediate**: Write migration script to backfill existing narratives
3. **Test**: Run diagnostic script again to verify fix
4. **Deploy**: Push to production
5. **Monitor**: Re-run quality audit after 24h to verify improvement
