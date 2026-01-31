# [BUG-005] FastAPI Route Order - Articles Endpoint Returns 404

**Status:** 🔴 **CRITICAL - BLOCKING PAGINATION**
**Priority:** P0 (Must fix immediately)
**Estimated Effort:** 10 minutes
**Sprint:** Sprint 4 (UX Enhancements)
**Created:** 2026-01-30 (Evening)

---

## Executive Summary

**Problem:** Frontend pagination works locally but returns 404 in production when calling `/api/v1/narratives/{id}/articles`

**Root Cause:** FastAPI route order bug - the generic `/{narrative_id}` route (line 739) is defined BEFORE the specific `/{narrative_id}/articles` route (line 870), causing FastAPI to match the wrong endpoint.

**Solution:** Move the `/{narrative_id}/articles` endpoint to BEFORE the `/{narrative_id}` endpoint. More specific routes must come first in FastAPI.

**Impact:** Without this fix, users cannot load more than 20 articles for any narrative.

---

## Error Details

### Console Error
```
GET https://context-owl-production.up.railway.app/api/v1/narratives/68f32d197082f49df56956c6/articles?offset=0&limit=20 404 (Not Found)
```

### What's Happening
1. Frontend calls: `/narratives/68f32d197082f49df56956c6/articles?offset=0&limit=20`
2. FastAPI sees `/{narrative_id}` route first (line 739)
3. FastAPI matches this route with `narrative_id = "68f32d197082f49df56956c6"`
4. Never reaches the `/{narrative_id}/articles` route (line 870)
5. Returns 404 because "articles" is not a valid narrative ID

---

## The Fix

### File to Edit
`backend/api/v1/endpoints/narratives.py`

### Current Route Order (WRONG)
```python
# Line 739 - Generic route defined FIRST (wrong order)
@router.get("/{narrative_id}", response_model=NarrativeResponse)
async def get_narrative_by_id_endpoint(narrative_id: str):
    # ... 130 lines of code ...

# Line 870 - Specific route defined SECOND (never reached)
@router.get("/{narrative_id}/articles")
async def get_narrative_articles_endpoint(
    narrative_id: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50)
):
    # ... 43 lines of code ...
```

### Correct Route Order (FIXED)
```python
# Specific route FIRST (gets matched first)
@router.get("/{narrative_id}/articles")
async def get_narrative_articles_endpoint(
    narrative_id: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50)
):
    # ... 43 lines of code ...

# Generic route SECOND (only matches if /articles not present)
@router.get("/{narrative_id}", response_model=NarrativeResponse)
async def get_narrative_by_id_endpoint(narrative_id: str):
    # ... 130 lines of code ...
```

---

## Implementation Steps

### Step 1: Locate the Project
```bash
# Find your backend directory
cd ~/path/to/context-owl/backend
# or wherever your backend code lives
```

### Step 2: Open the File
```bash
# Open backend/api/v1/endpoints/narratives.py
# Navigate to lines 739-912
```

### Step 3: Move the Code

**What to Move:** Lines 870-912 (the entire `get_narrative_articles_endpoint` function)

**Where to Move It:** Right BEFORE line 739 (before `get_narrative_by_id_endpoint`)

**Detailed Instructions:**

1. **Copy lines 870-912** (the `/articles` endpoint):
   ```python
   @router.get("/{narrative_id}/articles")
   async def get_narrative_articles_endpoint(
       narrative_id: str,
       offset: int = Query(0, ge=0, description="Number of articles to skip"),
       limit: int = Query(20, ge=1, le=50, description="Maximum number of articles to return (1-50)")
   ):
       """
       Get paginated articles for a specific narrative.
       
       ... [full docstring] ...
       """
       try:
           db = await mongo_manager.get_async_database()
           result = await get_articles_paginated(
               narrative_id=narrative_id,
               offset=offset,
               limit=limit,
               db=db
           )
           return result
       except HTTPException:
           raise
       except Exception as e:
           logger.exception(f"Error fetching paginated articles: {e}")
           raise HTTPException(status_code=500, detail="Failed to fetch articles")
   ```

2. **Delete lines 870-913** (remove from old location, including the blank lines)

3. **Paste at line 739** (BEFORE the `/{narrative_id}` endpoint)

4. **Add blank lines for readability** (2 blank lines between endpoints)

### Step 4: Verify the Order

After moving, your file should look like this around line 739:

```python
# ... previous code ...


@router.get("/{narrative_id}/articles")
async def get_narrative_articles_endpoint(
    narrative_id: str,
    offset: int = Query(0, ge=0, description="Number of articles to skip"),
    limit: int = Query(20, ge=1, le=50, description="Maximum number of articles to return (1-50)")
):
    """Get paginated articles for a specific narrative."""
    try:
        db = await mongo_manager.get_async_database()
        result = await get_articles_paginated(
            narrative_id=narrative_id,
            offset=offset,
            limit=limit,
            db=db
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error fetching paginated articles: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch articles")


@router.get("/{narrative_id}", response_model=NarrativeResponse)
async def get_narrative_by_id_endpoint(narrative_id: str):
    """Get a single narrative by ID with articles."""
    # ... rest of function ...
```

---

## Testing

### Local Testing

1. **Start Backend:**
   ```bash
   cd backend
   python -m uvicorn app.main:app --reload
   ```

2. **Test the Endpoint:**
   ```bash
   # Should return 200 OK with paginated articles
   curl "http://localhost:8000/api/v1/narratives/68f32d197082f49df56956c6/articles?offset=0&limit=20"
   ```

