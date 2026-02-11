# Orphaned Entity Data Fix - "Zoom" Entity Issue

**Date:** October 19, 2025  
**Status:** ✅ **FIXED - Ready for Deployment**  
**Branch:** `fix/benzinga-blacklist-enforcement` (will create new branch)

## Problem

The "Zoom" entity showed in Signals endpoint but had no articles, causing a confusing user experience.

## Root Cause Analysis

### Investigation Results

1. **Signal Score Exists:**
   - Entity: "Zoom" (company)
   - Score 7d: 1.3
   - Mentions 7d: 11
   - Last Updated: 2025-10-15

2. **But No Entity Mentions:**
   - `entity_mentions` count for "Zoom": **0**
   - The mentions were deleted (likely when articles were cleaned up)

3. **Stale Signal Scores:**
   - Found **21 total stale signal_scores** with no entity_mentions
   - These are leftover from deleted articles/mentions
   - Examples: Zoom, Airbnb, FedEx, Costco, Snap, Ford, etc.

### Why This Happened

1. Articles were deleted (manual cleanup or data migration)
2. Entity_mentions were deleted (cascade or cleanup)
3. **Signal_scores were NOT updated** - they became stale
4. Signals endpoint returned these stale entities
5. `get_recent_articles_for_entity()` found no articles → empty list

## Solution: 3-Part Fix

### Part 1: Filter Stale Signals in Query ✅

**File:** `src/crypto_news_aggregator/db/operations/signal_scores.py`

Modified `get_trending_entities()` to:
- Verify each entity has current mentions before including it
- Fetch `limit * 2` signals to account for filtering
- Only return entities with `mention_count > 0`

```python
# Verify entity has current mentions (filter out stale signals)
mention_count = await entity_mentions.count_documents(
    {"entity": entity},
    limit=1
)

if mention_count > 0:
    results.append(signal)
```

### Part 2: Cleanup Script ✅

**File:** `scripts/cleanup_stale_signals.py`

Created script to:
- Find all signal_scores with no entity_mentions
- Show details of what will be deleted
- Support dry-run mode (default)
- Delete stale signals when run with `--execute`

**Usage:**
```bash
# Dry run (see what would be deleted)
poetry run python scripts/cleanup_stale_signals.py --dry-run

# Actually delete stale signals
poetry run python scripts/cleanup_stale_signals.py --execute
```

**Results:**
- Found 21 stale signals
- Includes: Zoom, Airbnb, FedEx, Costco, Snap, Ford, Rivian, etc.

### Part 3: Prevention Functions ✅

**File:** `src/crypto_news_aggregator/db/operations/entity_mentions.py`

Added functions to prevent future orphans:

```python
async def delete_entity_mentions_for_article(article_id: str) -> int:
    """Delete all entity mentions for a specific article."""
    
async def delete_entity_mentions_for_articles(article_ids: List[str]) -> int:
    """Delete all entity mentions for multiple articles."""
```

**Usage:** Call these functions whenever articles are deleted:
```python
# When deleting a single article
await delete_entity_mentions_for_article(article_id)

# When deleting multiple articles
await delete_entity_mentions_for_articles(article_ids)
```

## Data Integrity

### Current State
- Entity mentions: 10,056
- Signal scores: 498 (21 are stale)
- Articles: 2,486

### After Cleanup
- Entity mentions: 10,056 (unchanged)
- Signal scores: 477 (21 stale removed)
- Articles: 2,486 (unchanged)

## Testing

### 1. Verify Stale Signals Found
```bash
poetry run python scripts/cleanup_stale_signals.py --dry-run
```
Expected: Shows 21 stale signals including Zoom

### 2. Test Signals Endpoint (Before Cleanup)
```bash
curl "http://localhost:8000/api/v1/signals/trending?limit=50"
```
Expected: May include entities with no articles (like Zoom)

### 3. Run Cleanup
```bash
poetry run python scripts/cleanup_stale_signals.py --execute
```
Expected: Deletes 21 stale signals

### 4. Test Signals Endpoint (After Cleanup)
```bash
curl "http://localhost:8000/api/v1/signals/trending?limit=50"
```
Expected: All entities have articles (Zoom no longer appears)

### 5. Verify Query Filter Works
The `get_trending_entities()` filter will prevent any new stale signals from appearing even if they exist in the database.

## Deployment Steps

1. **Commit and push changes:**
   ```bash
   git checkout fix/benzinga-blacklist-enforcement
   git add src/crypto_news_aggregator/db/operations/signal_scores.py
   git add src/crypto_news_aggregator/db/operations/entity_mentions.py
   git add scripts/cleanup_stale_signals.py
   git commit -m "fix: filter stale signals and add cleanup for orphaned entity data"
   git push
   ```

2. **Merge to main** (after review)

3. **Deploy to Railway**

4. **Run cleanup script on production:**
   ```bash
   # SSH into Railway or run via Railway CLI
   python scripts/cleanup_stale_signals.py --execute
   ```

5. **Verify Signals endpoint:**
   - Check that Zoom no longer appears
   - Verify all entities have articles

## Prevention Best Practices

### When Deleting Articles

Always clean up related data:

```python
from src.crypto_news_aggregator.db.operations.entity_mentions import (
    delete_entity_mentions_for_article
)

# Delete article
await articles.delete_one({"_id": article_id})

# Clean up entity mentions
await delete_entity_mentions_for_article(str(article_id))
```

### When Deleting Multiple Articles

```python
from src.crypto_news_aggregator.db.operations.entity_mentions import (
    delete_entity_mentions_for_articles
)

# Delete articles
result = await articles.delete_many({"source": "benzinga"})

# Clean up entity mentions
article_ids = [str(aid) for aid in article_ids_list]
await delete_entity_mentions_for_articles(article_ids)
```

### Periodic Cleanup

Consider adding a scheduled task to clean up stale signals:

```python
# In worker.py or similar
async def cleanup_stale_signals_task():
    """Periodically clean up stale signal scores."""
    while True:
        try:
            # Run cleanup logic
            await asyncio.sleep(86400)  # Once per day
        except Exception as exc:
            logger.error(f"Stale signal cleanup failed: {exc}")
```

## Files Changed

- ✅ `src/crypto_news_aggregator/db/operations/signal_scores.py` - Filter stale signals
- ✅ `src/crypto_news_aggregator/db/operations/entity_mentions.py` - Add cleanup functions
- ✅ `scripts/cleanup_stale_signals.py` - Cleanup script
- ✅ `scripts/cleanup_orphaned_entity_data.py` - Comprehensive cleanup (optional)
- ✅ `ORPHANED_ENTITY_DATA_FIX.md` - This document

## Success Metrics

✅ Root cause identified (stale signal_scores)  
✅ Query filter implemented to exclude stale signals  
✅ Cleanup script created and tested (dry-run)  
✅ Prevention functions added  
✅ 21 stale signals identified  
🔄 Awaiting deployment and cleanup execution  

## Next Steps

1. Review and merge PR
2. Deploy to Railway
3. Run cleanup script on production
4. Verify Signals endpoint no longer shows orphaned entities
5. Document prevention best practices for team
