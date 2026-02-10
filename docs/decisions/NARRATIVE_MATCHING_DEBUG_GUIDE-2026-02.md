# Narrative Matching Debug Guide

## Overview

The `debug_production_matching.py` script analyzes why new narratives were created instead of matching existing ones. This helps identify issues with the matching threshold, fingerprint similarity calculation, or grace period logic.

## Problem Context

In the 72-hour test, 15 new narratives were created when they potentially should have matched existing narratives. This script investigates each new narrative to understand why matching failed.

## Script Location

```bash
scripts/debug_production_matching.py
```

## Usage

### Basic Usage (Last 24 Hours)

```bash
poetry run python scripts/debug_production_matching.py
```

### Custom Time Window

```bash
# Analyze narratives created in last 72 hours
poetry run python scripts/debug_production_matching.py --hours 72

# Analyze narratives created in last 7 days
poetry run python scripts/debug_production_matching.py --hours 168
```

## What It Analyzes

For each new narrative created in the specified time window, the script shows:

### 1. Fingerprint Components

- **Nucleus Entity**: The central entity the narrative is about
- **Top Actors**: Up to 5 key participants (sorted by salience)
- **Key Actions**: Up to 3 main events/actions

### 2. Top 3 Similarity Scores

Shows the 3 most similar existing narratives that were available when this narrative was created, including:
- Narrative title
- Similarity score (0.0-1.0)
- Their fingerprints
- When they were created/updated

### 3. Why It Didn't Match

Categorizes the reason into one of three categories:

#### `similarity_below_threshold`
- Best similarity score was < 0.6 (the matching threshold)
- Indicates genuinely different narratives OR threshold too strict

#### `no_candidates_found`
- No existing narratives were found within the time window
- Could indicate grace period is too short

#### `should_have_matched`
- Similarity score was ≥ 0.6 but matching still failed
- **This is a bug** - indicates a problem with the matching logic

### 4. Same Nucleus Entity Check

Lists existing narratives with the same nucleus entity to see if they should have matched based on the central topic.

## Output Structure

### Summary Section

```
SUMMARY
================================================================================

Total new narratives analyzed: 15

Reasons for not matching:
  - similarity_below_threshold: 12 (80.0%)
  - no_candidates_found: 2 (13.3%)
  - should_have_matched: 1 (6.7%)
```

### Detailed Analysis

For each narrative:

```
1. Bitcoin's Resilience Amid Market Volatility
   ID: 67890abcdef12345
   Created: 2025-10-15 14:23:45+00:00
   Reason: similarity_below_threshold
   Fingerprint:
     Nucleus: Bitcoin
     Actors: Bitcoin, Ethereum, ETFs, Traders, Markets
     Actions: price volatility, market correction, institutional buying

   Top 3 Candidate Matches:
   1. Bitcoin Price Surge Continues
      Similarity: 0.543
      Created: 2025-10-14 10:15:30+00:00
      Last Updated: 2025-10-15 08:45:12+00:00
      Fingerprint:
        Nucleus: Bitcoin
        Actors: Bitcoin, Investors, ETFs, Exchanges, Whales
        Actions: price increase, all-time high, market rally
```

## Interpreting Results

### High Similarity But No Match (≥ 0.6)

**Problem**: Bug in matching logic
**Action**: Investigate `find_matching_narrative()` in `narrative_service.py`

### Low Similarity (< 0.6) with Same Nucleus

**Problem**: Threshold may be too strict OR fingerprints are genuinely different
**Action**: 
- Review fingerprint components to see if they're truly different
- Consider lowering threshold if narratives are clearly related
- Check if actor/action extraction is working correctly

### No Candidates Found

**Problem**: Grace period may be too short
**Action**:
- Check if related narratives exist outside the time window
- Consider increasing the grace period (currently 7-30 days adaptive)
- Review `calculate_grace_period()` logic

### Many Narratives with Same Nucleus But Low Similarity

**Problem**: Actor or action overlap is too low
**Action**:
- Review the similarity calculation weights:
  - Nucleus match: 30%
  - Actor overlap: 50%
  - Action overlap: 20%
- Consider adjusting weights if nucleus match should be more important

## Similarity Calculation

The fingerprint similarity is calculated as:

```
similarity = (nucleus_match * 0.3) + (actor_overlap * 0.5) + (action_overlap * 0.2)
```

Where:
- **nucleus_match**: 1.0 if exact match, 0.0 otherwise
- **actor_overlap**: Jaccard similarity of top_actors sets
- **action_overlap**: Jaccard similarity of key_actions sets

### Example

