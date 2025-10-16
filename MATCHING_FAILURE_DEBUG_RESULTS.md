# Narrative Matching Failure - Debug Results

## Executive Summary

**Root Cause Identified**: All existing narratives in the database have **empty `key_actions` arrays**, causing similarity scores to be extremely low (0.0 - 0.07) and preventing any matches above the 0.6 threshold.

## Debug Script Results

### Test Cluster Fingerprint
```python
{
    'nucleus_entity': 'SEC',
    'top_actors': ['SEC', 'Binance', 'Coinbase'],
    'key_actions': ['filed lawsuit', 'regulatory enforcement']
}
```

### Existing Narratives Analysis

#### Narrative 1: "Crypto Regulatory Woes"
- **Fingerprint Structure**: ✓ Valid dict
- **Nucleus Entity**: `'regulatory'` (generic, not specific entity)
- **Top Actors**: `['FTX', 'stablecoin', 'Bitget', 'Donald Trump Jr.', 'Crypto.com']`
- **Key Actions**: `[]` ❌ **EMPTY**
- **Similarity Score**: 0.0000
- **Would Match**: ✗ No

**Issues**:
1. Empty key_actions array
2. Nucleus entity is a theme category, not an entity
3. No actor overlap with test cluster

#### Narrative 2: "Defi Adoption Narrative"
- **Fingerprint Structure**: ✓ Valid dict
- **Nucleus Entity**: `'defi_adoption'` (theme category)
- **Top Actors**: `['Donald Trump', 'treasury', 'Vladimir Chistyukhin', 'crypto operations', 'airdrop']`
- **Key Actions**: `[]` ❌ **EMPTY**
- **Similarity Score**: 0.0000
- **Would Match**: ✗ No

**Issues**:
1. Empty key_actions array
2. Nucleus entity is a theme category
3. No actor overlap

#### Narrative 3: "Institutional Investment in Crypto"
- **Fingerprint Structure**: ✓ Valid dict
- **Nucleus Entity**: `'institutional_investment'` (theme category)
- **Top Actors**: `['stablecoin', 'AI data center', 'Tether', 'Donald Trump Jr.', 'Coinbase']`
- **Key Actions**: `[]` ❌ **EMPTY**
- **Similarity Score**: 0.0714 (only from 1 actor overlap: 'Coinbase')
- **Would Match**: ✗ No (below 0.6 threshold)

**Issues**:
1. Empty key_actions array
2. Nucleus entity is a theme category
3. Minimal actor overlap (1/7)

## Similarity Calculation Breakdown

The similarity formula is:
```
similarity = (nucleus_match * 0.3) + (actor_overlap * 0.5) + (action_overlap * 0.2)
```

### Why Matching Fails

For Narrative 3 (best case):
- **Nucleus Match**: 0.0 (SEC ≠ institutional_investment) → contributes 0.0
- **Actor Overlap**: 1/7 = 0.143 → contributes 0.143 * 0.5 = 0.0714
- **Action Overlap**: 0/2 = 0.0 (empty actions) → contributes 0.0
- **Total**: 0.0714 (far below 0.6 threshold)

Even with perfect actor overlap (1.0), the maximum possible score would be:
```
0.0 (nucleus) + 1.0 * 0.5 (actors) + 0.0 (actions) = 0.5 (still below 0.6!)
```

## Root Causes

### 1. Empty Key Actions Arrays
All narratives have `key_actions: []`, which means:
- Action overlap is always 0.0
- Loses 20% of potential similarity score
- Makes it nearly impossible to reach 0.6 threshold

### 2. Theme Categories as Nucleus Entities
Narratives use theme categories (`'regulatory'`, `'defi_adoption'`) instead of specific entities:
- Prevents nucleus matches (loses 30% of score)
- Makes matching too generic

### 3. Legacy Data Format
These narratives appear to be from the old theme-based system:
- Status is `'unknown'` (not using lifecycle states)
- Fingerprints were likely backfilled but incompletely
- Missing the action extraction that new narratives should have

## Impact

**0% Match Rate**: With empty actions and theme-based nucleus entities, no narratives can achieve the 0.6 similarity threshold, causing:
- Every new cluster creates a duplicate narrative
- No narrative consolidation or growth
- Database bloat with redundant narratives

## Recommended Fixes

### Immediate (High Priority)

1. **Backfill Key Actions**
   - Extract actions from narrative summaries or article content
   - Populate `key_actions` arrays for all existing narratives
   - Script: `scripts/backfill_narrative_actions.py`

2. **Fix Nucleus Entities**
   - Convert theme categories to actual entity names
   - Use the top actor with highest salience as nucleus
   - Update fingerprints to use entity-based nucleus

3. **Lower Threshold Temporarily**
   - Reduce similarity threshold from 0.6 to 0.4 during transition
   - Allow matching based on actor overlap alone
   - Restore to 0.6 after backfill complete

### Medium Term

4. **Improve Fingerprint Generation**
   - Ensure `compute_narrative_fingerprint()` always extracts actions
   - Validate fingerprints before saving
   - Add logging for empty components

5. **Add Fingerprint Validation**
   - Check for empty arrays before saving narratives
   - Warn or reject narratives with incomplete fingerprints
   - Add database migration to fix existing data

### Long Term

6. **Monitoring and Alerts**
   - Track similarity score distribution
   - Alert on low match rates
   - Dashboard for fingerprint quality metrics

## Testing Recommendations

1. **Test with Backfilled Data**
   - Run matching tests after backfilling actions
   - Verify similarity scores improve to 0.6+
   - Check that duplicates merge correctly

2. **Test Threshold Adjustment**
   - Experiment with thresholds: 0.4, 0.5, 0.6
   - Measure false positive rate (incorrect merges)
   - Find optimal balance

3. **Integration Testing**
   - Run full narrative clustering pipeline
   - Verify new clusters match existing narratives
   - Monitor for duplicate creation

## Script Location

Debug script: `scripts/debug_matching_failure.py`

Usage:
```bash
poetry run python scripts/debug_matching_failure.py
```

## Next Steps

1. ✅ Debug script created and run
2. ⏳ Create backfill script for key_actions
3. ⏳ Create script to fix nucleus_entity values
4. ⏳ Run backfill on production database
5. ⏳ Re-test matching with fixed data
6. ⏳ Adjust threshold if needed
7. ⏳ Deploy and monitor
