# Last Article At Implementation Summary

## Problem
All narratives showed "Updated just now" because the UI was displaying `last_updated`, which represents when the background worker last processed narratives (all at the same time), not when the last article was actually added to each narrative.

## Root Cause
- `last_updated` = timestamp when background worker runs (e.g., 2025-10-22 20:48:34)
- Most recent article = actual article publish time (e.g., 2025-10-21 16:37:16 - 28 hours ago)
- Result: All narratives showed "just now" instead of meaningful relative times like "28h ago"

## Solution
Added `last_article_at` field that tracks when the most recent article was published to each narrative.

## Changes Made

### 1. Backend API (`src/crypto_news_aggregator/api/v1/endpoints/narratives.py`)

#### Added $lookup aggregation stage (lines 201-222)
```python
# Lookup articles to get the most recent article timestamp
{'$lookup': {
    'from': 'articles',
    'let': {'article_ids': '$article_ids'},
    'pipeline': [
        {'$match': {
            '$expr': {
                '$in': [{'$toString': '$_id'}, '$$article_ids']
            }
        }},
        {'$project': {'published_at': 1}},
        {'$sort': {'published_at': -1}},
        {'$limit': 1}
    ],
    'as': 'recent_articles'
}},
# Add computed field for last_article_at
{'$addFields': {
    'last_article_at': {
        '$arrayElemAt': ['$recent_articles.published_at', 0]
    }
}}
```

#### Updated response model (line 117)
```python
last_article_at: Optional[str] = Field(default=None, description="ISO timestamp when the most recent article was published to this narrative")
```

#### Added response data handling (lines 293-300)
```python
# Handle last_article_at timestamp (most recent article published_at)
last_article_at = narrative.get("last_article_at")
last_article_at_str = None
if last_article_at:
    last_article_at_str = last_article_at.isoformat() if hasattr(last_article_at, 'isoformat') else str(last_article_at)
else:
    # Fallback to last_updated if no articles found
    last_article_at_str = last_updated_str
```

### 2. Frontend Types (`context-owl-ui/src/types/index.ts`)

#### Added field to Narrative interface (line 90)
```typescript
last_article_at?: string;   // ISO timestamp when most recent article was published to this narrative
```

### 3. Frontend UI (`context-owl-ui/src/pages/Narratives.tsx`)

#### Added full timestamp formatter (lines 90-107)
```typescript
/**
 * Format full timestamp for tooltip display
 */
const formatFullTimestamp = (dateValue: any): string => {
  try {
    const date = new Date(parseNarrativeDate(dateValue));
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    });
  } catch {
    return 'Unknown';
  }
};
```

#### Updated displayUpdated logic (lines 448-452)
```typescript
// IMPORTANT: Use last_article_at as primary timestamp for "Updated X ago"
// - last_article_at = when the most recent article was published (meaningful for users)
// - last_updated = when background worker last processed narrative (not meaningful - all show "just now")
// - updated_at = legacy field, fallback for backward compatibility
const displayUpdated = narrative.last_article_at || narrative.last_updated || narrative.updated_at;
```

#### Added hover tooltips (lines 583-590)
```typescript
<div className="flex items-center justify-between text-xs text-gray-600 dark:text-gray-400 mt-2">
  <span title={formatFullTimestamp(narrative.first_seen)}>
    Started {formatDate(narrative.first_seen)}
  </span>
  <span title={formatFullTimestamp(displayUpdated)}>
    Updated {formatShortRelativeTime(displayUpdated)}
  </span>
</div>
```
Note: No cursor change on hover - tooltips work via native `title` attribute without affecting the card's clickable behavior.

## How It Works

1. **Aggregation Pipeline**: When fetching narratives, the API now performs a `$lookup` to join with the articles collection
2. **Find Most Recent**: For each narrative, it finds the article with the most recent `published_at` timestamp
3. **Project Field**: The `last_article_at` field is added to the response with this timestamp
4. **UI Display**: The UI prioritizes `last_article_at` over `last_updated` for the "Updated X ago" display

## Benefits

- ✅ **Meaningful timestamps**: Shows when content was actually added, not when processing ran
- ✅ **Differentiated updates**: Each narrative shows its own unique update time
- ✅ **Backward compatible**: Falls back to `last_updated` if `last_article_at` is not available
- ✅ **No database migration**: Calculated on-the-fly via aggregation pipeline
- ✅ **Enhanced UX**: Hover tooltips show full date/time for both "Started" and "Updated" timestamps
- ✅ **Non-intrusive**: Native browser tooltips don't interfere with card clickability

## Example

**Before:**
- All narratives: "Updated just now" (all showing same time)

**After:**
- Narrative A: "Updated 2h ago" (last article published 2 hours ago)
  - Hover tooltip: "Oct 22, 2025, 12:30 PM"
- Narrative B: "Updated 1d ago" (last article published yesterday)
  - Hover tooltip: "Oct 21, 2025, 4:15 PM"
- Narrative C: "Updated 3w ago" (last article published 3 weeks ago)
  - Hover tooltip: "Oct 1, 2025, 9:45 AM"

## Testing

To verify the fix works:

1. Deploy the backend changes to Railway
2. Deploy the frontend changes
3. Check the Narratives page - each narrative should show different "Updated X ago" times
4. Verify the times match when the most recent article was published, not when the background worker ran
5. **Test hover tooltips**:
   - Hover over "Started [date]" text - should show full timestamp tooltip
   - Hover over "Updated X ago" text - should show full timestamp tooltip
   - Cursor should remain as pointer (for card clickability), not change to help icon

## Performance Considerations

The `$lookup` stage adds a join operation to the aggregation pipeline. However:
- It only fetches 1 article per narrative (using `$limit: 1`)
- It only projects the `published_at` field
- The articles collection should have an index on `_id` for efficient lookups
- This is more efficient than the previous approach of fetching all articles

## Related Files

- **Backend API**: `src/crypto_news_aggregator/api/v1/endpoints/narratives.py`
- **Frontend Types**: `context-owl-ui/src/types/index.ts`
- **Frontend UI**: `context-owl-ui/src/pages/Narratives.tsx`
- **Documentation**: `NARRATIVE_TIMELINE_FIELDS.md`
