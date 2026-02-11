# Narrative Fingerprint Backfill

## Overview

The `backfill_narrative_fingerprints.py` script adds fingerprints to existing narratives in the database that don't have them. This enables intelligent narrative matching for new clusters.

## What It Does

1. **Queries all narratives** from the database
2. **For each narrative without a fingerprint**:
   - Computes fingerprint using `compute_narrative_fingerprint`
   - Uses `entities` list as `top_actors`
   - Uses `theme` as `nucleus_entity` (if no `nucleus_entity` exists)
   - Uses empty `actions` list
3. **Updates narrative documents** with computed fingerprints
4. **Logs progress** every 10 narratives
5. **Provides final summary** of total processed

## Usage

```bash
# Run the backfill script
poetry run python scripts/backfill_narrative_fingerprints.py
```

## Output

The script provides detailed logging:

```
================================================================================
NARRATIVE FINGERPRINT BACKFILL
================================================================================
📊 Total narratives in database: 36
🔍 Processing 36 narratives...

✅ Progress: 10 narratives updated (10/36 processed)
✅ Progress: 20 narratives updated (20/36 processed)
✅ Progress: 30 narratives updated (30/36 processed)

================================================================================
BACKFILL COMPLETE
================================================================================
📊 Total narratives processed: 36
✅ Narratives updated with fingerprints: 36
⏭️  Narratives skipped (already had fingerprint): 0
================================================================================
```

## Fingerprint Structure

Each fingerprint contains:

```python
{
    'nucleus_entity': 'regulatory',  # From theme or nucleus_entity field
    'top_actors': ['FTX', 'stablecoin', 'Bitget', ...],  # From entities list
    'key_actions': [],  # Empty for backfilled narratives
    'timestamp': datetime(2025, 10, 15, 19, 20, 45)  # When computed
}
```

## Idempotency

The script is **idempotent** - it can be run multiple times safely:
- Skips narratives that already have fingerprints
- Only updates narratives missing fingerprints
- Logs skipped narratives for transparency

## When to Run

Run this script:
- **After deploying narrative matching feature** - to enable matching for existing narratives
- **After database migrations** - if fingerprint field is removed or reset
- **For testing** - to verify fingerprint computation works correctly

## Related Files

- **Script**: `scripts/backfill_narrative_fingerprints.py`
- **Fingerprint computation**: `src/crypto_news_aggregator/services/narrative_themes.py::compute_narrative_fingerprint`
- **Narrative matching**: `src/crypto_news_aggregator/services/narrative_service.py::find_matching_narrative`

## Implementation Details

### Fingerprint Computation

For backfilled narratives:
- **nucleus_entity**: Uses existing `nucleus_entity` field, falls back to `theme`
- **top_actors**: Converts `entities` list to dict with default salience of 3
- **key_actions**: Empty list (legacy narratives don't have action data)

### Database Updates

Updates use MongoDB's `update_one` with `$set`:

```python
await narratives_collection.update_one(
    {'_id': narrative_id},
    {'$set': {'fingerprint': fingerprint}}
)
```

## Testing

Verify fingerprints were added:

```python
# Quick verification
from crypto_news_aggregator.db.mongodb import mongo_manager

db = await mongo_manager.get_async_database()
narratives = db.narratives

# Count narratives with fingerprints
with_fp = await narratives.count_documents({'fingerprint': {'$exists': True}})
total = await narratives.count_documents({})

print(f"Narratives with fingerprints: {with_fp}/{total}")
```

## Exit Codes

- **0**: Success (narratives updated or all already have fingerprints)
- **1**: Error during backfill

## Logging

The script uses Python's `logging` module:
- **INFO**: Progress updates, summaries
- **DEBUG**: Individual narrative processing details
- **ERROR**: Processing failures for specific narratives

Set `logging.DEBUG` in the script to see detailed per-narrative logs.
