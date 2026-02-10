# Narrative Matching Test Guide

Quick reference for testing narrative matching logic.

## Quick Start

```bash
# Run the test
poetry run python scripts/test_narrative_matching.py
```

## What It Does

The test script (`scripts/test_narrative_matching.py`) verifies that narratives are being **matched and merged** correctly instead of creating duplicates.

### Test Flow

1. **Initial State** - Shows current narrative count and recent narratives
2. **Cluster Detection** - Finds narrative clusters from last 72 hours
3. **Matching Test** - For each cluster:
   - Computes fingerprint (nucleus entity + top 3 actors)
   - Searches for matching existing narratives
   - Shows similarity scores for top 3 candidates
   - Reports whether it would match or create new
4. **Summary** - Shows before/after counts and analysis

### Dry-Run Mode

⚠️ **Important:** The script runs in **dry-run mode** - it queries the database but **does not save any changes**.

## Understanding Output

### Initial State Section

```
📊 INITIAL STATE
Total narratives in database: 36
Narratives active in last 72 hours: 23
```

Shows baseline narrative counts.

### Existing Narratives

```
📋 EXISTING NARRATIVES (Last 72 hours)
1. Narrative #68ec5c4ed6a52d09a05dd0a0
   Title: Crypto.com Navigates Regulation and Volatility
   Nucleus: Crypto.com
   Actors: Crypto.com, Regulators, Exchanges
   Articles: 3
   Last updated: 2025-10-13 20:15:03
```

Lists recent narratives that could potentially match new clusters.

### Cluster Analysis

```
🔸 CLUSTER #1
Nucleus: Hyperliquid
Actors: Hyperliquid, DeFi, Bitcoin
Articles in cluster: 8

🔎 Finding candidate matches...
✨ NO MATCHES FOUND - Would create NEW narrative
```

**Good Output (Matching Working):**
```
🔸 CLUSTER #5
Nucleus: Bitcoin
Actors: Bitcoin, Ethereum, ETFs
Articles in cluster: 97

🔎 Finding candidate matches...
Found 5 candidate narratives

📊 TOP 3 CANDIDATE MATCHES:
  1. Narrative #68ec32435c001fd2c716d18e
     Title: Bitcoin Price Surges...
     Nucleus: Bitcoin
     Actors: Bitcoin, Ethereum, Traders
     Similarity Score: 0.850
     Articles: 45
     
✅ MATCH FOUND - Would UPDATE Narrative #68ec32435c001fd2c716d18e
   Match score: 0.850 >= 0.600 (threshold)
```

### Summary Section

```
📈 SUMMARY
Narratives before detection:  36
Clusters detected:            39
Would create NEW narratives:  39  ⚠️ BAD - should be lower
Would UPDATE existing:        0   ⚠️ BAD - should have matches
Narratives after detection:   75 (projected)

⚠️ WARNING: Only creating new narratives, not matching existing ones
   This suggests potential duplicate narrative creation
```

## Interpreting Results

### ✅ Healthy Matching

- **Mix of matches and new narratives** - Some clusters match existing, some are genuinely new
- **High match rate for similar topics** - Clusters with same nucleus entity match existing narratives
- **Reasonable growth** - Narrative count increases moderately, not doubling

Example:
```
Clusters detected:            39
Would create NEW narratives:  15  ✅ Some new topics
Would UPDATE existing:        24  ✅ Good match rate
```

### ⚠️ Matching Issues

- **Zero matches** - No clusters matching existing narratives
- **All new narratives** - Every cluster creates a new narrative
- **Obvious duplicates** - Clusters with identical nucleus as existing narratives don't match

Example:
```
Clusters detected:            39
Would create NEW narratives:  39  ❌ All new
Would UPDATE existing:        0   ❌ No matches
```

### 🚨 Critical Problems

- **Narrative count doubles or more** - Massive duplication
- **Identical nucleus entities don't match** - Core matching logic broken
- **All similarity scores below threshold** - Threshold too strict or calculation broken

## Common Issues

### Issue 1: No Matches Found

**Symptom:** All clusters show "NO MATCHES FOUND"

**Possible Causes:**
- Missing fingerprints on existing narratives
- Fingerprint format mismatch
- Similarity threshold too strict (>0.6)
- Candidate retrieval query issues

**Debug Steps:**
1. Check if existing narratives have `fingerprint` field
2. Verify fingerprint structure matches expected format
3. Add logging to `find_matching_narrative()` to see candidates
4. Test similarity calculation with known matching pairs

