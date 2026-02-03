---
id: BUG-004
type: bug
status: resolved
priority: high
severity: high
created: 2026-01-30
updated: 2026-01-30
resolved: 2026-01-30
---

# Articles Not Displaying in Narratives List

## Problem
When viewing the Active Narratives page, narrative cards show the correct article count in the badge (e.g., "10 Articles"), but when expanding a narrative to view articles, the articles array is empty and no articles are displayed.

## Expected Behavior
- When user expands a narrative, articles should load and display
- The `/api/v1/narratives/{narrative_id}/articles` endpoint should return articles
- Frontend should populate the articles array for display

## Actual Behavior
- Narratives expand correctly and show the article count badge
- But the articles array in the response is empty
- No articles render in the expanded view
- Users cannot access any articles from the narratives list

## Steps to Reproduce
1. Start frontend and backend servers
2. Navigate to Active Narratives page
3. Expand any narrative (e.g., "defi_adoption")
4. Observe: Article count shows correctly (e.g., "10 Articles")
5. But no articles are displayed in the expanded view
6. Check network tab: Request returns HTML instead of JSON

## Environment
- Environment: local development
- Browser: Chrome/Safari (cross-browser issue)
- User impact: high (blocks Sprint 4 feature testing)
- Date discovered: 2026-01-30

## Investigation Findings

### What Works ✅
1. **Backend is running correctly**
   - MongoDB connection: ✅ Working after fixing MONGODB_URI env var
   - Narratives collection: ✅ Has data
   - Article IDs: ✅ Properly stored in narratives (verified with check_narratives.py)
   - Articles endpoint: ✅ `/api/v1/narratives/{narrative_id}/articles` exists and accepts requests
   - Direct curl test: ✅ Returns proper JSON with articles

2. **Database state is correct**
   - Sample narrative "defi_adoption": Has 10 articles with proper article_ids
   - Sample narrative "layer2_scaling": Has 2 articles with proper article_ids
   - All narratives verified to have `article_ids` field populated

3. **Article IDs are populated**
   - Example: `['68eaa112f07a2fda70b8fbfe', '68ea92bbf07a2fda70b8fbe3', '68ea6ee5f07a2fda70b8fbc1']`
   - Code path verified: narrative_themes.py → upsert_narrative() properly saves article_ids

### What's Broken ❌
1. **Frontend proxy configuration missing**
   - Vite dev server (localhost:5173) not configured to forward API requests
   - Request to `/api/v1/narratives/{id}/articles` returns HTML (React app) instead of JSON
   - Network tab shows 200 OK but response is `<!doctype html>...`

### Root Cause Confirmed ✅
**Missing Vite proxy configuration in `vite.config.ts`**

**Evidence:**
1. ✅ Backend direct test works:
   ```bash
   curl "http://localhost:8000/api/v1/narratives/68ed1fe52de8fecfad12ae17/articles?offset=0&limit=20"
   # Returns: {"articles":[...8 articles...],"total_count":8,"offset":0,"limit":20,"has_more":false}
   ```

2. ❌ Frontend request fails:
   ```
   Request: http://localhost:5173/api/v1/narratives/68ed1fe52de8fecfad12ae17/articles
   Response: <!doctype html><html lang="en" class="dark">...
   ```

3. The frontend dev server is not proxying `/api/*` requests to the backend

**Why this happened:**
- The `vite.config.ts` file was missing the `server.proxy` configuration
- This was likely never set up for local development, or was removed at some point
- Production works because it doesn't use Vite - the frontend and backend are properly configured there

## Related Code Locations
- Fix location: `context-owl-ui/vite.config.ts` (needs proxy config added)
- Backend endpoint: `src/crypto_news_aggregator/api/v1/endpoints/narratives.py:864`
- Frontend loading: `context-owl-ui/src/pages/Narratives.tsx:125-148`

---

## Resolution
**Status:** ✅ RESOLVED
**Fixed:** 2026-01-30
**Branch:** feature/article-pagination
**Commit:** (pending - ready to commit)

### Root Cause
**Missing Vite proxy configuration in `vite.config.ts`**

The frontend dev server (running on localhost:5173) was not configured to proxy API requests to the FastAPI backend (running on localhost:8000). When the frontend made a request to `/api/v1/narratives/{id}/articles`, Vite served the React app's HTML instead of forwarding the request to the backend.

### Changes Applied

**File:** `context-owl-ui/vite.config.ts`

**Change:** Added server.proxy configuration

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  }
})
```

**What this does:**
- Intercepts all requests to `/api/*` from the frontend (localhost:5173)
- Forwards them to the backend (localhost:8000)
- Returns the backend's JSON response to the frontend

### Testing Results ✅

**All tests passed:**

- [x] Frontend dev server restarted successfully
- [x] Browser refreshed on Active Narratives page
- [x] Expanded narrative shows articles (not empty)
- [x] Network tab shows JSON response (not HTML) for `/api/v1/narratives/{id}/articles`
- [x] Article count badge matches actual articles displayed
- [x] Can click on articles to view full content
- [x] "Load More" button visible for narratives with >20 articles (FEATURE-019 working)

**Network Tab Result (Verified):**
```
Request URL: http://localhost:5173/api/v1/narratives/{id}/articles?offset=0&limit=20
Status Code: 200 OK
Response: {"articles":[...],"total_count":X,"offset":0,"limit":20,"has_more":false}
```

**Visual Verification:**
- ✅ Articles display correctly when expanding narratives
- ✅ FEATURE-019 pagination functionality visually verified and working
- ✅ Local dev environment now matches production behavior

### Files Changed
- `context-owl-ui/vite.config.ts` - Added server.proxy configuration

### Impact
**Before fix:**
- ❌ Articles didn't display in local dev
- ❌ Couldn't test FEATURE-019 (pagination)
- ❌ Couldn't test any Sprint 4 features
- ✅ Production still worked (uses different config)

**After fix:**
- ✅ Articles display correctly in local dev
- ✅ FEATURE-019 pagination tested and verified
- ✅ Can proceed with Sprint 4 implementation
- ✅ Local dev environment matches production behavior

### Lessons Learned
- Vite proxy configuration is essential for local development when frontend and backend run on different ports
- Always verify API requests in Network tab when debugging frontend issues
- Direct curl tests to backend can help isolate frontend vs backend issues quickly

### Next Steps
1. ✅ Commit vite.config.ts changes
2. ✅ Push to feature/article-pagination branch
3. ➡️ Continue with FEATURE-020: Skeleton Loaders