3. **Verify Frontend:**
   ```bash
   cd context-owl-ui
   npm run dev
   ```
   - Navigate to http://localhost:5173/narratives
   - Expand a narrative with 69+ articles
   - Should see "Showing 20 of 69 Articles"
   - Click "Load More" - should load next 20 articles

### Production Testing

After deploying to Railway:

1. **Check Endpoint Directly:**
   ```bash
   curl "https://context-owl-production.up.railway.app/api/v1/narratives/68f32d197082f49df56956c6/articles?offset=0&limit=20"
   ```
   - Should return 200 OK (not 404)

2. **Check Frontend:**
   - Navigate to production URL
   - Expand narrative
   - Verify pagination works

---

## Git Workflow

```bash
# In backend directory
cd backend

# Make sure you're on the right branch
git checkout feature/article-pagination

# Stage the change
git add api/v1/endpoints/narratives.py

# Commit with descriptive message
git commit -m "fix(api): correct route order for article pagination endpoint

FastAPI matches routes in the order they're defined. The generic
/{narrative_id} route was defined before the specific /{narrative_id}/articles
route, causing all /articles requests to match the generic route first.

This resulted in 404 errors because 'articles' was being treated as a
narrative_id instead of being routed to the pagination endpoint.

Solution: Moved /{narrative_id}/articles endpoint to be defined BEFORE
/{narrative_id} endpoint. More specific routes must come first in FastAPI.

Fixes BUG-005 - Article pagination 404 errors in production
Resolves issue preventing users from loading more than 20 articles"

# Push to origin
git push origin feature/article-pagination
```

---

## Deployment to Railway

### Option 1: Automatic Deployment (if configured)
Railway should auto-deploy when you push to the branch.

### Option 2: Manual Deployment
1. Go to Railway dashboard
2. Select your backend service
3. Click "Deploy" or trigger a new deployment
4. Wait for deployment to complete
5. Test the endpoint

---

## Why This Happens in FastAPI

**FastAPI Route Matching Rules:**
1. Routes are matched in the **order they are defined**
2. The **first matching route** is used
3. Path parameters (like `{narrative_id}`) match **anything**

**Example:**
```python
# ❌ WRONG ORDER
@router.get("/{narrative_id}")      # Matches: /123, /abc, /articles, /timeline
async def get_narrative(...):
    pass

@router.get("/{narrative_id}/articles")  # Never reached!
async def get_articles(...):
    pass

# ✅ CORRECT ORDER
@router.get("/{narrative_id}/articles")  # Matches: /123/articles
async def get_articles(...):
    pass

@router.get("/{narrative_id}")           # Matches: /123, /abc (but not /articles)
async def get_narrative(...):
    pass
```

When a request comes in for `/narratives/123/articles`:
- **Wrong order:** FastAPI sees `/{narrative_id}` first, matches it with `narrative_id="123"` and path suffix `/articles`, returns 404
- **Correct order:** FastAPI sees `/{narrative_id}/articles` first, matches it exactly, calls the right endpoint

---

## Verification Checklist

After deploying the fix:

- [ ] Local backend starts without errors
- [ ] Local endpoint returns 200: `curl "http://localhost:8000/api/v1/narratives/{id}/articles?offset=0&limit=20"`
- [ ] Local frontend pagination works
- [ ] Production endpoint returns 200: `curl "https://context-owl-production.up.railway.app/api/v1/narratives/{id}/articles?offset=0&limit=20"`
- [ ] Production frontend pagination works
- [ ] Badge shows "Showing 20 of 69 Articles"
- [ ] "Load More" button appears and works
- [ ] Can load all 69 articles successfully
- [ ] No console errors

---

## Related Tickets

- **FEATURE-019:** Article Pagination (blocked by this bug)
- **FEATURE-020:** Skeleton Loaders (blocked by this bug)
- **FEATURE-021:** Error Handling (ready after this fix)

---

## Success Metrics

After fix is deployed:
- ✅ 0% 404 error rate on `/articles` endpoint
- ✅ Users can load 20+ articles for narratives
- ✅ "Load More" button appears when appropriate
- ✅ No console errors in production
- ✅ Backend endpoint responding correctly

---

## Time Estimate

- **Code change:** 5 minutes (just moving code)
- **Testing locally:** 3 minutes
- **Commit & push:** 2 minutes
- **Deploy to Railway:** 2-5 minutes (automatic)
- **Test in production:** 2 minutes

**Total:** ~15 minutes

---

## Notes for Developer

### Why This Bug Went Undetected

The backend code was **100% correct** - the `get_articles_paginated()` function and the endpoint itself were perfectly implemented. The bug was purely a **route ordering issue** that only manifests when FastAPI processes the routes.

This is why:
1. The code review showed "everything looks good"
2. The frontend worked in isolation
3. The endpoint "existed" but returned 404

### Key Lesson

**Always define more specific routes before generic routes in FastAPI:**
- `/users/me` before `/users/{user_id}`
- `/items/recent` before `/items/{item_id}`
- `/{id}/articles` before `/{id}`

This is a common FastAPI gotcha that catches many developers!

---

**Status:** ✅ FIXED (2026-01-30)
**What Was Done:** Moved `/{narrative_id}/articles` endpoint to line 739 (before generic route)
**Current Location:** Line 739-781 (specific route), Line 784-912 (generic route)
**Next Steps:** Commit and deploy
**Ready for:** Testing and deployment to production