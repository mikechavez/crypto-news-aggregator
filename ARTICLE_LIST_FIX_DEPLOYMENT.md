# Article List Fix - Deployment Steps

## Issue Found
The narratives were missing the `_id` field in the API response, so the frontend couldn't fetch articles by ID.

## Changes Made

### Backend
1. Added `_id: Optional[str]` field to `NarrativeResponse` Pydantic model
2. Updated all three narrative endpoints to include `_id` in responses:
   - `/api/v1/narratives/active`
   - `/api/v1/narratives/archived`
   - `/api/v1/narratives/resurrections`
3. Added new endpoint: `GET /api/v1/narratives/{narrative_id}` to fetch single narrative with articles

### Frontend
1. Updated `narrativesAPI.getNarrativeById()` to accept `string | number` for MongoDB ObjectIds
2. Modified `Narratives.tsx` to fetch articles on-demand when cards are expanded
3. Added caching to prevent redundant API calls

## Deployment Steps

### 1. Restart Backend Server
The backend changes require a server restart to take effect:

```bash
# If running locally with uvicorn
pkill -f uvicorn
poetry run uvicorn crypto_news_aggregator.main:app --reload --host 0.0.0.0 --port 8000

# If deployed on Railway
# Push changes and Railway will auto-deploy
```

### 2. Clear Frontend Cache (Optional)
If using Redis cache, you may want to clear the narratives cache:

```bash
# Connect to Redis and flush narratives cache keys
redis-cli
> KEYS narratives:*
> DEL narratives:active:50
```

Or wait 10 minutes for cache to expire naturally.

### 3. Rebuild Frontend (if needed)
```bash
cd context-owl-ui
npm run build
```

## Testing After Deployment

1. **Open the app in browser**
2. **Navigate to Cards tab**
3. **Click on any narrative card to expand it**
4. **Expected behavior:**
   - Shows "Loading articles..." spinner briefly
   - Displays list of articles with titles, sources, and timestamps
   - Articles are clickable links
   - Re-expanding the same card shows articles instantly (cached)

5. **Check browser console:**
   - Should see no errors
   - Network tab should show successful API call to `/api/v1/narratives/{id}`

6. **Test Pulse tab:**
   - Same behavior as Cards tab

7. **Test Archive tab:**
   - Articles should display immediately (already included in response)

## Troubleshooting

### "No articles available" message
- Check browser console for API errors
- Verify narrative has `_id` field in response (check Network tab)
- Verify backend endpoint returns articles for that narrative ID

### Loading spinner never goes away
- Check for JavaScript errors in console
- Verify API endpoint is responding (check Network tab)
- Check backend logs for errors

### Articles not clickable
- Verify article objects have `url`, `title`, `source`, and `published_at` fields
- Check browser console for rendering errors

## Files Modified
1. `src/crypto_news_aggregator/api/v1/endpoints/narratives.py`
2. `context-owl-ui/src/api/narratives.ts`
3. `context-owl-ui/src/pages/Narratives.tsx`
