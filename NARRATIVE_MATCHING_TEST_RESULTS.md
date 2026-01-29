# Narrative Matching Test Results

**Date:** October 15, 2025  
**Test Script:** `scripts/test_narrative_matching.py`

## Executive Summary

🚨 **CRITICAL ISSUE DETECTED**: Narrative matching logic is **completely failing** to match new clusters with existing narratives.

- **36 total narratives** in database
- **23 active narratives** in last 72 hours
- **39 clusters detected** from recent articles
- **0 matches found** (0% match rate)
- **39 new narratives** would be created (100% duplication)

This confirms that narratives are being duplicated instead of being merged with existing ones.

## Test Configuration

- **Time Window:** 72 hours
- **Articles Analyzed:** 614 articles with narrative data
- **Minimum Cluster Size:** 3 articles
- **Similarity Threshold:** 0.6 (60%)
- **Mode:** Dry-run (no database changes)

## Key Findings

### 1. Zero Matches Despite Obvious Overlaps

Several clusters have **identical nucleus entities** to existing narratives but still failed to match:

| Cluster Nucleus | Existing Narrative | Expected Match? | Actual Result |
|----------------|-------------------|-----------------|---------------|
| Hyperliquid | "Hyperliquid's Decentralized Futures..." | ✅ YES | ❌ NO MATCH |
| Strategy | "Strategy's Bet on Bitcoin..." | ✅ YES | ❌ NO MATCH |
| WazirX | "WazirX Restructures After $234M Hack..." | ✅ YES | ❌ NO MATCH |
| Shiba Inu | "Shiba Inu: Meme Coin Mania..." | ✅ YES | ❌ NO MATCH |
| Ripple | "Ripple Expands Reach..." | ✅ YES | ❌ NO MATCH |
| Trader | "Crypto Trader Profits From..." | ✅ YES | ❌ NO MATCH |
| Crypto Market | "Crypto Market Volatility Tied..." | ✅ YES | ❌ NO MATCH |

### 2. Sample Cluster Details

**Cluster #1: Hyperliquid**
- Nucleus: Hyperliquid
- Top Actors: Hyperliquid, DeFi, Bitcoin
- Articles: 8
- **Result:** NO MATCHES FOUND - Would create NEW narrative

**Existing Narrative (should have matched):**
- Title: "Hyperliquid's Decentralized Futures Expansion Amid Crypto Volatility"
- Nucleus: Hyperliquid
- Actors: HYPE, HIP-3, BitForex
- Articles: 7
- Last updated: 2025-10-13 20:15:03

**Cluster #5: Bitcoin**
- Nucleus: Bitcoin
- Top Actors: Bitcoin, Ethereum, ETFs
- Articles: 97 (largest cluster)
- **Result:** NO MATCHES FOUND - Would create NEW narrative

**Cluster #11: Ripple**
- Nucleus: Ripple
- Top Actors: Ripple, SEC, XRP
- Articles: 9
- **Result:** NO MATCHES FOUND - Would create NEW narrative

## Root Cause Analysis

The matching failure suggests one or more of these issues:

### 1. **Fingerprint Computation Issues**
- `compute_narrative_fingerprint()` may not be generating consistent fingerprints
- Fingerprints from clusters vs. existing narratives may use different formats

### 2. **Similarity Calculation Problems**
- `calculate_fingerprint_similarity()` may be returning scores below threshold
- The 0.6 threshold may be too strict for legitimate matches
- Nucleus entity comparison may be case-sensitive or have normalization issues

### 3. **Candidate Retrieval Issues**
- `find_matching_narrative()` may not be finding candidate narratives correctly
- Time window or status filters may be excluding valid candidates
- Database query may have issues

### 4. **Fingerprint Storage Issues**
- Existing narratives may not have `fingerprint` field populated
- Legacy narratives may use different fingerprint format
- Fingerprint field may be missing or malformed

## Impact

If this matching logic is deployed:
- **Narrative count would double** (36 → 75) in one detection cycle
- **Duplicate narratives** would be created for the same stories
- **User experience degraded** with redundant narrative listings
- **Database bloat** with duplicate data
- **Signal quality reduced** due to fragmented narratives

## Recommended Actions

### Immediate (High Priority)

1. **Debug `find_matching_narrative()`**
   - Add detailed logging to show why candidates are rejected
   - Log similarity scores for all candidates
   - Verify fingerprint format consistency

2. **Inspect Existing Narratives**
   - Check if `fingerprint` field exists on all narratives
   - Verify fingerprint structure matches expected format
   - Run backfill if fingerprints are missing

3. **Test Similarity Calculation**
   - Create unit tests with known matching pairs
   - Test with identical nucleus entities
   - Verify threshold is appropriate (0.6 may be too high)

### Short-term

4. **Add Fingerprint Validation**
   - Ensure all narratives have valid fingerprints
   - Normalize nucleus entity names (case, whitespace)
   - Validate actor lists are properly formatted

5. **Improve Matching Logic**
   - Consider lowering threshold for exact nucleus matches
   - Add special case for identical nucleus entities
   - Implement fuzzy matching for entity names

6. **Add Integration Tests**
   - Test matching with real narrative data
   - Verify updates don't create duplicates
   - Test edge cases (empty actors, missing fields)

## Test Script Usage

```bash
# Run the test script
poetry run python scripts/test_narrative_matching.py

# The script will:
# 1. Show current narrative count and recent narratives
# 2. Detect clusters from last 72 hours of articles
# 3. Test matching logic for each cluster
# 4. Display similarity scores for top candidates
# 5. Show summary of matches vs. new narratives
# 6. Run in dry-run mode (no database changes)
```

## Next Steps

1. ✅ Test script created and run successfully
2. ⏭️ Debug `find_matching_narrative()` function
3. ⏭️ Inspect fingerprint data in existing narratives
4. ⏭️ Fix matching logic based on findings
5. ⏭️ Re-run test to verify fixes
6. ⏭️ Deploy fix to production

## Conclusion

The test clearly demonstrates that **narrative matching is completely broken**. No clusters are matching existing narratives, which would result in massive duplication. This must be fixed before deploying any narrative detection updates.

The test script provides a reliable way to verify the matching logic and should be run after any fixes to ensure the problem is resolved.
