# Archive Tab Issue - Findings & Solution

## 🔍 Issue Identified

**Problem:** Archive tab shows "2 articles" but no narrative cards are displayed.

**Root Cause:** The dormant narrative exists in the database but has **old schema fields** that aren't being properly transformed by the API.

## 📊 Database Analysis Results

### What We Found
```
✓ Database has 1 dormant narrative
✓ It has exactly 2 articles
✓ It's within the 30-day window (updated today)
✓ It SHOULD appear in the archive tab
```

### The Problem
The narrative has **old schema fields**:
- ❌ No `title` field (has `nucleus_entity` instead)
- ❌ No `summary` field (has `narrative_summary` instead)  
- ❌ No `entities` array (has `actors` dict instead)

### Full Narrative Data
```json
{
  "_id": "68f176c0adf726e41839e827",
  "nucleus_entity": "BTC",
  "actors": {
    "BTC": 4,
    "WLFI": 4,
    "HYPE": 4,
    ...
  },
  "narrative_summary": "This article covers a range of crypto-related events...",
  "article_count": 2,
  "lifecycle_state": "dormant",
  "last_updated": "2025-10-18 05:39:38.636000"
}
```

**Missing fields:**
- `title` (should fallback to `nucleus_entity` = "BTC")
- `summary` (should fallback to `narrative_summary`)
- `entities` (should extract from `actors` dict)

## 🔧 The API Fallback Logic

The API endpoint (`src/crypto_news_aggregator/api/v1/endpoints/narratives.py`) has fallback logic for old schema narratives:

### Lines 359-379: Old Schema Handling
```python
# Handle old schema: extract entities from actors dict or use nucleus_entity
entities = narrative.get("entities", [])
if not entities:
    # Old schema: try actors dict keys or nucleus_entity
    actors = narrative.get("actors", {})
    if actors:
        # Get top 10 actors by count
        entities = sorted(actors.keys(), key=lambda k: actors[k], reverse=True)[:10]
    elif narrative.get("nucleus_entity"):
        entities = [narrative.get("nucleus_entity")]

# Handle old schema: use nucleus_entity or first action as title
title = narrative.get("title") or narrative.get("theme")
if not title:
    # Old schema fallback: use nucleus_entity or first action
    if narrative.get("nucleus_entity"):
        title = f"{narrative.get('nucleus_entity')} Activity"
    elif narrative.get("actions") and len(narrative.get("actions", [])) > 0:
        title = narrative.get("actions")[0][:100]
    else:
        title = "Untitled Narrative"
```

### Line 357: Summary Fallback
```python
summary = narrative.get("summary") or narrative.get("story") or narrative.get("narrative_summary", "")
```

**This logic exists in the `/archived` endpoint** (lines 356-379) but we need to verify it's working in production.

## ❓ Why Can't We Test Production?

The Railway deployment at `https://crypto-news-aggregator-production.up.railway.app` returns:
```json
{"status":"error","code":404,"message":"Application not found"}
```

This means:
1. The deployment might not be active
2. The URL might be incorrect
3. The app might not be deployed to Railway yet

## ✅ Next Steps

### Option 1: Test with Local API (Recommended)
1. Start the local API server:
   ```bash
   cd /Users/mc/dev-projects/crypto-news-aggregator
   poetry run uvicorn crypto_news_aggregator.main:app --reload --port 8000
   ```

2. Run the test script:
   ```bash
   export API_URL="http://localhost:8000"
   poetry run python scripts/test_production_archive_api.py
   ```

3. This will show if the API fallback logic is working correctly

### Option 2: Check Railway Deployment
1. Open Railway dashboard
2. Verify the deployment is active
3. Get the correct URL from the deployment
4. Update the script with the correct URL:
   ```bash
   export RAILWAY_API_URL="https://your-actual-url.railway.app"
   poetry run python scripts/test_production_archive_api.py
   ```

### Option 3: Migrate the Old Schema Narrative
Create a migration script to update the narrative to the new schema:

```python
# scripts/migrate_old_schema_narrative.py
async def migrate_narrative():
    db = await mongo_manager.get_async_database()
    collection = db.narratives
    
    # Find the old schema narrative
    narrative = await collection.find_one({"_id": ObjectId("68f176c0adf726e41839e827")})
    
    # Transform to new schema
    update = {
        "$set": {
            "title": f"{narrative['nucleus_entity']} Activity",
            "summary": narrative.get("narrative_summary", ""),
            "entities": sorted(narrative["actors"].keys(), key=lambda k: narrative["actors"][k], reverse=True)[:10]
        }
    }
    
    await collection.update_one({"_id": narrative["_id"]}, update)
```

## 🎯 Expected Behavior After Fix

Once the API fallback logic is working OR the narrative is migrated:

**API Response:**
```json
{
  "_id": "68f176c0adf726e41839e827",
  "title": "BTC Activity",
  "summary": "This article covers a range of crypto-related events...",
  "entities": ["BTC", "WLFI", "HYPE", "TRON", "Metaplanet"],
  "article_count": 2,
  "lifecycle_state": "dormant"
}
```

**Frontend Display:**
- ✅ Card renders with title "BTC Activity"
- ✅ Summary is displayed
- ✅ Entities shown as badges
- ✅ Purple border (archive styling)
- ✅ Article count shows "2 articles"

## 📝 Summary

| Component | Status | Details |
|-----------|--------|---------|
| Database | ✅ Working | 1 dormant narrative with 2 articles exists |
| Lifecycle State | ✅ Correct | Marked as "dormant" |
| Date Range | ✅ Within Window | Updated today (0 days ago) |
| Schema | ❌ Old Format | Missing `title`, `summary`, `entities` |
| API Fallback | ❓ Unknown | Can't test production, needs local test |
| Frontend | ⏳ Waiting | Will work once API returns proper data |

## 🚀 Recommended Action

**Run the local API test to verify the fallback logic:**

```bash
# Terminal 1: Start API
poetry run uvicorn crypto_news_aggregator.main:app --reload --port 8000

# Terminal 2: Test the endpoint
export API_URL="http://localhost:8000"
poetry run python scripts/test_production_archive_api.py
```

If the fallback logic works locally, the issue is with the Railway deployment.  
If it doesn't work locally, we need to fix the API fallback logic or migrate the narrative.
