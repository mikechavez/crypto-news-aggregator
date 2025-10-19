# Semantic Boost Implementation

## Summary
Added a semantic boost feature to the `calculate_fingerprint_similarity` function in `narrative_themes.py` to improve narrative merging when narratives share the same core entity.

## Changes Made

### 1. Core Implementation (`src/crypto_news_aggregator/services/narrative_themes.py`)

**Location**: Lines 201-209 in `calculate_fingerprint_similarity` function

**What was added**:
- Case-insensitive comparison of `nucleus_entity` fields from both fingerprints
- When both fingerprints have the same nucleus entity (case-insensitive), a **0.1 bonus** is added to the final similarity score
- Logging at INFO level when the boost is applied
- Updated debug logging to include the boost value

**Code snippet**:
```python
# Semantic boost: if both fingerprints have the exact same nucleus_entity (case-insensitive),
# add 0.1 bonus to help narratives about the same core entity merge even with minimal actor overlap
semantic_boost = 0.0
if nucleus1 and nucleus2 and nucleus1.lower() == nucleus2.lower():
    semantic_boost = 0.1
    similarity += semantic_boost
    logger.info(
        f"Applied semantic boost (+{semantic_boost:.1f}) for matching nucleus entity: '{nucleus1}' == '{nucleus2}'"
    )
```

### 2. Test Updates (`tests/services/test_narrative_themes.py`)

Updated all existing tests in `TestCalculateFingerprintSimilarity` class to account for the semantic boost:

- **test_identical_fingerprints**: Now expects 1.1 (1.0 + 0.1 boost)
- **test_same_nucleus_high_actor_overlap**: Updated expected range to 0.75-0.85
- **test_same_nucleus_no_actor_overlap**: Updated expected range to 0.58-0.66
- **test_different_nucleus_high_actor_overlap**: Updated expected range to 0.30-0.40 (also corrected for weight changes)
- **test_missing_fields_handled_gracefully**: Updated expected range to 0.50-0.60
- **test_action_overlap_contribution**: Updated expected range to 0.95-1.05
- **test_weighted_scoring**: Updated logic to reflect that nucleus match with boost is now higher than actor overlap
- **test_jaccard_similarity_calculation**: Updated expected range to 0.68-0.78
- **test_case_insensitive_nucleus_matching**: Renamed from `test_case_sensitive_matching` and updated to test case-insensitive behavior

**New test added**: `test_semantic_boost_applied`
- Tests exact case match (e.g., "Bitcoin" == "Bitcoin")
- Tests case-insensitive match (e.g., "BITCOIN" == "bitcoin")
- Tests no match scenario (e.g., "Ethereum" vs "Bitcoin")

## Rationale

### Problem
Narratives about the same core entity (e.g., "SEC") were sometimes failing to merge when they had minimal actor overlap, even though they were clearly about the same topic.

### Solution
The semantic boost ensures that narratives sharing the same nucleus entity get a similarity bump, making them more likely to merge. The 0.1 boost is significant enough to help borderline cases merge while not overwhelming the other similarity components.

### Example Impact

**Before** (without semantic boost):
- Two "SEC" narratives with different actors: similarity ~0.45
- Might not merge if threshold is 0.5

**After** (with semantic boost):
- Same two "SEC" narratives: similarity ~0.55 (0.45 + 0.1)
- More likely to merge, creating better narrative continuity

## Weight Distribution

The final similarity score is calculated as:
- **Nucleus match**: 0.45 (exact match)
- **Actor overlap**: 0.35 (Jaccard similarity)
- **Action overlap**: 0.20 (Jaccard similarity)
- **Semantic boost**: +0.1 (when nucleus entities match case-insensitively)

Maximum possible score: 1.1 (when all components match perfectly)

## Testing

All 13 tests in `TestCalculateFingerprintSimilarity` pass:
```bash
poetry run pytest tests/services/test_narrative_themes.py::TestCalculateFingerprintSimilarity -v
```

## Logging

When the semantic boost is applied, you'll see INFO-level log messages like:
```
Applied semantic boost (+0.1) for matching nucleus entity: 'SEC' == 'SEC'
```

This helps track when narratives are being merged due to shared nucleus entities.
