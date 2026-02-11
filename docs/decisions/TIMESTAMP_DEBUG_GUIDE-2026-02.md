# Reversed Timestamp Debug Guide

## Problem
Narratives are being created with `first_seen > last_updated` despite backend validation in `upsert_narrative()`. This means the corruption happens **before** data reaches `upsert_narrative()`, in the narrative service's timestamp calculations.

## Solution: Debug Logging Added
Detailed logging has been added to `src/crypto_news_aggregator/services/narrative_service.py` immediately before each `upsert_narrative()` call to identify which code path is setting timestamps incorrectly.

## Two Code Paths to Monitor

### 1. Merge Path (Line 750) - Existing Narratives
**Location**: When matching an existing narrative and merging new articles

**Timestamp Logic**:
- `first_seen` = taken from existing narrative (line 705)
- `last_updated` = `datetime.now(timezone.utc)` (line 709)

**Expected Behavior**: `first_seen` should be earlier than `last_updated`

**Debug Logs to Look For**:
```
[MERGE NARRATIVE DEBUG] ========== MERGE UPSERT START ==========
[MERGE NARRATIVE DEBUG] Theme: <theme>
[MERGE NARRATIVE DEBUG] Article dates (sorted):
[MERGE NARRATIVE DEBUG]   [1] <earliest_date>
[MERGE NARRATIVE DEBUG]   [2] <date>
[MERGE NARRATIVE DEBUG] Earliest article: <earliest>
[MERGE NARRATIVE DEBUG] Latest article: <latest>
[MERGE NARRATIVE DEBUG] Existing narrative first_seen: <existing_first_seen>
[MERGE NARRATIVE DEBUG] Calculated first_seen (from existing or now): <first_seen>
[MERGE NARRATIVE DEBUG] Calculated last_updated (now): <last_updated>
[MERGE NARRATIVE DEBUG] Is first_seen > last_updated? <TRUE/FALSE>
[MERGE NARRATIVE DEBUG] Timestamp sources: first_seen from existing narrative, last_updated from now()
```

**Potential Issue**: If existing narrative's `first_seen` is corrupted (set to a future date), it will propagate here.

### 2. Create Path (Line 879) - New Narratives
**Location**: When creating a brand new narrative (no existing match)

**Timestamp Logic** (CURRENT - BUGGY):
- `first_seen` = `datetime.now(timezone.utc)` (line 844)
- `last_updated` = `datetime.now(timezone.utc)` (line 845)

**Expected Behavior**: Should use article dates, not `now()`
- `first_seen` should = `min(article_dates)` (earliest article)
- `last_updated` should = `max(article_dates)` (latest article)

**Debug Logs to Look For**:
```
[CREATE NARRATIVE DEBUG] ========== CREATE UPSERT START ==========
[CREATE NARRATIVE DEBUG] Theme: <theme>
[CREATE NARRATIVE DEBUG] Title: <title>
[CREATE NARRATIVE DEBUG] Article dates collected: <count>
[CREATE NARRATIVE DEBUG] Article dates (sorted):
[CREATE NARRATIVE DEBUG]   [1] <earliest_date>
[CREATE NARRATIVE DEBUG]   [2] <date>
[CREATE NARRATIVE DEBUG] Earliest article: <earliest>
[CREATE NARRATIVE DEBUG] Latest article: <latest>
[CREATE NARRATIVE DEBUG] Calculated first_seen (now): <first_seen>
[CREATE NARRATIVE DEBUG] Calculated last_updated (now): <last_updated>
[CREATE NARRATIVE DEBUG] Is first_seen > last_seen? <TRUE/FALSE>
[CREATE NARRATIVE DEBUG] Timestamp sources: BOTH from now() - THIS IS THE BUG!
[CREATE NARRATIVE DEBUG] Should use: first_seen = min(article_dates), last_updated = max(article_dates)
```

## How to Use This Debug Info

1. **Deploy** the code with these debug logs
2. **Monitor** Railway logs for `[MERGE NARRATIVE DEBUG]` and `[CREATE NARRATIVE DEBUG]` prefixes
3. **Look for**:
   - Which path creates reversed timestamps?
   - Are article dates being collected correctly?
   - Is `first_seen` being set from wrong source?
   - Is `last_updated` being set from wrong source?

## Expected Findings

### Most Likely Culprit: Create Path
The create path (line 844-845) is setting **both** `first_seen` and `last_updated` to `now()`, which means:
- If articles were published in the past, `first_seen` will be set to current time (wrong!)
- This creates reversed timestamps if any validation happens later

### Fix Strategy (Once Confirmed)
For new narratives, change:
```python
# CURRENT (BUGGY)
first_seen = datetime.now(timezone.utc)
last_updated = datetime.now(timezone.utc)

# SHOULD BE
first_seen = min(article_dates) if article_dates else datetime.now(timezone.utc)
last_updated = max(article_dates) if article_dates else datetime.now(timezone.utc)
```

## Validation Commands

After deploying and collecting logs:

```bash
# Check Railway logs for debug output
# Look for patterns like:
# - "Is first_seen > last_updated? True"
# - "Timestamp sources: BOTH from now()"

# Check MongoDB for remaining reversed timestamps
db.narratives.aggregate([
  {$addFields: {isReversed: {$gt: ["$first_seen", "$last_updated"]}}},
  {$match: {isReversed: true}},
  {$count: "count"}
])
```

## Files Modified
- `src/crypto_news_aggregator/services/narrative_service.py` - Added debug logging before upsert_narrative calls