### Issue 2: Low Similarity Scores

**Symptom:** Candidates found but all scores < 0.6

**Possible Causes:**
- Actor lists don't overlap
- Nucleus entity name mismatch (case, whitespace)
- Fingerprint computation inconsistent

**Debug Steps:**
1. Log fingerprints being compared
2. Check nucleus entity normalization
3. Verify actor lists are properly formatted
4. Test with identical fingerprints (should score 1.0)

### Issue 3: No Candidates Found

**Symptom:** "NO MATCHES FOUND" immediately, no candidates listed

**Possible Causes:**
- Time window too narrow
- Status filter excluding valid narratives
- Database query issues

**Debug Steps:**
1. Check `last_updated` field on existing narratives
2. Verify status values match expected list
3. Test database query directly

## Configuration

Edit the script to adjust test parameters:

```python
# Time window for articles (line 109)
hours = 72  # Change to 24, 48, 168, etc.

# Minimum cluster size (line 134)
min_cluster_size = 3  # Change to 2, 4, 5, etc.

# Similarity threshold (line 271)
threshold = 0.6  # Change to 0.5, 0.7, etc.
```

## Advanced Usage

### Test Specific Time Windows

```python
# Test last 24 hours only
hours = 24

# Test last week
hours = 168
```

### Adjust Cluster Size

```python
# More granular clusters
min_cluster_size = 2

# Larger, more significant clusters
min_cluster_size = 5
```

### Change Similarity Threshold

```python
# More lenient matching
threshold = 0.5

# Stricter matching
threshold = 0.7
```

## Debugging Tips

### Add Detailed Logging

Edit `find_matching_narrative()` in `narrative_service.py`:

```python
# Add after line 329
logger.info(f"Evaluating {len(candidates)} candidate narratives")
for candidate in candidates:
    logger.debug(f"Candidate: {candidate.get('title')}")
    logger.debug(f"  Fingerprint: {candidate.get('fingerprint')}")
```

### Inspect Fingerprints

Add to test script after line 190:

```python
print(f"Cluster fingerprint: {fingerprint}")
print(f"  nucleus_entity: {fingerprint.get('nucleus_entity')}")
print(f"  top_actors: {fingerprint.get('top_actors')}")
print(f"  key_actions: {fingerprint.get('key_actions')}")
```

### Test Similarity Directly

```python
from crypto_news_aggregator.services.narrative_service import calculate_fingerprint_similarity

fp1 = {'nucleus_entity': 'Bitcoin', 'top_actors': ['Bitcoin', 'ETF'], 'key_actions': []}
fp2 = {'nucleus_entity': 'Bitcoin', 'top_actors': ['Bitcoin', 'ETF'], 'key_actions': []}

score = calculate_fingerprint_similarity(fp1, fp2)
print(f"Similarity: {score}")  # Should be 1.0 for identical
```

## Expected Behavior

After fixing matching logic, you should see:

1. **Clusters with identical nucleus entities match existing narratives**
2. **Similarity scores > 0.6 for obvious matches**
3. **Mix of updates and new narratives** (not all new)
4. **Reasonable narrative growth** (not doubling)

## Re-running After Fixes

```bash
# After making fixes to matching logic
poetry run python scripts/test_narrative_matching.py

# Look for improvements in:
# - Number of matches found
# - Similarity scores for candidates
# - Ratio of updates vs. new narratives
```

## Success Criteria

✅ Test passes when:
- Clusters with same nucleus entity match existing narratives
- Similarity scores are reasonable (0.6-1.0 for matches)
- Match rate is > 30% for established topics
- Narrative count growth is moderate (<50% increase)

❌ Test fails when:
- Zero matches found despite obvious overlaps
- All similarity scores below threshold
- Narrative count doubles or more
- Identical nucleus entities don't match

## Related Files

- **Test Script:** `scripts/test_narrative_matching.py`
- **Matching Logic:** `src/crypto_news_aggregator/services/narrative_service.py`
- **Fingerprint Functions:** `src/crypto_news_aggregator/services/narrative_themes.py`
- **Test Results:** `NARRATIVE_MATCHING_TEST_RESULTS.md`

## Next Steps

1. Run test to identify issues ✅
2. Debug matching logic based on output
3. Fix identified problems
4. Re-run test to verify fixes
5. Deploy when test shows healthy matching