```python
fingerprint1 = {
    'nucleus_entity': 'SEC',
    'top_actors': ['SEC', 'Binance', 'Coinbase'],
    'key_actions': ['filed lawsuit', 'regulatory enforcement']
}

fingerprint2 = {
    'nucleus_entity': 'SEC',
    'top_actors': ['SEC', 'Binance', 'Kraken'],
    'key_actions': ['filed lawsuit', 'compliance review']
}

# Calculation:
# nucleus_match = 1.0 (SEC == SEC)
# actor_overlap = 2/4 = 0.5 (2 common actors, 4 total unique)
# action_overlap = 1/3 = 0.333 (1 common action, 3 total unique)
# similarity = (1.0 * 0.3) + (0.5 * 0.5) + (0.333 * 0.2) = 0.617
```

## Common Issues and Solutions

### Issue: Too Many New Narratives Created

**Symptoms**: High percentage of `similarity_below_threshold`

**Possible Causes**:
1. Threshold (0.6) is too strict
2. Fingerprint extraction is inconsistent
3. Actor/action lists are too different even for related narratives

**Solutions**:
1. Lower threshold to 0.5 or 0.55
2. Improve actor/action extraction consistency
3. Adjust similarity weights to favor nucleus match more

### Issue: Narratives Not Matching Despite Same Topic

**Symptoms**: Same nucleus entity but low similarity scores

**Possible Causes**:
1. Actor lists are completely different
2. Action lists have no overlap
3. Weights favor actor/action overlap too much

**Solutions**:
1. Increase nucleus match weight from 0.3 to 0.4 or 0.5
2. Decrease actor overlap weight from 0.5 to 0.4 or 0.3
3. Review if actor extraction is capturing the right entities

### Issue: Old Narratives Not Being Considered

**Symptoms**: High percentage of `no_candidates_found`

**Possible Causes**:
1. Grace period is too short
2. Old narratives are marked as inactive
3. Time window calculation is incorrect

**Solutions**:
1. Increase grace period (currently 7-30 days adaptive)
2. Check lifecycle state filtering in `find_matching_narrative()`
3. Review `calculate_grace_period()` logic

## Related Files

- **Matching Logic**: `src/crypto_news_aggregator/services/narrative_service.py`
  - `find_matching_narrative()` - Main matching function
  - `calculate_grace_period()` - Adaptive time window
  - `determine_lifecycle_state()` - Lifecycle state calculation

- **Fingerprint Logic**: `src/crypto_news_aggregator/services/narrative_themes.py`
  - `compute_narrative_fingerprint()` - Fingerprint creation
  - `calculate_fingerprint_similarity()` - Similarity calculation

- **Database Operations**: `src/crypto_news_aggregator/db/operations/narratives.py`
  - `upsert_narrative()` - Create/update narratives

## Next Steps After Analysis

1. **Review the summary statistics** to identify the primary issue
2. **Examine detailed analysis** for specific narratives with unexpected results
3. **Check fingerprint components** to ensure they're being extracted correctly
4. **Adjust matching parameters** based on findings:
   - Threshold (currently 0.6)
   - Similarity weights (nucleus: 0.3, actors: 0.5, actions: 0.2)
   - Grace period (currently 7-30 days adaptive)
5. **Re-run narrative detection** to test changes
6. **Re-run this debug script** to verify improvements

## Example Workflow

```bash
# 1. Run the debug script to identify issues
poetry run python scripts/debug_production_matching.py --hours 72

# 2. Review the output and identify the primary issue
# Example: 80% of narratives have similarity_below_threshold

# 3. Adjust matching parameters in narrative_service.py
# Example: Lower threshold from 0.6 to 0.55

# 4. Re-run narrative detection to test
poetry run python scripts/trigger_narrative_detection.py --hours 72

# 5. Re-run debug script to verify improvements
poetry run python scripts/debug_production_matching.py --hours 72
```

## Troubleshooting

### Script Fails to Connect to Database

**Error**: `Connection refused` or `Authentication failed`

**Solution**: Ensure MongoDB connection is configured correctly in environment variables

### No Narratives Found

**Output**: `No new narratives found in the specified time window`

**Solution**: 
- Increase `--hours` parameter
- Check if narratives are being created at all
- Verify `first_seen` field is being set correctly

### Memory Issues with Large Time Windows

**Error**: `MemoryError` or script hangs

**Solution**: 
- Reduce `--hours` parameter
- Process narratives in batches
- Add pagination to the script

## Performance Notes

- Script loads all narratives into memory for comparison
- Typical runtime: 5-30 seconds depending on database size
- For large databases (>1000 narratives), consider adding pagination
- MongoDB queries are optimized with indexes on `first_seen` and `last_updated`
