# Backfill NULL Fingerprints Guide

**Script:** `scripts/backfill_null_fingerprints.py`  
**Purpose:** Fix 229 narratives with `nucleus_entity = None` by regenerating fingerprints from article data

## Problem Statement

229 narratives have NULL `nucleus_entity` in their `narrative_fingerprint` field, causing:
- Failed narrative matching/merging
- Duplicate narratives for the same story
- Fragmented signal scores
- Poor user experience

## Solution

This script:
1. Queries narratives with NULL/missing `narrative_fingerprint.nucleus_entity`
2. Fetches associated articles for each narrative
3. Extracts entity data from articles:
   - `nucleus_entity`: Most common nucleus across articles
   - `actors`: Combined actor salience (averaged)
   - `actions`: Unique actions from all articles
4. Generates new fingerprint using `compute_narrative_fingerprint()`
5. Updates narrative with regenerated fingerprint

## Usage

### 1. Preview Changes (Dry Run)
```bash
poetry run python scripts/backfill_null_fingerprints.py --dry-run
```

**What it does:**
- Shows what would be updated without making changes
- Safe to run anytime
- Good for testing

### 2. Test with Limited Sample
```bash
poetry run python scripts/backfill_null_fingerprints.py --limit 10 --verbose
```

**What it does:**
- Processes only first 10 narratives
- Shows detailed logs for each narrative
- Good for validation

### 3. Full Backfill (Production)
```bash
poetry run python scripts/backfill_null_fingerprints.py
```

**What it does:**
- Processes ALL narratives with NULL fingerprints
- Requires confirmation prompt (type 'y' to proceed)
- Updates database with new fingerprints

### 4. Full Backfill (Skip Confirmation)
```bash
poetry run python scripts/backfill_null_fingerprints.py --yes
```

**What it does:**
- Same as #3 but skips confirmation prompt
- Use in automated scripts

## Command-Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--limit N` | None | Process only N narratives (for testing) |
| `--batch-size N` | 50 | Number of narratives per batch |
| `--dry-run` | False | Preview without making changes |
| `--verbose` | False | Print detailed logs for each narrative |
| `--yes` | False | Skip confirmation prompt |

## Output

### Progress Logs
```
🔍 Querying narratives with NULL fingerprints...
📊 Found 229 narratives to process

📦 Processing batch 1/5 (50 narratives)
  ✅ Updated 'Bitcoin Price Volatility...' - nucleus=Bitcoin, actors=5, actions=3
  ⚠️  Narrative 'XYZ...' has no articles - skipping
   Batch complete: 48 successful, 0 failed, 2 skipped
```

### Summary Report
```
======================================================================
BACKFILL SUMMARY
======================================================================
Total narratives found:        229
Successfully updated:          220
Failed:                        2
Skipped (no articles):         5
Skipped (no entity data):      2
Total processed:               229
Success rate:                  96.1%
======================================================================
```

### Failure Log
If any narratives fail, their IDs are written to:
```
backfill_null_fingerprints_failures.log
```

## What Gets Updated

For each narrative, the script updates:

```python
{
  'narrative_fingerprint': {
    'nucleus_entity': 'Bitcoin',           # Most common nucleus from articles
    'top_actors': ['Bitcoin', 'SEC', ...], # Top 5 actors by salience
    'key_actions': ['price surge', ...],   # Top 3 actions
    'timestamp': datetime.now(timezone.utc)
  },
  'fingerprint_backfilled_at': datetime.now(timezone.utc)  # Audit trail
}
```

## Edge Cases Handled

### 1. Narratives with No Articles
**Scenario:** Narrative has empty `article_ids` array  
**Action:** Skip with warning  
**Log:** `⚠️ Narrative 'XYZ...' has no articles - skipping`

### 2. Articles Not Found in Database
**Scenario:** Article IDs exist but articles deleted/missing  
**Action:** Skip with warning  
**Log:** `⚠️ Narrative 'XYZ...' - no articles found in DB - skipping`

