# Verify Narrative Matching Fix

## Purpose
Verify that the narrative actions backfill succeeded and that narratives now match correctly with populated `key_actions`.

## Quick Start

```bash
# After running backfill_narrative_actions.py
python3 scripts/verify_matching_fix.py
```

## What It Does

### Part 1: Backfill Verification
Queries the database to show:
1. **Total narratives count** - All narratives in database
2. **Count with populated key_actions** - Narratives with non-empty actions
3. **Percentage with actions** - Success rate of backfill
4. **Sample 5 narratives** - Shows fingerprints with actions

### Part 2: Matching Test (Last 24 Hours)
Re-runs matching logic for recent narratives:
1. Finds narratives from last 24 hours
2. Tests each narrative against candidates
3. Calculates similarity scores
4. Counts matches vs new narratives
5. Shows top 5 similarity scores

### Part 3: Before vs After Comparison
Compares results:
- **Match rate**: 0% (before) vs actual% (after)
- **Top similarity**: Previous best vs new best
- **Threshold analysis**: How many exceed 0.6
- **Distribution**: Excellent/Good/Poor scores

## Expected Output

```
🔍 NARRATIVE MATCHING VERIFICATION
Verifying backfill and testing matching improvements

================================================================================
PART 1: BACKFILL VERIFICATION
================================================================================

1. Total narratives in database: 127
2. Narratives with populated key_actions: 115
3. Percentage with actions: 90.6%

4. Sample narratives with populated key_actions:
--------------------------------------------------------------------------------

Sample 1:
  Theme: regulatory_enforcement
  Title: SEC Intensifies Crypto Enforcement Actions
  Fingerprint:
    - Nucleus Entity: SEC
    - Top Actors: ['SEC', 'Binance', 'Coinbase', 'Kraken']
    - Key Actions: ['filed lawsuit', 'regulatory enforcement', 'compliance review']

Sample 2:
  Theme: defi_protocol
  Title: Uniswap Partnership Expansion
  Fingerprint:
    - Nucleus Entity: Uniswap
    - Top Actors: ['Uniswap', 'Coinbase', 'Arbitrum']
    - Key Actions: ['announced partnership', 'protocol integration']

...

================================================================================
PART 2: MATCHING TEST (LAST 24 HOURS)
================================================================================

Found 23 narratives from last 24 hours

Testing matching for 23 narratives...
--------------------------------------------------------------------------------
[1/23] regulatory_enforcement                    | ✓ MATCH (similarity: 0.735)
[2/23] defi_protocol                             | ✓ MATCH (similarity: 0.682)
[3/23] network_upgrade                           | ✗ NEW (best similarity: 0.450)
[4/23] market_movement                           | ✓ MATCH (similarity: 0.701)
...

================================================================================
MATCHING RESULTS
================================================================================

Total narratives tested: 23
Matches found (≥0.6 similarity): 15
New narratives (<0.6 similarity): 8
Match rate: 65.2%

Top 5 similarity scores achieved:
  1. 0.850
  2. 0.782
  3. 0.735
  4. 0.701
  5. 0.682

Top 5 matches:
  1. regulatory_enforcement                → sec_enforcement_actions              (similarity: 0.850)
  2. defi_adoption                         → defi_growth_narrative                (similarity: 0.782)
  3. bitcoin_etf                           → spot_etf_approval                    (similarity: 0.735)
  4. market_rally                          → bullish_momentum                     (similarity: 0.701)
  5. ethereum_upgrade                      → network_improvements                 (similarity: 0.682)

================================================================================
PART 3: BEFORE vs AFTER COMPARISON
================================================================================

📊 MATCH RATE
  Before backfill: 0.0%
  After backfill:  65.2%
  ✓ Improvement: +65.2 percentage points

📈 SIMILARITY SCORES
  Before backfill (best): 0.500
  After backfill (best):  0.850
  ✓ Improvement: +0.350

🎯 THRESHOLD ANALYSIS
  Matching threshold: 0.600
  Narratives above threshold: 15
  Narratives below threshold: 8

📊 SIMILARITY DISTRIBUTION (Top scores)
  Excellent (≥0.8): 3
  Good (0.6-0.8):  12
  Poor (<0.6):     8

================================================================================
CONCLUSION
================================================================================

✅ SUCCESS: Narratives are now matching!
   - 15 narratives matched successfully
   - Match rate improved from 0.0% to 65.2%
   - Top similarity score: 0.850

================================================================================
Verification complete!
================================================================================
```

