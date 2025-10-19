# Merge Duplicate Narratives Guide

**Script:** `scripts/merge_duplicate_narratives.py`  
**Purpose:** Consolidate narratives with matching fingerprints after backfill

## Overview

After running `backfill_null_fingerprints.py`, many narratives will have matching `nucleus_entity` values (e.g., dozens about "Bitcoin", "Ethereum", etc.). This script merges narratives with similar fingerprints to eliminate duplication.

## When to Run

**Run this script AFTER:**
1. ✅ `backfill_null_fingerprints.py` has completed
2. ✅ All narratives have valid fingerprints with `nucleus_entity`
3. ✅ You've verified fingerprint quality

**Expected scenario:**
- 229 narratives had NULL fingerprints
- After backfill, many will have same `nucleus_entity` (e.g., "Bitcoin", "Ethereum")
- This script merges those duplicates into consolidated narratives

## How It Works

### 1. Grouping Phase
```
Query all narratives → Group by nucleus_entity
```

Example groups:
- **Bitcoin:** 45 narratives
- **Ethereum:** 32 narratives  
- **SEC:** 18 narratives
- **Binance:** 12 narratives

### 2. Similarity Calculation

For each group with 2+ narratives:
- Calculate pairwise fingerprint similarity
- Use `calculate_fingerprint_similarity()` from production code
- Apply adaptive thresholds:
  - **Recent (updated within 48h):** 0.5 threshold
  - **Older (>48h):** 0.6 threshold (or custom via `--threshold`)

### 3. Merge Decision

If similarity >= threshold:
- **Select primary:** Narrative with most articles
- **Merge data:**
  - Combine `article_ids` (deduplicated)
  - Average `entity_salience` scores
  - Recalculate `lifecycle_state` based on combined metrics
- **Delete duplicate:** Remove merged narrative
- **Log merge:** Record details for audit

## Usage

### 1. Preview Merges (Recommended First Step)

```bash
poetry run python scripts/merge_duplicate_narratives.py --dry-run --verbose
```

**What it does:**
- Shows what would be merged without making changes
- Displays similarity scores for each pair
- Safe to run anytime

**Expected output:**
```
🔍 Checking nucleus 'Bitcoin' (45 narratives)
   Found 12 duplicate pairs
   [DRY RUN] Would merge 'Bitcoin Price Volatility...' (5 articles) 
   → 'Bitcoin Market Analysis...' (23 articles) [similarity: 0.723]
   ...

MERGE SUMMARY
Total narratives:              229
Duplicate pairs found:         48
Would merge: 48 duplicates into 181 narratives
Reduction: 229 → 181 narratives (21.0% reduction)
```

### 2. Merge with Default Threshold

```bash
poetry run python scripts/merge_duplicate_narratives.py
```

**What it does:**
- Uses adaptive thresholds (0.5 for recent, 0.6 for older)
- Asks for confirmation before proceeding
- Performs actual merges and deletes duplicates

**Expected output:**
```
❓ Proceed with merge? [y/N]: y
🚀 Starting merge...

🔍 Checking nucleus 'Bitcoin' (45 narratives)
   ✅ Merged 'Bitcoin Price Volatility...' (5 articles) 
   → 'Bitcoin Market Analysis...' (23 articles) [similarity: 0.723]
   ...

MERGE SUMMARY
Merges performed:              48
Narratives deleted:            48
Articles consolidated:         156
Reduction: 229 → 181 narratives (21.0% reduction)
```

### 3. Merge with Custom Threshold

```bash
poetry run python scripts/merge_duplicate_narratives.py --threshold 0.7
```

**What it does:**
- Uses stricter threshold (0.7) for older narratives
- Recent narratives still use 0.5
- More conservative merging

### 4. Merge Specific Nucleus Only

```bash
poetry run python scripts/merge_duplicate_narratives.py --nucleus "Bitcoin" --verbose
```

**What it does:**
- Only processes narratives with `nucleus_entity = "Bitcoin"`
- Useful for testing or targeted cleanup
- Shows detailed logs for each pair

### 5. Automated Merge (Skip Confirmation)

```bash
poetry run python scripts/merge_duplicate_narratives.py --yes
```

