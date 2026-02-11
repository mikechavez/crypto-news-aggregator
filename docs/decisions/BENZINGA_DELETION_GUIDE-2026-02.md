# Benzinga Article Deletion Guide

## Overview

The `delete_recent_benzinga.py` script safely removes recent Benzinga articles and all associated data from the database.

## What It Does

1. **Queries Benzinga articles** from the last 24 hours (configurable)
   - Filters by `source.id = "benzinga"`
   - Filters by `published_at > (24 hours ago)`
   - Shows article titles and publication dates

2. **Deletes entity_mentions** for each article
   - Uses `delete_entity_mentions_for_articles()` for batch deletion
   - Logs count of deleted entity_mentions

3. **Deletes articles** from the articles collection
   - Removes articles by their ObjectId
   - Logs count of deleted articles

4. **Clears signals cache**
   - Clears Redis cache entries matching `signals:trending:*`
   - Forces UI to refresh with updated data
   - In-memory cache auto-expires

5. **Recommends signal_scores cleanup**
   - Suggests running `cleanup_stale_signals.py` to remove orphaned signal scores
   - Or waiting for next scheduled recalculation

## Usage

### Preview Mode (Safe - Default)

```bash
# Preview what will be deleted (last 24 hours)
python scripts/delete_recent_benzinga.py --dry-run

# Preview with custom time window
python scripts/delete_recent_benzinga.py --dry-run --hours 48
```

### Deletion Mode (Requires Confirmation)

```bash
# Delete articles from last 24 hours
python scripts/delete_recent_benzinga.py --confirm

# Delete articles from last 48 hours
python scripts/delete_recent_benzinga.py --confirm --hours 48
```

## Command-Line Options

- `--dry-run`: Preview mode - shows what would be deleted without actually deleting (default)
- `--confirm`: Actually delete the data (requires user confirmation)
- `--hours N`: Number of hours to look back (default: 24)

## Example Output

### Dry Run Mode

```
======================================================================
DELETE RECENT BENZINGA ARTICLES
======================================================================

Looking for Benzinga articles from the last 24 hours...

🔍 DRY RUN MODE - No data will be deleted

Found 15 Benzinga articles:
----------------------------------------------------------------------
1. Bitcoin ETF Sees Record Inflows
   Published: 2025-10-19 14:30:00 UTC
   URL: https://benzinga.com/...
2. Ethereum Upgrade Scheduled for Q4
   Published: 2025-10-19 13:15:00 UTC
   URL: https://benzinga.com/...
...
----------------------------------------------------------------------

DRY RUN: Would delete 15 articles...
DRY RUN: Would delete 87 entity_mentions

DRY RUN: Would clear signals cache

======================================================================
SUMMARY
======================================================================
Articles that would be deleted: 15
Entity mentions that would be deleted: 87

======================================================================
SIGNAL SCORES UPDATE
======================================================================

DRY RUN: Signal scores would need to be recalculated.
Options after running with --confirm:
  1. Run: python scripts/cleanup_stale_signals.py --execute
  2. Wait for next scheduled signal calculation
  3. Manually trigger the signal calculation worker

======================================================================
To actually delete the data, run with --confirm flag:
  python scripts/delete_recent_benzinga.py --confirm --hours 24
======================================================================
```

### Confirm Mode

```
======================================================================
DELETE RECENT BENZINGA ARTICLES
======================================================================

Looking for Benzinga articles from the last 24 hours...

⚠️  LIVE MODE - Data will be permanently deleted

Are you sure you want to delete Benzinga articles? (yes/no): yes

Found 15 Benzinga articles:
----------------------------------------------------------------------
[Article list...]
----------------------------------------------------------------------

Deleting 15 articles...
✅ Deleted 87 entity_mentions
✅ Deleted 15 articles

Clearing signals cache...
✅ Cleared 12 Redis cache entries
✅ Cache cleared (in-memory cache will auto-expire)

======================================================================
SUMMARY
======================================================================
Articles deleted: 15
Entity mentions deleted: 87

======================================================================
SIGNAL SCORES UPDATE
======================================================================

⚠️  IMPORTANT: Signal scores need to be updated!

Recommended next steps:
  1. Run: python scripts/cleanup_stale_signals.py --execute
     This will remove stale signal_scores for deleted entities
  2. Or wait for the next scheduled signal calculation

✅ Deletion complete!
```

## Post-Deletion Steps

After deleting Benzinga articles, you should clean up stale signal scores:

```bash
# Preview stale signals
python scripts/cleanup_stale_signals.py --dry-run

# Remove stale signals
python scripts/cleanup_stale_signals.py --execute
```

This removes signal_scores for entities that no longer have any entity_mentions (orphaned from deleted articles).

## Safety Features

1. **Dry run by default**: Always previews changes before deletion
2. **Confirmation prompt**: Requires explicit "yes" confirmation in live mode
3. **Detailed logging**: Shows exactly what will be/was deleted
4. **Batch operations**: Efficient deletion of entity_mentions
5. **Cache clearing**: Ensures UI reflects changes immediately

## Technical Details

### Database Collections Affected

- **articles**: Benzinga articles are deleted
- **entity_mentions**: All mentions from deleted articles are removed
- **signal_scores**: Become stale (need cleanup with separate script)

### Cache Clearing

- **Redis**: Deletes keys matching `signals:trending:*`
- **In-memory**: Auto-expires after 60 seconds
- **Effect**: Forces API to recalculate trending signals on next request

### Query Logic

```python
query = {
    "source.id": "benzinga",
    "published_at": {"$gte": cutoff_time}
}
```

### Deletion Flow

1. Query articles → Get article IDs
2. Delete entity_mentions by article_id (batch)
3. Delete articles by _id (batch)
4. Clear cache (Redis + in-memory)
5. Log all operations

## Error Handling

- MongoDB connection errors are caught and logged
- Redis cache errors are non-fatal (falls back gracefully)
- Invalid article IDs are skipped
- Transaction-like behavior: entity_mentions deleted before articles

## Performance

- Batch operations for efficiency
- Async/await for non-blocking I/O
- Indexes used for fast queries:
  - `source.id` index
  - `published_at` index
  - `article_id` index on entity_mentions

## Related Scripts

- `cleanup_stale_signals.py`: Remove orphaned signal_scores
- `cleanup_orphaned_entity_data.py`: General entity data cleanup

## Notes

- Articles are permanently deleted (no soft delete)
- Entity mentions are cascade deleted
- Signal scores require separate cleanup
- Cache clears automatically force UI refresh
- No impact on narratives (they reference articles but don't depend on them)