## Understanding the Results

### Backfill Success
- **90%+ with actions**: Excellent - most narratives backfilled
- **70-90% with actions**: Good - some narratives may lack summaries
- **<70% with actions**: Poor - investigate why backfill failed

### Match Rate
- **>50% match rate**: Excellent - narratives merging well
- **30-50% match rate**: Good - reasonable deduplication
- **<30% match rate**: May need threshold adjustment

### Similarity Scores
- **≥0.8**: Excellent match - very similar narratives
- **0.6-0.8**: Good match - related narratives
- **<0.6**: Poor match - different narratives (correctly not matched)

## Interpreting Results

### Success Indicators
✅ High percentage of narratives with actions (>80%)  
✅ Match rate significantly above 0%  
✅ Top similarity scores above 0.7  
✅ Multiple narratives exceeding 0.6 threshold  

### Warning Signs
⚠️ Low percentage with actions (<50%)  
⚠️ Match rate still 0%  
⚠️ All similarity scores below 0.6  
⚠️ No narratives in "Excellent" range  

## Troubleshooting

### No Matches Found
**Possible reasons**:
1. Not enough narratives in last 24 hours
2. Narratives are genuinely different (good!)
3. Need more time for data accumulation

**Solution**: Wait for more narratives or extend time window

### Low Backfill Percentage
**Possible reasons**:
1. Many narratives lack summaries
2. API errors during backfill
3. Backfill script didn't complete

**Solution**: 
- Check backfill logs
- Re-run backfill script
- Investigate narratives without summaries

### Low Similarity Scores
**Possible reasons**:
1. Narratives are genuinely diverse
2. Actions not descriptive enough
3. Threshold may be too high

**Solution**:
- Review sample fingerprints
- Consider threshold adjustment
- Check action quality

## Technical Details

### Matching Logic
The script uses the same matching logic as production:
```python
from crypto_news_aggregator.services.narrative_service import find_matching_narrative
from crypto_news_aggregator.services.narrative_themes import calculate_fingerprint_similarity
```

### Similarity Calculation
```python
# Weighted scoring:
# - Actor overlap (Jaccard): 50% weight
# - Nucleus match (exact):   30% weight  
# - Action overlap (Jaccard): 20% weight
# Threshold: 0.6 (60% similarity)
```

### Time Window
- **Backfill verification**: All narratives
- **Matching test**: Last 24 hours only
- **Candidate search**: 14 days lookback

## Next Steps After Verification

### If Successful (>50% match rate)
1. ✅ Backfill is working
2. ✅ Monitor ongoing matching
3. ✅ Consider running narrative detection
4. ✅ Check for reduced duplicates

### If Partially Successful (20-50% match rate)
1. Review sample matches
2. Check action quality
3. Consider threshold tuning
4. Monitor over longer period

### If Unsuccessful (<20% match rate)
1. Review backfill logs
2. Check narrative summaries
3. Verify API key is working
4. Consider re-running backfill

## Verification Checklist

Before running:
- [ ] Backfill script has completed
- [ ] MongoDB is accessible
- [ ] At least some narratives exist

After running:
- [ ] Backfill percentage is >80%
- [ ] Sample fingerprints show actions
- [ ] Match rate is >0%
- [ ] Top similarity scores are >0.6
- [ ] Conclusion shows "SUCCESS"

## Related Files
- Backfill script: `scripts/backfill_narrative_actions.py`
- Test script: `scripts/test_action_extraction.py`
- Matching implementation: `src/crypto_news_aggregator/services/narrative_service.py`
- Similarity calculation: `src/crypto_news_aggregator/services/narrative_themes.py`

## Cost
This script only reads from the database - **no API calls, no cost**.

## Frequency
Run this script:
- ✅ Immediately after backfill
- ✅ After any matching threshold changes
- ✅ Weekly to monitor matching health
- ✅ When investigating duplicate narratives
