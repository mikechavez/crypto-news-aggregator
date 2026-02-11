# Salience-Aware Narrative Clustering Implementation

## Summary

Implemented intelligent narrative clustering that uses salience scores and nucleus entities to group articles by what they're actually ABOUT, not just which entities are mentioned.

## Implementation Details

### Function: `cluster_by_narrative_salience`

**Location:** `src/crypto_news_aggregator/services/narrative_themes.py`

**Purpose:** Cluster articles using weighted link strength based on:
- Nucleus entity overlap (strongest signal)
- High-salience actor overlap (medium signal)
- Tension/theme overlap (weak signal)

### Clustering Algorithm

**Link Strength Calculation:**
- **Same nucleus entity:** +1.0 (e.g., both articles are fundamentally about "SEC")
- **2+ shared high-salience actors (≥4):** +0.7 (e.g., both feature "Binance" and "Coinbase" as key players)
- **1 shared high-salience actor:** +0.4
- **1+ shared tensions:** +0.3 (e.g., both involve "Regulation vs Innovation")

**Clustering Threshold:** Articles cluster together if `link_strength >= 0.8`

**Filtering:** Clusters with fewer than `min_cluster_size` articles are filtered out (default: 3)

### Key Features

1. **Salience-Aware:** Only actors with salience ≥ 4 are considered "core actors"
   - Filters out background mentions (salience 1-3)
   - Focuses on key players in the story

2. **Nucleus Entity Priority:** Articles about the same entity strongly cluster
   - Captures "SEC enforcement wave" narratives
   - Groups "Bitcoin adoption" stories

3. **Weighted Overlap:** Combines multiple signals for robust clustering
   - Prevents over-clustering from weak signals alone
   - Requires meaningful overlap (0.8 threshold)

4. **Small Cluster Filtering:** Removes noise
   - Only substantial narratives (≥3 articles) are kept
   - Prevents single-article "narratives"

## Test Coverage

**File:** `tests/services/test_salience_clustering.py`

**Test Scenarios:**
1. ✅ Same nucleus entity clustering
2. ✅ High-salience actor overlap clustering
3. ✅ Weak links below threshold (no clustering)
4. ✅ Small cluster filtering
5. ✅ Tension overlap alone (insufficient)
6. ✅ One shared actor + tension (below threshold)
7. ✅ Low-salience actors ignored
8. ✅ Mixed clustering (multiple clusters)
9. ✅ Empty input handling
10. ✅ Missing fields handling

**All tests passing:** 10/10 ✅

## Example Clustering Scenarios

### Scenario 1: SEC Enforcement Wave
```python
# Articles with same nucleus entity "SEC" cluster together
Article 1: "SEC sues Binance" (nucleus: SEC, actors: [SEC:5, Binance:4])
Article 2: "SEC targets Coinbase" (nucleus: SEC, actors: [SEC:5, Coinbase:4])
Article 3: "SEC vs Ripple update" (nucleus: SEC, actors: [SEC:5, Ripple:4])

Result: 1 cluster with 3 articles (link_strength = 1.0 for all pairs)
```

### Scenario 2: DeFi Protocol Interactions
```python
# Articles with 2+ shared high-salience actors + shared tension
Article 1: "Uniswap integrates with Aave" (nucleus: Uniswap, core_actors: [Uniswap:5, Aave:4], tensions: [DeFi Innovation])
Article 2: "Aave launches on new chain" (nucleus: Aave, core_actors: [Aave:5, Uniswap:4], tensions: [DeFi Innovation])
Article 3: "Curve partners with Uniswap" (nucleus: Curve, core_actors: [Curve:5, Uniswap:4, Aave:4], tensions: [DeFi Innovation])

Result: 1 cluster with 3 articles (link_strength = 1.0 for all pairs)
```

### Scenario 3: Weak Links (No Clustering)
```python
# Articles with only tension overlap (0.3) - below threshold
Article 1: "Bitcoin adoption in El Salvador" (nucleus: Bitcoin, tensions: [Adoption])
Article 2: "Ethereum staking grows" (nucleus: Ethereum, tensions: [Adoption])
Article 3: "Solana TVL increases" (nucleus: Solana, tensions: [Adoption])

Result: 0 clusters (each article forms its own cluster, all below min_cluster_size)
```

## Integration Points

### Current Usage
- Can be called directly with article data containing:
  - `nucleus_entity`: Primary entity the article is about
  - `actors`: List of all actors mentioned
  - `actor_salience`: Dict mapping actors to salience scores (1-5)
  - `tensions`: List of themes/tensions

### Future Integration
- Will be used in narrative discovery pipeline
- Replaces simple entity co-occurrence clustering
- Enables more accurate narrative detection

## Next Steps

1. **Integrate with narrative discovery:**
   - Call `cluster_by_narrative_salience` after extracting narrative elements
   - Generate narrative summaries for each cluster

2. **Tune parameters:**
   - Adjust link strength weights based on real-world performance
   - Experiment with clustering threshold (currently 0.8)
   - Test different min_cluster_size values

3. **Add cluster quality metrics:**
   - Measure cluster coherence
   - Track false positives/negatives
   - Monitor cluster size distribution

4. **Optimize performance:**
   - Current O(n²) complexity acceptable for small datasets
   - Consider more efficient algorithms for large-scale clustering

## Technical Notes

- **Greedy clustering:** Articles are processed sequentially and matched to best cluster
- **No re-clustering:** Once an article joins a cluster, it doesn't move
- **Cluster properties:** Aggregated from all articles in the cluster
- **Missing data handling:** Gracefully handles missing fields with empty defaults

## Files Modified

1. `src/crypto_news_aggregator/services/narrative_themes.py`
   - Added `cluster_by_narrative_salience` function

2. `tests/services/test_salience_clustering.py`
   - Created comprehensive test suite (10 test cases)

## Validation

✅ Syntax check passed
✅ All tests passing (10/10)
✅ Edge cases handled (empty input, missing fields)
✅ Realistic scenarios validated

---

**Implementation Date:** 2025-01-11
**Status:** Complete and tested