**What it does:**
- Skips confirmation prompt
- Useful for automated scripts or CI/CD

## Command-Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--threshold N` | 0.6 | Base similarity threshold for older narratives |
| `--nucleus "X"` | None | Only merge narratives with this nucleus_entity |
| `--dry-run` | False | Preview merges without executing |
| `--verbose` | False | Print detailed logs for each group |
| `--yes` | False | Skip confirmation prompt |

## Merge Logic

### Primary Selection

When merging two narratives, the **primary** (kept) is selected by:

1. **Most articles** (highest priority)
2. **Most recent `last_updated`** (if article count equal)
3. **Earliest `created_at`** (if still tied)

**Example:**
```
Narrative A: 23 articles, updated 2 days ago
Narrative B: 5 articles, updated 1 day ago
→ Primary: Narrative A (more articles)
```

### Data Merging

**Article IDs:**
- Combine both lists
- Deduplicate (set union)
- Sort by published date

**Entity Salience:**
- Combine salience scores for all entities
- Average scores where entity appears in both
- Preserve unique entities from each

**Lifecycle State:**
- Recalculate based on combined article count
- Consider time span of all articles
- Use `calculate_lifecycle_state()` from production

### Adaptive Thresholds

The script uses the same adaptive threshold logic as production:

| Narrative Age | Threshold | Rationale |
|---------------|-----------|-----------|
| Updated within 48h | 0.5 | Allow easier continuation of recent stories |
| Older than 48h | 0.6 (or custom) | Maintain strict matching to prevent unrelated merges |

**Why adaptive?**
- Recent narratives naturally have variance in actor mentions
- Older narratives should match more strictly to avoid false positives

## Output Examples

### Dry Run Output
```
🔍 Querying all narratives...
📊 Found 229 total narratives
📦 Grouping narratives by nucleus_entity...
📊 Found 15 unique nucleus entities

⚠️  DRY RUN MODE - No changes will be saved

🔍 Checking nucleus 'Bitcoin' (45 narratives)
   Found 12 duplicate pairs
   [DRY RUN] Would merge 'Bitcoin Price Volatility...' (5 articles) 
   → 'Bitcoin Market Analysis...' (23 articles) [similarity: 0.723]
   [DRY RUN] Would merge 'Bitcoin Trading Volume...' (8 articles) 
   → 'Bitcoin Market Analysis...' (23 articles) [similarity: 0.681]
   ...

🔍 Checking nucleus 'Ethereum' (32 narratives)
   Found 8 duplicate pairs
   ...

======================================================================
MERGE SUMMARY
======================================================================
Total narratives:              229
Unique nucleus entities:       15
Groups with duplicates:        8
Duplicate pairs found:         48
Merges performed:              48
Narratives deleted:            48
Articles consolidated:         156

Reduction: 229 → 181 narratives (21.0% reduction)

⚠️  This was a DRY RUN - no changes were saved
======================================================================
```

### Live Merge Output
```
🚀 Starting merge...

🔍 Checking nucleus 'Bitcoin' (45 narratives)
   Found 12 duplicate pairs
   ✅ Merged 'Bitcoin Price Volatility...' (5 articles) 
   → 'Bitcoin Market Analysis...' (23 articles) [similarity: 0.723]
   ✅ Merged 'Bitcoin Trading Volume...' (8 articles) 
   → 'Bitcoin Market Analysis...' (23 articles) [similarity: 0.681]
   ...

======================================================================
MERGE SUMMARY
======================================================================
Total narratives:              229
Merges performed:              48
Narratives deleted:            48
Articles consolidated:         156

Reduction: 229 → 181 narratives (21.0% reduction)
======================================================================
```

## Validation

### Before Merge
```bash
# Check current duplicate count
poetry run python scripts/check_duplicate_narratives.py
```

Expected: 229 narratives with same nucleus_entity

### After Merge
```bash
# Verify duplicates reduced
poetry run python scripts/check_duplicate_narratives.py
```

Expected: Significantly fewer duplicates (e.g., 181 narratives)

### Verify Data Integrity
```javascript
// MongoDB query to check merged narratives
db.narratives.find({
  'merged_at': { $exists: true }
}).count()

// Check article consolidation
db.narratives.aggregate([
  { $match: { merged_at: { $exists: true } } },
  { $project: { title: 1, article_count: { $size: '$article_ids' } } }
])
```

