# Fingerprint Similarity Implementation

## Overview

Added `calculate_fingerprint_similarity()` function to determine how similar two narrative fingerprints are, enabling intelligent narrative merging decisions.

## Implementation Details

### Location
- **File**: `src/crypto_news_aggregator/services/narrative_themes.py`
- **Function**: `calculate_fingerprint_similarity(fingerprint1, fingerprint2) -> float`

### Algorithm

The function calculates a weighted similarity score between 0.0 and 1.0 based on three components:

1. **Nucleus Entity Match** (weight: 0.3)
   - Binary score: 1.0 if nucleus entities match exactly, 0.0 otherwise
   - The nucleus entity is the primary protagonist of the narrative

2. **Actor Overlap** (weight: 0.5)
   - Jaccard similarity: `|intersection| / |union|`
   - Compares the top 5 actors from each fingerprint
   - Highest weight because actors are the strongest signal of narrative similarity

3. **Action Overlap** (weight: 0.2)
   - Jaccard similarity: `|intersection| / |union|`
   - Compares the top 3 key actions from each fingerprint
   - Lower weight because actions can vary while narratives remain related

### Formula

```
similarity = (nucleus_match * 0.3) + (actor_jaccard * 0.5) + (action_jaccard * 0.2)
```

### Jaccard Similarity

For sets A and B:
```
jaccard(A, B) = |A ∩ B| / |A ∪ B|
```

Example:
- A = {SEC, Binance, Coinbase}
- B = {SEC, Coinbase, Kraken}
- Intersection = {SEC, Coinbase} = 2 elements
- Union = {SEC, Binance, Coinbase, Kraken} = 4 elements
- Jaccard = 2/4 = 0.5

## Usage Example

```python
from crypto_news_aggregator.services.narrative_themes import (
    compute_narrative_fingerprint,
    calculate_fingerprint_similarity
)

# Create fingerprints from narrative clusters
cluster1 = {
    "nucleus_entity": "SEC",
    "actors": {"SEC": 5, "Binance": 4, "Coinbase": 3},
    "actions": ["filed lawsuit", "regulatory enforcement"]
}

cluster2 = {
    "nucleus_entity": "SEC",
    "actors": {"SEC": 5, "Coinbase": 4, "Kraken": 3},
    "actions": ["filed lawsuit", "compliance review"]
}

fp1 = compute_narrative_fingerprint(cluster1)
fp2 = compute_narrative_fingerprint(cluster2)

similarity = calculate_fingerprint_similarity(fp1, fp2)
# Returns: ~0.63

# Decision logic
if similarity >= 0.6:
    print("MERGE: These narratives are similar enough to combine")
else:
    print("KEEP SEPARATE: These are distinct narratives")
```

## Test Results

All 12 tests pass, covering:

- ✅ Identical fingerprints (similarity = 1.0)
- ✅ High similarity with same nucleus and actor overlap
- ✅ Low similarity with different nucleus and actors
- ✅ Moderate similarity with same nucleus but different actors
- ✅ Empty fingerprint handling
- ✅ Missing field handling
- ✅ Weighted scoring verification
- ✅ Jaccard similarity calculation accuracy
- ✅ Case-sensitive matching

**Test Command:**
```bash
poetry run pytest tests/services/test_narrative_themes.py::TestCalculateFingerprintSimilarity -v
```

**Result:** 12 passed in 0.06s

## Demo Script

Run the interactive demo to see the function in action:

```bash
poetry run python examples/fingerprint_similarity_demo.py
```

The demo shows three scenarios:
1. **Similar SEC Regulatory Narratives** → Similarity: 0.633 → MERGE
2. **Different Narratives (DeFi vs Regulation)** → Similarity: 0.000 → SEPARATE
3. **Same Nucleus, Different Actors** → Similarity: 0.400 → SEPARATE

## Merge Threshold

**Recommended threshold: 0.6 (60% similarity)**

This threshold balances:
- **Precision**: Avoiding false merges of unrelated narratives
- **Recall**: Capturing genuinely related narratives with some variation

### Threshold Sensitivity

- **similarity ≥ 0.8**: Very high confidence merge (same nucleus + high actor overlap)
- **0.6 ≤ similarity < 0.8**: Good merge candidate (same nucleus OR high actor overlap)
- **0.4 ≤ similarity < 0.6**: Borderline (manual review recommended)
- **similarity < 0.4**: Keep separate (distinct narratives)

## Edge Cases Handled

1. **Empty fingerprints**: Returns 0.0 similarity
2. **Missing fields**: Treats missing fields as empty sets
3. **Case sensitivity**: Entity matching is case-sensitive (intentional)
4. **Empty sets**: Handles division by zero gracefully (returns 0.0)

## Integration Points

This function can be used in:

1. **Narrative Deduplication**: Merge similar narratives in the database
2. **Real-time Clustering**: Decide if new articles belong to existing narratives
3. **Narrative Evolution**: Track how narratives change over time
4. **Quality Metrics**: Measure narrative coherence and distinctiveness

## Performance

- **Time Complexity**: O(n) where n is the number of actors/actions (typically ≤ 8)
- **Space Complexity**: O(1) - only creates small sets for comparison
- **Typical Runtime**: < 1ms per comparison

## Next Steps

Potential enhancements:
1. Add temporal decay (older fingerprints get lower similarity)
2. Add entity type weighting (protocols vs people vs organizations)
3. Add semantic similarity for actions (using embeddings)
4. Add configurable weights for different use cases
5. Add similarity explanation (which components contributed most)

## Related Files

- **Implementation**: `src/crypto_news_aggregator/services/narrative_themes.py`
- **Tests**: `tests/services/test_narrative_themes.py`
- **Demo**: `examples/fingerprint_similarity_demo.py`
- **Documentation**: This file

## References

- Jaccard Similarity: https://en.wikipedia.org/wiki/Jaccard_index
- Related function: `compute_narrative_fingerprint()` (lines 77-129)
- Related function: `merge_shallow_narratives()` (lines 1007-1107)
