# Adaptive Matching Threshold Implementation

## Overview
Implemented adaptive matching thresholds in `find_matching_narrative()` to allow more lenient matching for recently updated narratives while maintaining strict matching for older stories.

## Implementation Details

### Threshold Strategy
- **Recent narratives** (updated within 48 hours): **0.5 threshold**
  - Allows near-term narrative continuations to merge more easily
  - Accounts for natural variance in actor mentions and phrasing
  - Helps ongoing stories stay connected despite minor differences
  
- **Older narratives** (>48 hours): **0.6 threshold**
  - Maintains strict matching to prevent unrelated stories from merging
  - Reduces false positives for dormant or cooling narratives

### Code Changes

**File:** `src/crypto_news_aggregator/services/narrative_service.py`

**Function:** `find_matching_narrative()`

#### Key Changes:
1. **48-hour cutoff calculation** (line 464-466):
   ```python
   now = datetime.now(timezone.utc)
   recent_cutoff = now - timedelta(hours=48)
   ```

2. **Per-candidate threshold determination** (line 482-491):
   ```python
   candidate_last_updated = candidate.get('last_updated')
   if candidate_last_updated and candidate_last_updated >= recent_cutoff:
       # Recent narrative (within 48h): use lower threshold (0.5)
       threshold = 0.5
       recency_label = "recent (48h)"
   else:
       # Older narrative: use stricter threshold (0.6)
       threshold = 0.6
       recency_label = "older (>48h)"
   ```

3. **Threshold-aware matching** (line 498-502):
   ```python
   # Track best match that meets its threshold
   if similarity >= threshold and similarity > best_similarity:
       best_similarity = similarity
       best_match = candidate
       best_threshold = threshold
   ```

4. **Enhanced logging** (line 493-496, 506-515):
   - Debug logs show which threshold applies to each candidate
   - Info logs report the threshold used for successful matches
   - No-match logs clarify the adaptive threshold strategy

### Benefits

1. **Better narrative continuity**: Ongoing stories with slight actor variance can now merge
2. **Reduced fragmentation**: Fewer duplicate narratives for the same evolving story
3. **Maintained precision**: Older narratives still require strong similarity to avoid false merges
4. **Transparent operation**: Detailed logging shows which threshold was applied and why

### Example Scenarios

#### Scenario 1: Recent Narrative Match
- Narrative last updated: 24 hours ago
- Similarity score: 0.52
- **Result**: Match (meets 0.5 threshold for recent narratives)
- **Log**: `"Found matching narrative: 'Title' (similarity: 0.520, threshold: 0.5)"`

#### Scenario 2: Older Narrative No Match
- Narrative last updated: 5 days ago
- Similarity score: 0.52
- **Result**: No match (below 0.6 threshold for older narratives)
- **Log**: `"No matching narrative found - best similarity: 0.520 (adaptive thresholds: 0.5 for recent, 0.6 for older)"`

#### Scenario 3: Strong Match
- Narrative last updated: 3 days ago
- Similarity score: 0.72
- **Result**: Match (exceeds both thresholds)
- **Log**: `"Found matching narrative: 'Title' (similarity: 0.720, threshold: 0.6)"`

## Testing

### Unit Tests Added

Three new test cases were added to `tests/services/test_narrative_matching.py`:

1. **`test_find_matching_narrative_adaptive_threshold_recent`**
   - Tests that recent narratives (within 48h) use 0.5 threshold
   - Verifies that moderate similarity (~0.5-0.6) matches for recent narratives

2. **`test_find_matching_narrative_adaptive_threshold_old`**
   - Tests that older narratives (>48h) use 0.6 threshold
   - Verifies that moderate similarity (~0.5-0.6) does NOT match for old narratives

3. **`test_find_matching_narrative_adaptive_threshold_boundary`**
   - Tests behavior at exactly 48-hour boundary
   - Confirms that narratives at the boundary use the 0.6 threshold (older)

### Running Tests

```bash
# Run all narrative matching tests
poetry run pytest tests/services/test_narrative_matching.py -v

# Run only adaptive threshold tests
poetry run pytest tests/services/test_narrative_matching.py -k adaptive_threshold -v
```

### Post-Deployment Monitoring

1. **Monitor narrative merging behavior** after deployment
2. **Check logs** for threshold application patterns
3. **Verify** that recent narratives merge appropriately
4. **Confirm** that older narratives maintain strict matching

## Related Configuration

The adaptive threshold works in conjunction with:
- **Adaptive grace period**: `calculate_grace_period()` adjusts time window based on velocity
- **Fingerprint similarity**: `calculate_fingerprint_similarity()` computes the similarity score
- **Lifecycle tracking**: Recent narratives are typically in 'hot', 'rising', or 'emerging' states

## Documentation Updates

Updated function docstring to document the adaptive threshold strategy and its rationale.