## Edge Cases

### 1. No Duplicates Found
**Scenario:** All narratives have unique fingerprints  
**Output:** `Duplicate pairs found: 0`  
**Action:** No merges needed

### 2. Circular Dependencies
**Scenario:** A matches B, B matches C, but A doesn't match C  
**Handling:** Each pair evaluated independently, may result in chain merges

### 3. Merge Failures
**Scenario:** Database update fails  
**Handling:** Log error, continue with other merges, report in summary

### 4. Multiple Matches
**Scenario:** Narrative A matches both B and C  
**Handling:** Process pairwise, A may absorb both B and C

## Troubleshooting

### Issue: "No duplicates found" but you expect many
**Cause:** Threshold too high or fingerprints too different  
**Solution:**
```bash
# Try lower threshold
poetry run python scripts/merge_duplicate_narratives.py --threshold 0.5 --dry-run
```

### Issue: Too many merges (false positives)
**Cause:** Threshold too low  
**Solution:**
```bash
# Use stricter threshold
poetry run python scripts/merge_duplicate_narratives.py --threshold 0.7 --dry-run
```

### Issue: Specific nucleus has issues
**Cause:** Bad fingerprints or edge case  
**Solution:**
```bash
# Test specific nucleus
poetry run python scripts/merge_duplicate_narratives.py --nucleus "Bitcoin" --verbose --dry-run
```

### Issue: Merge fails for some pairs
**Cause:** Database connection, missing articles, or data corruption  
**Solution:**
1. Check MongoDB connection
2. Verify articles exist for all article_ids
3. Review failed_merges in summary

## Performance

- **Processing time:** ~1-2 seconds per nucleus group
- **Total time (229 narratives, 15 groups):** ~30-60 seconds
- **Database operations:**
  - Read: 1 query for all narratives + N queries for article dates
  - Write: 1 update + 1 delete per merge
- **Memory usage:** Low (processes one group at a time)

## Rollback

If merges need to be reverted:

### Option 1: Restore from Backup
```bash
# Restore narratives collection from backup
mongorestore --uri="$MONGODB_URI" --nsInclude="crypto_news.narratives" dump/
```

### Option 2: Manual Revert (if merged_at field exists)
```javascript
// Find merged narratives
db.narratives.find({ merged_at: { $exists: true } })

// Note: Deleted narratives cannot be easily restored without backup
// Prevention: Always run --dry-run first!
```

## Best Practices

### 1. Always Dry Run First
```bash
poetry run python scripts/merge_duplicate_narratives.py --dry-run --verbose
```

### 2. Test on Specific Nucleus
```bash
poetry run python scripts/merge_duplicate_narratives.py --nucleus "Bitcoin" --dry-run
```

### 3. Start with Stricter Threshold
```bash
poetry run python scripts/merge_duplicate_narratives.py --threshold 0.7 --dry-run
```

### 4. Backup Before Production Merge
```bash
mongodump --uri="$MONGODB_URI" --collection=narratives --out=backup/
```

### 5. Monitor Results
```bash
# Check narrative count before and after
poetry run python scripts/check_duplicate_narratives.py
```

## Next Steps After Merge

### 1. Verify Results
```bash
poetry run python scripts/check_duplicate_narratives.py
```

### 2. Update Frontend Cache
If using caching, clear narrative cache to reflect merged data

### 3. Monitor Lifecycle States
Check that merged narratives have correct lifecycle states

### 4. Add Prevention
- Add validation to prevent future NULL fingerprints
- Add monitoring for duplicate narratives
- Consider running merge script periodically

## Related Documentation

- **Backfill Guide:** `BACKFILL_NULL_FINGERPRINTS_GUIDE.md`
- **Duplicate Analysis:** `DUPLICATE_NARRATIVES_ANALYSIS.md`
- **Fingerprint Logic:** `NARRATIVE_FINGERPRINT_SUMMARY.md`

## Support

If you encounter issues:
1. Run with `--dry-run --verbose` to diagnose
2. Check MongoDB connection and permissions
3. Verify fingerprints are valid
4. Review similarity scores in output
