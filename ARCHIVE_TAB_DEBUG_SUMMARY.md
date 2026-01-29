# Archive Tab Debug Summary

## Problem Statement
The Archive tab shows "2 articles" in the UI but displays no narrative cards.

## Investigation Created

### Debug Scripts Created

1. **`scripts/test_archive_api.py`**
   - Tests the `/api/v1/narratives/archived` endpoint
   - Shows how many narratives are returned
   - Displays lifecycle_state, article_count, and full response structure
   - Run with: `poetry run python scripts/test_archive_api.py`

2. **`scripts/check_dormant_narratives.py`**
   - Queries MongoDB directly for dormant narratives
   - Shows lifecycle_state distribution
   - Checks for narratives with 2 articles
   - Identifies old schema narratives without lifecycle_state field
   - Run with: `poetry run python scripts/check_dormant_narratives.py`

3. **`scripts/run_archive_debug.sh`**
   - Runs both scripts in sequence
   - Run with: `./scripts/run_archive_debug.sh`

4. **`scripts/debug_archive_tab.md`**
   - Comprehensive debugging guide
   - Explains data flow from database → API → frontend
   - Lists possible issues and solutions

## Data Flow Analysis

```
Database (MongoDB)
  ↓ Query: {lifecycle_state: "dormant", last_updated: {$gte: cutoff}}
  ↓
get_archived_narratives() in db/operations/narratives.py
  ↓ Returns: List[Dict[str, Any]]
  ↓
GET /api/v1/narratives/archived in api/v1/endpoints/narratives.py
  ↓ Converts to: List[NarrativeResponse]
  ↓
Frontend: narrativesAPI.getArchivedNarratives(50, 30)
  ↓ Receives: NarrativesResponse (array of narratives)
  ↓
Narratives.tsx: viewMode === 'archive'
  ↓ Renders: narrative cards in <div className="space-y-6">
```

## Key Code Locations

### Frontend Query (context-owl-ui/src/pages/Narratives.tsx)
```typescript
// Line 63: API call when viewMode === 'archive'
const result = viewMode === 'archive' 
  ? await narrativesAPI.getArchivedNarratives(50, 30) 
  : await narrativesAPI.getNarratives();

// Line 64-68: Debug logging (check browser console)
console.log(`[DEBUG] ${viewMode} API returned:`, result.length, 'narratives');
if (viewMode === 'archive') {
  console.log('[DEBUG] Archive narratives lifecycle_state values:', result.map(n => n.lifecycle_state));
  console.log('[DEBUG] Archive narratives data:', result);
}

// Line 645-646: Rendering
<div className="space-y-6">
  {narratives.map((narrative, index) => {
    // ... render cards
  })}
</div>
```

### API Endpoint (src/crypto_news_aggregator/api/v1/endpoints/narratives.py)
```python
# Line 308-457: /archived endpoint
@router.get("/archived", response_model=List[NarrativeResponse])
async def get_archived_narratives_endpoint(
    limit: int = Query(50, ...),
    days: int = Query(30, ...)
):
    narratives = await get_archived_narratives(limit=limit, days=days)
    # ... converts to response format
```

### Database Query (src/crypto_news_aggregator/db/operations/narratives.py)
```python
# Line 334-395: Database query
async def get_archived_narratives(limit: int = 50, days: int = 30):
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    query = {
        "lifecycle_state": "dormant",
        "last_updated": {"$gte": cutoff_date}
    }
    
    cursor = collection.find(query).sort("last_updated", -1).limit(limit)
```

## Possible Root Causes

### 1. No Dormant Narratives in Database
**Likelihood:** High  
**Check:** Run `scripts/check_dormant_narratives.py`  
**Symptoms:**
- Database query returns 0 results
- API returns empty array
- Frontend shows no cards

**Why this happens:**
- Lifecycle system may not be marking narratives as dormant
- Narratives might be stuck in other states (emerging, rising, etc.)
- Old schema narratives don't have `lifecycle_state` field

**Solution:**
```bash
# Check lifecycle state distribution
poetry run python scripts/check_dormant_narratives.py

# If narratives exist but aren't marked dormant, run migration
poetry run python scripts/backfill_lifecycle_states.py
```

### 2. Dormant Narratives Outside 30-Day Window
**Likelihood:** Medium  
**Check:** Look for "Dormant narratives updated in last 30 days: 0" in script output  
**Symptoms:**
- Database has dormant narratives
- But none updated in last 30 days
- API returns empty array

**Solution:**
- Increase the `days` parameter in the frontend
- Or check why narratives aren't being updated

### 3. Old Schema Narratives
**Likelihood:** Medium  
**Check:** Look for "Old schema narratives: X" in script output  
**Symptoms:**
- Narratives exist with article_count = 2
- But they don't have `lifecycle_state` field
- Query filters them out

