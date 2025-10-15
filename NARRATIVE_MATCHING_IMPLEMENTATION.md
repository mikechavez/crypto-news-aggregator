# Narrative Matching Implementation

## Overview
Implemented `find_matching_narrative()` function to check if a similar narrative already exists before creating a new one. This prevents duplicate narratives and enables narrative merging.

## Implementation Details

### Function: `find_matching_narrative()`
**Location:** `src/crypto_news_aggregator/services/narrative_service.py`

**Signature:**
```python
async def find_matching_narrative(
    fingerprint: Dict[str, Any],
    within_days: int = 14
) -> Optional[Dict[str, Any]]
```

**Parameters:**
- `fingerprint`: Narrative fingerprint dict with `nucleus_entity`, `top_actors`, `key_actions`
- `within_days`: Time window in days to search for matching narratives (default: 14)

**Returns:**
- Best matching narrative dict if similarity > 0.6
- `None` if no match found

### Algorithm

1. **Query Active Narratives**
   - Searches narratives with `last_updated` within time window
   - Filters by active statuses: `['emerging', 'rising', 'hot', 'cooling', 'dormant']`

2. **Calculate Similarity**
   - For each candidate narrative, extracts or constructs fingerprint
   - Uses `calculate_fingerprint_similarity()` from `narrative_themes.py`
   - Tracks best match across all candidates

3. **Return Best Match**
   - Returns narrative if similarity > 0.6 threshold
   - Returns `None` if no match exceeds threshold

### Key Features

#### Legacy Format Support
Handles narratives without `fingerprint` field by constructing from legacy fields:
```python
candidate_fingerprint = {
    'nucleus_entity': candidate.get('theme', ''),
    'top_actors': candidate.get('entities', []),
    'key_actions': []  # Legacy narratives may not have actions
}
```

#### Logging
- Debug: Similarity score for each candidate
- Info: Number of candidates evaluated
- Info: Best match found with similarity score
- Info: No match found with best similarity score

#### Error Handling
- Catches and logs exceptions
- Returns `None` on error to allow graceful fallback

## Usage Example

```python
from src.crypto_news_aggregator.services.narrative_service import find_matching_narrative

# Create fingerprint for new narrative
fingerprint = {
    'nucleus_entity': 'SEC',
    'top_actors': ['SEC', 'Binance', 'Coinbase'],
    'key_actions': ['filed lawsuit', 'regulatory enforcement']
}

# Check for existing match
existing_narrative = await find_matching_narrative(fingerprint, within_days=14)

if existing_narrative:
    # Update existing narrative
    print(f"Found match: {existing_narrative['title']}")
    # Merge new articles into existing narrative
else:
    # Create new narrative
    print("No match found, creating new narrative")
```

## Testing

### Test Coverage
Created comprehensive test suite in `tests/services/test_narrative_matching.py`:

1. **test_find_matching_narrative_with_match**
   - Tests finding a narrative above similarity threshold
   - Verifies correct narrative returned

2. **test_find_matching_narrative_no_match**
   - Tests when no narrative exceeds threshold
   - Verifies `None` returned

3. **test_find_matching_narrative_no_candidates**
   - Tests when no narratives exist in time window
   - Verifies `None` returned

4. **test_find_matching_narrative_legacy_format**
   - Tests matching with legacy narrative format
   - Verifies fingerprint construction from legacy fields

5. **test_find_matching_narrative_custom_time_window**
   - Tests custom time window parameter
   - Verifies query uses correct cutoff time

### Test Results
```
tests/services/test_narrative_matching.py::test_find_matching_narrative_with_match PASSED
tests/services/test_narrative_matching.py::test_find_matching_narrative_no_match PASSED
tests/services/test_narrative_matching.py::test_find_matching_narrative_no_candidates PASSED
tests/services/test_narrative_matching.py::test_find_matching_narrative_legacy_format PASSED
tests/services/test_narrative_matching.py::test_find_matching_narrative_custom_time_window PASSED

5 passed in 0.03s
```

## Integration Points

### Dependencies
- `calculate_fingerprint_similarity` from `narrative_themes.py`
- `mongo_manager` for database access
- Standard library: `datetime`, `timezone`, `timedelta`

### Database Query
```python
query = {
    'last_updated': {'$gte': cutoff_time},
    'status': {'$in': ['emerging', 'rising', 'hot', 'cooling', 'dormant']}
}
```

### Similarity Threshold
- **0.6**: Minimum similarity score to consider a match
- Based on weighted scoring:
  - Actor overlap (Jaccard): 50%
  - Nucleus match (exact): 30%
  - Action overlap (Jaccard): 20%

## Next Steps

1. **Integrate into Narrative Creation**
   - Call `find_matching_narrative()` before creating new narratives
   - Merge articles into existing narrative if match found
   - Update narrative metadata (article_count, last_updated, etc.)

2. **Add Merge Logic**
   - Combine article_ids from new and existing narratives
   - Recalculate lifecycle stage and momentum
   - Update narrative summary if needed

3. **Monitor Performance**
   - Track similarity scores in production
   - Adjust threshold if needed (currently 0.6)
   - Consider indexing `last_updated` and `status` fields

4. **Add Metrics**
   - Count of narratives merged vs created
   - Distribution of similarity scores
   - Time window effectiveness

## Configuration

### Tunable Parameters
- `within_days`: Default 14 days, adjustable per call
- Similarity threshold: Currently hardcoded at 0.6
- Active statuses: `['emerging', 'rising', 'hot', 'cooling', 'dormant']`

### Recommended Settings
- **Short-term news**: `within_days=7`, threshold=0.7
- **Long-term narratives**: `within_days=30`, threshold=0.5
- **Strict matching**: threshold=0.8
- **Loose matching**: threshold=0.5

## Files Modified

1. **src/crypto_news_aggregator/services/narrative_service.py**
   - Added import: `calculate_fingerprint_similarity`
   - Added function: `find_matching_narrative()`

2. **tests/services/test_narrative_matching.py** (new)
   - Comprehensive test suite with 5 test cases
   - Covers success, failure, and edge cases

## Summary

Successfully implemented narrative matching function that:
- ✅ Queries narratives within configurable time window
- ✅ Filters by active lifecycle statuses
- ✅ Calculates similarity using fingerprint comparison
- ✅ Returns best match if above 0.6 threshold
- ✅ Handles legacy narrative formats
- ✅ Includes comprehensive logging
- ✅ Has full test coverage (5/5 tests passing)

Ready for integration into narrative creation workflow to prevent duplicates and enable narrative merging.
