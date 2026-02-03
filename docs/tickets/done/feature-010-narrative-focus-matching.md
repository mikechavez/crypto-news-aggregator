# [FEATURE-010] Revise Narrative Similarity Matching to Prioritize Focus

**STATUS: COMPLETE** ✅ (2026-01-07)

## Context
- ADR: `docs/decisions/004-narrative-focus-identity.md`
- Sprint: Sprint 2 (Intelligence Layer)
- Priority: P1 (blocks narrative deduplication fix)
- Actual effort: ~3 hours (implementation + testing)
- Related: FEATURE-009 (complete), unblocks FEATURE-011
- Completed by: Claude Haiku with comprehensive test coverage

## What to Build

Rewrite the narrative fingerprint similarity calculation to prioritize `narrative_focus` as the primary identity signal. This fixes narrative duplication where the same entity (e.g., "Dogecoin") creates multiple simultaneous narratives for different stories.

**Current problem**: Using `nucleus_entity` as strongest signal causes both over-splitting (same story fragments) and over-merging (different stories collapse).

**Solution**: Make `narrative_focus` the primary discriminator (0.5 weight) so parallel stories about the same entity remain distinct.

## Files to Modify

**PRIMARY**:
- `src/crypto_news_aggregator/services/narrative_service.py`
  - ADD: `_compute_focus_similarity()` function
  - MODIFY: `_compute_fingerprint_similarity()` - reweight components
  - MODIFY: `_should_merge_with_existing()` - add hard gate logic

**TESTS**:
- `tests/services/test_narrative_service.py`
  - ADD: Focus similarity tests
  - ADD: Hard gate edge case tests
  - UPDATE: Existing fingerprint tests with new weights

## Implementation Details

### Step 1: Add Focus Similarity Function
```python
def _compute_focus_similarity(focus1: str, focus2: str) -> float:
    """
    Token-based similarity for narrative focus phrases.
    Returns: 1.0 (exact), 0.9 (high similarity), 0.7 (partial), 0.0 (different)
    """
    if not focus1 or not focus2:
        return 0.5  # Neutral for missing focus
    
    tokens1 = set(focus1.lower().split())
    tokens2 = set(focus2.lower().split())
    
    overlap = len(tokens1 & tokens2)
    total = len(tokens1 | tokens2)
    ratio = overlap / total if total > 0 else 0.0
    
    if ratio > 0.8: return 0.9
    if ratio > 0.5: return 0.7
    return 0.0
```

### Step 2: Add Hard Gate Logic
```python
def _compute_fingerprint_similarity(fp1, fp2) -> float:
    # Hard gate: Must have focus OR entity match
    focus1 = fp1.get("narrative_focus", "")
    focus2 = fp2.get("narrative_focus", "")
    entity1 = fp1.get("nucleus_entity", "")
    entity2 = fp2.get("nucleus_entity", "")
    
    has_focus_match = focus1 and focus2 and focus1.lower() == focus2.lower()
    has_entity_match = entity1 and entity2 and entity1 == entity2
    
    if not (has_focus_match or has_entity_match):
        return 0.0
    
    # Continue with weighted similarity...
```

### Step 3: Reweight Components
**Current (FEATURE-009)**:
- Focus: 0.35, Nucleus: 0.30, Actors: 0.20, Actions: 0.15

**Target (FEATURE-010)**:
- Focus: 0.5, Nucleus: 0.3, Actors: 0.1, Actions: 0.1

```python
score = 0.0

# Focus component (0.5) - primary signal
focus_sim = _compute_focus_similarity(fp1.get("narrative_focus"), fp2.get("narrative_focus"))
score += focus_sim * 0.5

# Nucleus component (0.3) - secondary signal
if fp1.get("nucleus_entity") == fp2.get("nucleus_entity"):
    score += 0.3

# Actors component (0.1)
actors1 = set(fp1.get("top_actors", []))
actors2 = set(fp2.get("top_actors", []))
if actors1 and actors2:
    actor_overlap = len(actors1 & actors2) / max(len(actors1), len(actors2))
    score += actor_overlap * 0.1

# Actions component (0.1)
actions1 = set(fp1.get("key_actions", []))
actions2 = set(fp2.get("key_actions", []))
if actions1 and actions2:
    action_overlap = len(actions1 & actions2) / max(len(actions1), len(actions2))
    score += action_overlap * 0.1

return score
```

### Step 4: Remove Semantic Boost
Current code has semantic boost when both nucleus AND focus match. This is now redundant since weights sum to 1.0. Remove it.

## Acceptance Criteria

- [ ] `_compute_focus_similarity()` function added with token-based matching
- [ ] Hard gate logic prevents similarity when no common ground
- [ ] Similarity weights updated: focus (0.5), nucleus (0.3), actors (0.1), actions (0.1)
- [ ] Semantic boost removed (redundant)
- [ ] All existing tests pass (68+ tests)
- [ ] New tests added:
  - [ ] Focus similarity: exact match, high similarity, partial, different
  - [ ] Hard gate: no common ground returns 0.0
  - [ ] Same entity + different focus → score < 0.5 (splits)
  - [ ] Same entity + same focus → score ≥ 0.8 (merges)
  - [ ] Different entity + same focus → score ≈ 0.5 (medium)

## Out of Scope

- Semantic embeddings (future optimization)
- Synonym dictionary for focus matching (can add later if needed)
- Post-detection consolidation (FEATURE-011)
- Narrative reactivation logic (FEATURE-012)
- Changing time decay thresholds (keep at 0.5 recent, 0.6 older)

## Dependencies

**Complete**:
- ✅ FEATURE-009: `narrative_focus` field added to fingerprints
- ✅ Focus extraction working in LLM pipeline