### 3. Articles with No Entity Data
**Scenario:** Articles exist but have no `nucleus_entity` or `actors`  
**Action:** Skip with warning  
**Log:** `⚠️ Narrative 'XYZ...' - no nucleus entity found - skipping`

### 4. Update Failures
**Scenario:** Database update fails  
**Action:** Log error and continue  
**Log:** `❌ Failed to update 'XYZ...'`

## Validation

After running the backfill, verify results:

```bash
# Check how many narratives still have NULL fingerprints
poetry run python scripts/check_duplicate_narratives.py
```

Expected result: **0 narratives with NULL nucleus_entity**

## Rollback

If something goes wrong, narratives can be identified by the `fingerprint_backfilled_at` field:

```javascript
// MongoDB query to find backfilled narratives
db.narratives.find({
  'fingerprint_backfilled_at': { $exists: true }
})
```

To revert (if needed):
```javascript
// Remove backfilled fingerprints
db.narratives.updateMany(
  { 'fingerprint_backfilled_at': { $exists: true } },
  { 
    $unset: { 
      'narrative_fingerprint': '',
      'fingerprint_backfilled_at': ''
    }
  }
)
```

## Performance

- **Batch size:** 50 narratives per batch (configurable)
- **Processing time:** ~1-2 seconds per narrative
- **Total time (229 narratives):** ~5-10 minutes
- **Database load:** Minimal (read-heavy, single update per narrative)

## Next Steps After Backfill

1. **Verify Results**
   ```bash
   poetry run python scripts/check_duplicate_narratives.py
   ```

2. **Run Narrative Matching**
   After fingerprints are regenerated, run matching logic to merge duplicates:
   ```bash
   poetry run python scripts/match_duplicate_narratives.py
   ```

3. **Monitor for New NULL Fingerprints**
   Add validation to prevent future NULL fingerprints:
   - Add database constraint
   - Add validation in narrative creation logic
   - Add monitoring alert

## Troubleshooting

### Issue: "No narratives found with NULL fingerprints"
**Cause:** All narratives already have valid fingerprints  
**Solution:** No action needed - backfill already complete

### Issue: High skip rate (>20%)
**Cause:** Many narratives have no articles or missing entity data  
**Solution:** 
1. Check article extraction pipeline
2. Run entity extraction backfill first
3. Review narrative creation logic

### Issue: Script hangs or times out
**Cause:** Database connection issues or large batch size  
**Solution:**
1. Reduce batch size: `--batch-size 10`
2. Check MongoDB connection
3. Run with `--limit 50` to test smaller subset

### Issue: Permission denied
**Cause:** Script not executable  
**Solution:**
```bash
chmod +x scripts/backfill_null_fingerprints.py
```

## Code Reference

### Key Functions

- **`get_narratives_with_null_fingerprints()`**: Query narratives with NULL fingerprints
- **`fetch_articles_for_narrative()`**: Fetch articles by IDs
- **`extract_entities_from_articles()`**: Aggregate entity data from articles
- **`compute_narrative_fingerprint()`**: Generate fingerprint (from `narrative_themes.py`)
- **`update_narrative_fingerprint()`**: Update narrative in database

### Query Used

```python
query = {
    '$or': [
        {'narrative_fingerprint.nucleus_entity': None},
        {'narrative_fingerprint.nucleus_entity': {'$exists': False}},
        {'narrative_fingerprint': {'$exists': False}}
    ]
}
```

## Related Documentation

- **Root Cause Analysis:** `DUPLICATE_NARRATIVES_ANALYSIS.md`
- **Narrative Fingerprints:** `NARRATIVE_FINGERPRINT_SUMMARY.md`
- **Entity Extraction:** `docs/BACKFILL_ENTITIES.md`

## Support

If you encounter issues:
1. Check logs in console output
2. Review `backfill_null_fingerprints_failures.log`
3. Run with `--verbose` flag for detailed debugging
4. Check MongoDB connection and permissions
