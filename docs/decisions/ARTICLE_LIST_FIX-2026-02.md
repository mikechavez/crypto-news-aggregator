# Article List Fix for Expanded Cards

## Problem
Article lists weren't showing when narrative cards were expanded in the Cards and Pulse tabs. The Archive tab worked fine, but Cards and Pulse tabs showed no articles.

## Root Cause
The backend API endpoint `/api/v1/narratives/active` (used by Cards and Pulse tabs) intentionally returns **empty articles arrays** to prevent N+1 query problems and improve performance. This was done to reduce initial page load time from 2 minutes to <1 second.

Only the `/api/v1/narratives/archived` endpoint fetches articles upfront.

## Solution
Implemented **on-demand article fetching** when a card is expanded:

### Backend Changes
**File:** `src/crypto_news_aggregator/api/v1/endpoints/narratives.py`

1. **Added `_id` field to all narrative responses:**
   - Modified `NarrativeResponse` Pydantic model to include optional `_id` field
   - Updated `/active`, `/archived`, and `/resurrections` endpoints to include `_id` in response
   - The `_id` is the MongoDB ObjectId converted to string format

2. **Added new endpoint `GET /api/v1/narratives/{narrative_id}`:**
   - Accepts a MongoDB ObjectId as a string parameter
   - Fetches the full narrative document from MongoDB
   - Retrieves up to 20 articles using the existing `get_articles_for_narrative()` helper
   - Returns complete narrative data with articles included

### Frontend Changes

#### 1. API Client Update
**File:** `context-owl-ui/src/api/narratives.ts`
- Updated `getNarrativeById()` to accept `string | number` for the ID parameter
- This allows passing MongoDB ObjectId strings

#### 2. Narratives Component Update
**File:** `context-owl-ui/src/pages/Narratives.tsx`

Added state management:
```typescript
const [narrativeArticles, setNarrativeArticles] = useState<Map<string, any[]>>(new Map());
const [loadingArticles, setLoadingArticles] = useState<Set<string>>(new Set());
```

Modified `toggleExpanded()` function to:
1. Check if articles are already cached in `narrativeArticles` Map
2. If not cached and not in archive mode, fetch articles via API
3. Show loading state while fetching
4. Cache fetched articles by narrative ID to avoid refetching

Updated article rendering section to:
- Show loading spinner while fetching articles
- Display cached or pre-loaded articles
- Show "No articles available" if fetch returns empty
- Use `narrative.article_count` as fallback for article count display

## Behavior

### Cards Tab
- Initially shows article count badge (e.g., "15 articles")
- When card is clicked/expanded:
  - Shows "Loading articles..." spinner
  - Fetches articles from API
  - Displays article list with titles, sources, and timestamps
  - Articles are clickable links that open in new tab
- Subsequent expansions use cached data (no refetch)

### Pulse Tab
- Same behavior as Cards tab
- Articles are fetched on-demand when timeline cards are expanded

### Archive Tab
- No changes needed
- Articles are already included in the API response
- Displays immediately when expanded

## Performance Benefits
- Initial page load remains fast (<1 second)
- Articles only fetched when user explicitly requests them
- Caching prevents redundant API calls
- No N+1 query problem

## Testing Checklist
- [ ] Cards tab: Click a narrative card and verify articles load
- [ ] Pulse tab: Click a narrative card and verify articles load
- [ ] Archive tab: Verify articles still display correctly
- [ ] Verify loading spinner appears during fetch
- [ ] Verify articles are clickable and open in new tab
- [ ] Verify re-expanding same card uses cached data (no loading spinner)
- [ ] Check browser console for errors
- [ ] Verify article count badge shows correct number

## Files Modified
1. `src/crypto_news_aggregator/api/v1/endpoints/narratives.py` - Added GET /{narrative_id} endpoint
2. `context-owl-ui/src/api/narratives.ts` - Updated type signature
3. `context-owl-ui/src/pages/Narratives.tsx` - Implemented on-demand fetching with caching