**Blocked on this**:
- FEATURE-011: Consolidation safety pass
- FEATURE-012: Narrative reactivation

## Testing Requirements

### Unit Tests
```python
def test_focus_similarity_exact_match():
    assert _compute_focus_similarity("price surge", "price surge") == 1.0

def test_focus_similarity_partial():
    # "price surge" vs "price rally" - share "price"
    assert 0.6 <= _compute_focus_similarity("price surge", "price rally") <= 0.8

def test_hard_gate_no_match():
    fp1 = {"nucleus_entity": "Bitcoin", "narrative_focus": "price surge"}
    fp2 = {"nucleus_entity": "Ethereum", "narrative_focus": "governance"}
    assert _compute_fingerprint_similarity(fp1, fp2) == 0.0

def test_same_entity_different_focus_splits():
    fp1 = {"nucleus_entity": "Dogecoin", "narrative_focus": "price surge"}
    fp2 = {"nucleus_entity": "Dogecoin", "narrative_focus": "governance dispute"}
    assert _compute_fingerprint_similarity(fp1, fp2) < 0.5  # Below merge threshold

def test_same_entity_same_focus_merges():
    fp1 = {"nucleus_entity": "Dogecoin", "narrative_focus": "price surge"}
    fp2 = {"nucleus_entity": "Dogecoin", "narrative_focus": "price surge"}
    score = _compute_fingerprint_similarity(fp1, fp2)
    assert score >= 0.8  # Should be 0.5 (focus) + 0.3 (entity) = 0.8
```

### Integration Tests
- Run on production data subset
- Verify no over-merging of different stories
- Verify no over-splitting of same story

## Success Metrics

**Quantitative**:
- Narratives per entity: Target 1-3 (currently 5+)
- Same entity + different focus: Similarity score < 0.5
- Same entity + same focus: Similarity score ≥ 0.8

**Qualitative**:
- Manual review: 20 random narrative pairs should make sense
- Dogecoin test: Multiple Dogecoin narratives should have distinct focuses

## Known Edge Cases

1. **Missing focus field** (legacy data): Returns 0.5 neutral score
2. **Empty focus strings**: Treated as missing (0.5 neutral)
3. **Very short focus** ("surge" vs "rally"): Token overlap may be 0.0 (acceptable - these are different)
4. **Multi-word focus**: Token overlap handles well ("regulatory enforcement action" vs "enforcement action" = 0.7)

## Implementation Summary (2026-01-07)

### Changes Made

**File: `src/crypto_news_aggregator/services/narrative_themes.py`**

1. **Added `_compute_focus_similarity()` function** (lines 158-214)
   - Token-based Jaccard similarity for focus phrases
   - Returns: 1.0 (exact), 0.9 (>80% overlap), 0.7 (50-80% overlap), 0.0 (different), 0.5 (missing/legacy)
   - Handles case-insensitivity and whitespace normalization
   - Example: "regulatory enforcement action" vs "regulatory enforcement" → 0.7

2. **Rewrote `calculate_fingerprint_similarity()` function** (lines 217-323)
   - **Hard gate logic** (lines 274-284): Requires either exact focus match OR nucleus match
     - Blocks unrelated narratives (e.g., "SEC regulatory" vs "DeFi protocol" → 0.0)
     - Allows narratives with same nucleus but different focus to be scored
   - **New weights** (lines 308-313):
     - Focus: 0.5 (primary discriminator, was 0.35)
     - Nucleus: 0.3 (secondary, was 0.30)
     - Actors: 0.1 (was 0.20)
     - Actions: 0.1 (was 0.15)
   - **Removed semantic boost** - weights sum to exactly 1.0 now

### Test Coverage

**File: `tests/services/test_narrative_themes.py`**

**New Tests:**
- `TestComputeFocusSimilarity` - 12 tests for focus similarity function
  - Exact match, high/partial/no similarity, empty strings, case-insensitivity, multi-word phrases

**Updated Tests:**
- `TestCalculateFingerprintSimilarity` - 16 tests updated with new weights and hard gate logic
  - Hard gate blocking tests (prevent over-merging)
  - Hard gate passing tests (allow same nucleus or same focus)
  - Weighted scoring verification
  - Edge cases (empty, missing fields, case-insensitivity)

**Results:** ✅ All 83 tests pass (12 new + 71 existing)

### Key Behaviors

**Hard Gate Examples:**
- "SEC regulatory enforcement" + "DeFi protocol upgrade" → **0.0** (blocks, no match on focus/nucleus)
- "Bitcoin price surge" + "Bitcoin institutional adoption" → **0.32** (allows, same nucleus)
- "Bitcoin institutional adoption" + "Ethereum institutional adoption" → **0.60** (allows, same focus)

**Preventing Over-Merge (Main Fix):**
- "Dogecoin price surge" + "Dogecoin governance dispute"
  - Old behavior: Would merge (same nucleus + some actor overlap)
  - New behavior: Score 0.33 (below 0.5 merge threshold)
  - Result: **Stays separate** ✅

## Post-Implementation

**Before deployment**:
1. ✅ All unit tests pass
2. Recommend: Review backfill script for legacy narratives before deployment
3. Consider: Run on sample data to verify behavior

**After deployment**:
1. Monitor narrative deduplication metrics
2. Log similarity scores for edge cases
3. Check production merge/split rates

**Follow-up tuning** (if needed):
- Add synonym dictionary if focus matching too strict
- Adjust weights based on production distribution
- Fine-tune hard gate thresholds if needed

## Reference

- **Primary file modified:** `src/crypto_news_aggregator/services/narrative_themes.py`
- **Test file:** `tests/services/test_narrative_themes.py`
- **Related features:** FEATURE-009 (focus extraction), FEATURE-011 (consolidation safety)
- **Architecture:** ADR-004 (Narrative Focus Identity)