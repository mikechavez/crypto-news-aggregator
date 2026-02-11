# Narrative Matching Implementation Summary

## Overview
Updated the narrative detection worker to merge new articles into existing narratives instead of always creating new ones. This prevents narrative duplication and enables narratives to grow over time.

## Changes Made

### 1. Updated `narrative_service.py`

#### Imports
- Added `compute_narrative_fingerprint` to imports from `narrative_themes`
- Added `Counter` to imports from `collections`

#### Modified `detect_narratives()` Function
The function now implements intelligent narrative matching:

**Before clustering:**
- Clusters articles by nucleus entity and weighted actor/tension overlap (unchanged)

**After clustering (NEW BEHAVIOR):**
For each cluster:

1. **Build cluster fingerprint data**
   - Aggregate nucleus entities from all articles in cluster
   - Aggregate actors with their salience scores
   - Aggregate actions from narrative summaries
   - Determine primary nucleus entity (most common)

2. **Compute fingerprint**
   - Call `compute_narrative_fingerprint()` with cluster data
   - Fingerprint includes: nucleus_entity, top_actors, key_actions, timestamp

3. **Check for matching narrative**
   - Call `find_matching_narrative()` with fingerprint
   - Searches within 14-day window
   - Returns best match if similarity > 0.6

4. **Merge or Create**
   
   **If match found:**
   - Combine existing and new article_ids (union)
   - Update article_count
   - Set `last_updated` to current time
   - Set `needs_summary_update = True` (flag for future summary regeneration)
   - Update fingerprint with latest cluster data
   - Log merge action
   
   **If no match:**
   - Generate narrative from cluster
   - Add fingerprint to narrative document
   - Set `needs_summary_update = False` (fresh summary)
   - Insert new narrative into database
   - Include all standard fields (lifecycle, momentum, timeline_data, etc.)

5. **Logging**
   - Track matched_count and created_count
   - Log final summary: "X merged into existing, Y newly created, Z total"

### 2. Database Schema Updates

New fields added to narrative documents:
- `fingerprint`: Dict with nucleus_entity, top_actors, key_actions, timestamp
- `needs_summary_update`: Boolean flag indicating if summary should be regenerated

### 3. Test Coverage

Created comprehensive test suite:

**`test_narrative_matching.py`** (5 tests)
- Test finding matching narrative above similarity threshold
- Test when no narrative exceeds similarity threshold
- Test when no candidate narratives exist in time window
- Test matching with legacy narrative format (no fingerprint field)
- Test with custom time window parameter

**`test_narrative_detection_matching.py`** (3 tests)
- Test that detect_narratives merges new articles into existing narratives
- Test that detect_narratives creates new narrative when no match found
- Test that new narratives include the computed fingerprint

**Updated `test_narrative_service.py`**
- Fixed test expectations to match new direct database insertion behavior

## Key Benefits

1. **Prevents Duplication**: Similar narratives are merged instead of creating duplicates
2. **Narrative Growth**: Existing narratives accumulate articles over time
3. **Efficient Matching**: Fingerprint-based similarity scoring (0.6 threshold)
4. **Summary Refresh Tracking**: `needs_summary_update` flag enables future batch summary regeneration
5. **Backward Compatible**: Handles legacy narratives without fingerprints
6. **Time-Bounded**: Only searches within 14-day window for performance

## Example Flow

```
New Articles → Clustering → For each cluster:
                              ↓
                        Compute Fingerprint
                              ↓
                        Find Matching Narrative
                              ↓
                    ┌─────────┴─────────┐
                    ↓                   ↓
              Match Found          No Match
                    ↓                   ↓
            Merge Articles      Create New Narrative
            Set needs_update    Set needs_update=False
            Update fingerprint  Include fingerprint
```

## Configuration

- **Similarity Threshold**: 0.6 (in `find_matching_narrative`)
- **Time Window**: 14 days (configurable via `within_days` parameter)
- **Active Statuses**: emerging, rising, hot, cooling, dormant

## Future Enhancements

1. **Summary Regeneration Worker**: Process narratives with `needs_summary_update=True`
2. **Fingerprint Evolution Tracking**: Store fingerprint history to track narrative drift
3. **Configurable Thresholds**: Make similarity threshold and time window configurable
4. **Merge Conflict Resolution**: Handle cases where multiple narratives match

## Testing

All tests pass:
```bash
poetry run pytest tests/services/test_narrative_service.py \
                 tests/services/test_narrative_matching.py \
                 tests/services/test_narrative_detection_matching.py -v
```

Result: **17 passed, 6 warnings**