**Solution:**
The API endpoint has fallback logic for old schema (lines 359-379 in narratives.py):
```python
# Handle old schema: extract entities from actors dict
entities = narrative.get("entities", [])
if not entities:
    actors = narrative.get("actors", {})
    if actors:
        entities = sorted(actors.keys(), key=lambda k: actors[k], reverse=True)[:10]
```

But the **database query** only looks for `lifecycle_state='dormant'`, so old schema narratives are excluded.

### 4. Frontend Filtering Issue
**Likelihood:** Low  
**Check:** Browser console logs  
**Symptoms:**
- API returns narratives (check Network tab)
- But frontend doesn't render them
- Console shows narratives received but cards not rendered

**Debug:**
1. Open browser DevTools
2. Go to Archive tab
3. Check Console for `[DEBUG]` messages
4. Check Network tab for `/api/v1/narratives/archived` response

### 5. "2 articles" Count is Misleading
**Likelihood:** Medium  
**Check:** Look at what's actually being displayed  

The "2 articles" might be coming from:
- A single narrative card showing `article_count: 2`
- The resurrection summary card showing article counts
- A different UI element entirely

## How to Debug

### Step 1: Run the Debug Scripts
```bash
cd /Users/mc/dev-projects/crypto-news-aggregator
./scripts/run_archive_debug.sh
```

### Step 2: Check Browser Console
1. Open the frontend
2. Click on Archive tab
3. Open DevTools Console
4. Look for these messages:
   ```
   [DEBUG] archive API returned: X narratives
   [DEBUG] Archive narratives lifecycle_state values: [...]
   [DEBUG] Archive narratives data: [...]
   [DEBUG] Narratives after data assignment: X viewMode: archive
   ```

### Step 3: Check Network Tab
1. Open DevTools Network tab
2. Click Archive tab
3. Find the request to `/api/v1/narratives/archived`
4. Check the response body

### Step 4: Analyze Results

**If API returns 0 narratives:**
- Problem is in database or query
- Check lifecycle state distribution
- May need to run migration

**If API returns narratives but frontend shows none:**
- Problem is in frontend rendering
- Check console logs for errors
- Check if narratives array is being filtered

**If narratives exist but aren't marked dormant:**
- Run lifecycle state backfill
- Check lifecycle transition logic

## Expected Output

### When Working Correctly

**Database Query:**
```
Total dormant narratives: 5
Dormant narratives updated in last 30 days: 3
```

**API Response:**
```json
[
  {
    "_id": "...",
    "title": "Some Narrative",
    "lifecycle_state": "dormant",
    "article_count": 2,
    "entities": ["Entity1", "Entity2"],
    ...
  }
]
```

**Frontend Console:**
```
[DEBUG] archive API returned: 3 narratives
[DEBUG] Archive narratives lifecycle_state values: ["dormant", "dormant", "dormant"]
[DEBUG] Narratives after data assignment: 3 viewMode: archive
```

**UI:**
- 3 narrative cards displayed
- Each with purple border and Archive icon
- Article count shown on each card

## Next Steps

1. **Run the debug scripts** to identify where the data is lost
2. **Check browser console** to see what the frontend receives
3. **Based on findings**, apply the appropriate fix:
   - If no dormant narratives → Run lifecycle migration
   - If narratives outside window → Adjust date range
   - If old schema → Update query to include them
   - If frontend issue → Fix rendering logic

## Files Modified

- ✅ `scripts/test_archive_api.py` - API endpoint test
- ✅ `scripts/check_dormant_narratives.py` - MongoDB query test
- ✅ `scripts/run_archive_debug.sh` - Run all tests
- ✅ `scripts/debug_archive_tab.md` - Detailed debugging guide
- ✅ `ARCHIVE_TAB_DEBUG_SUMMARY.md` - This file

## Logging Already in Place

The code already has extensive debug logging:

**Database Query (narratives.py:362-393):**
```python
logger.info(f"[DEBUG] Total narratives in database: {total_count}")
logger.info(f"[DEBUG] Narratives with lifecycle_state field: {with_lifecycle_state}")
logger.info(f"[DEBUG] Lifecycle state distribution: {lifecycle_distribution}")
logger.info(f"[DEBUG] Query for archived narratives: {query}")
logger.info(f"[DEBUG] Found {len(narratives)} archived narratives")
```

**API Endpoint (narratives.py:330-332):**
```python
logger.info(f"[DEBUG] get_archived_narratives returned {len(narratives)} narratives")
if narratives:
    logger.info(f"[DEBUG] First narrative: {narratives[0].get('theme', 'N/A')}, lifecycle_state: {narratives[0].get('lifecycle_state', 'N/A')}")
```

**Frontend (Narratives.tsx:64-68):**
```typescript
console.log(`[DEBUG] ${viewMode} API returned:`, result.length, 'narratives');
if (viewMode === 'archive') {
  console.log('[DEBUG] Archive narratives lifecycle_state values:', result.map(n => n.lifecycle_state));
  console.log('[DEBUG] Archive narratives data:', result);
}
```

Check your **Railway logs** for the backend debug messages and **browser console** for frontend messages.
