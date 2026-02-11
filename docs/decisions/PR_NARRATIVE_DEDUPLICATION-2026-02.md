# PR: Narrative Deduplication

## Summary
Implements narrative deduplication to merge similar stories based on entity overlap, reducing redundancy in narrative detection.

## Changes

### New Service: `narrative_deduplication.py`
- **Jaccard Similarity Calculation**: Computes entity overlap between narratives
  - Formula: `|intersection| / |union|`
  - Returns score from 0.0 (no overlap) to 1.0 (identical)
  
- **Merge Logic**: Groups and merges similar narratives
  - Default threshold: 0.7 (70% entity overlap)
  - Keeps narrative with most articles as base
  - Merges all unique entities from group
  - Sums article counts across merged narratives
  
- **Main Entry Point**: `deduplicate_narratives(narratives, threshold=0.7)`
  - Returns: `(deduplicated_list, num_merged)`

### Integration: `worker.py`
- Added deduplication step to `update_narratives()` function
- Runs after narrative detection, before database upsert
- Logs: `"Merged X duplicate narratives"` when duplicates found

### Tests: `test_narrative_deduplication.py`
- **20 comprehensive tests**, all passing
- Coverage includes:
  - Similarity calculation edge cases
  - Merge logic with various thresholds
  - Empty inputs and single narratives
  - Multiple merge groups
  - Custom thresholds

## Example Behavior

**Before Deduplication:**
```
1. "Bitcoin & Ethereum Rally" - [Bitcoin, Ethereum, Solana] - 15 articles
2. "BTC/ETH/SOL Pump" - [Bitcoin, Ethereum, Solana] - 8 articles
3. "Cardano Update" - [Cardano, Polkadot] - 5 articles
```

**After Deduplication (threshold=0.7):**
```
1. "Bitcoin & Ethereum Rally" - [Bitcoin, Ethereum, Solana] - 23 articles (merged)
2. "Cardano Update" - [Cardano, Polkadot] - 5 articles
```

**Log Output:**
```
INFO: Merged 1 duplicate narratives
INFO: Updated 2 narratives
```

## Technical Details

### Jaccard Similarity Examples
- Identical sets: `{BTC, ETH}` vs `{BTC, ETH}` → 1.0 (100% match)
- High overlap: `{BTC, ETH, SOL}` vs `{BTC, ETH, ADA}` → 0.5 (50% match)
- Threshold match: `{BTC, ETH, SOL, BNB}` vs `{BTC, ETH, SOL}` → 0.75 (above 0.7 threshold)

### Merge Strategy
1. Find all narratives with similarity ≥ threshold
2. Group similar narratives together
3. Sort group by article_count (descending)
4. Use highest-count narrative as base
5. Merge all unique entities
6. Sum article counts

## Testing

### Unit Tests
```bash
poetry run pytest tests/services/test_narrative_deduplication.py -v
# Result: 20 passed in 0.03s
```

### Integration Test
Verified end-to-end with realistic data:
- 3 input narratives (2 similar, 1 distinct)
- Correctly merged to 2 narratives
- Article counts summed correctly (15 + 8 = 23)

## Deployment Plan

1. **Merge PR** to main branch
2. **Railway auto-deploys** from main
3. **Monitor logs** for:
   - `"Merged X duplicate narratives"` messages
   - Narrative update cycles running smoothly
   - No errors in deduplication logic

## Benefits

- **Reduces redundancy**: Eliminates duplicate narratives with similar entity sets
- **Better UX**: Users see consolidated narratives instead of near-duplicates
- **Accurate counts**: Article counts reflect true coverage across merged narratives
- **Configurable**: Threshold can be adjusted if needed (default 0.7 works well)
- **Safe**: Only merges when similarity is high, preserves distinct narratives

## Monitoring

After deployment, check Railway logs for:
```
INFO: Starting narrative update cycle...
INFO: Found X trending entities for narrative detection
INFO: Found Y co-occurring entity groups
INFO: Generated Z narrative summaries
INFO: Merged N duplicate narratives  # <-- New log line
INFO: Updated M narratives
```

## Rollback Plan

If issues arise:
1. Revert commit: `git revert <commit-hash>`
2. Push to main
3. Railway auto-deploys previous version
4. Deduplication is bypassed, narratives work as before

## Future Enhancements

- Make threshold configurable via environment variable
- Add metrics tracking (merge rate, avg similarity)
- Consider semantic similarity (not just entity overlap)
- Add deduplication to API response (runtime dedup)
