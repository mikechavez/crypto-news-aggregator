# Archive Tab Debug Guide

## Problem
Archive tab shows "2 articles" but no narratives are displayed.

## Data Flow
1. **Frontend** (`Narratives.tsx`) → calls `narrativesAPI.getArchivedNarratives(50, 30)`
2. **API Client** (`narratives.ts`) → GET `/api/v1/narratives/archived?limit=50&days=30`
3. **API Endpoint** (`narratives.py`) → calls `get_archived_narratives(limit=50, days=30)`
4. **Database Query** (`narratives.py`) → queries MongoDB for `lifecycle_state='dormant'`

## Debug Steps

### Step 1: Test the API Endpoint
```bash
# Run the API test script
cd /Users/mc/dev-projects/crypto-news-aggregator
poetry run python scripts/test_archive_api.py
```

**What to check:**
- How many narratives are returned?
- What are their `lifecycle_state` values?
- What are their `article_count` values?
- Are articles included in the response?

### Step 2: Query MongoDB Directly
```bash
# Run the MongoDB query script
poetry run python scripts/check_dormant_narratives.py
```

**What to check:**
- How many narratives have `lifecycle_state='dormant'`?
- How many dormant narratives were updated in the last 30 days?
- Are there narratives with exactly 2 articles?
- What is their lifecycle_state?

### Step 3: Check Frontend Console Logs
The frontend has debug logging enabled in `Narratives.tsx`:

```typescript
// Line 63-68
const result = viewMode === 'archive' 
  ? await narrativesAPI.getArchivedNarratives(50, 30) 
  : await narrativesAPI.getNarratives();
console.log(`[DEBUG] ${viewMode} API returned:`, result.length, 'narratives');
if (viewMode === 'archive') {
  console.log('[DEBUG] Archive narratives lifecycle_state values:', result.map(n => n.lifecycle_state));
  console.log('[DEBUG] Archive narratives data:', result);
}
```

**What to check in browser console:**
- What does `[DEBUG] archive API returned:` show?
- Are narratives being received but filtered out?
- Check the full data structure logged

### Step 4: Check for Frontend Filtering
Look at line 137-151 in `Narratives.tsx`:

```typescript
const filteredNarratives = useMemo(() => {
  if (!selectedDate || viewMode !== 'pulse') {
    return narratives;
  }
  // ... filtering logic for pulse view
}, [narratives, selectedDate, viewMode]);
```

**For archive view**, `filteredNarratives` should equal `narratives` since `viewMode !== 'pulse'`.

### Step 5: Check Rendering Logic
The archive tab renders narratives starting at line 645:

```typescript
<div className="space-y-6">
  {narratives.map((narrative, index) => {
    // ... render each narrative card
  })}
</div>
```

**What to check:**
- Is `narratives` array empty?
- Are there any render conditions that might hide cards?

## Possible Issues

### Issue 1: No Dormant Narratives in Database
**Symptom:** API returns 0 narratives
**Solution:** Check if narratives are being marked as dormant by the lifecycle system

### Issue 2: Dormant Narratives Outside 30-Day Window
**Symptom:** Database has dormant narratives but API returns 0
**Solution:** Increase the `days` parameter or check `last_updated` timestamps

### Issue 3: Frontend Filtering
**Symptom:** API returns narratives but frontend shows none
**Solution:** Check console logs and filtering logic

### Issue 4: Old Schema Narratives
**Symptom:** Narratives exist but don't have `lifecycle_state` field
**Solution:** Run migration to add `lifecycle_state` to old narratives

### Issue 5: Article Count Mismatch
**Symptom:** "2 articles" shown but no narratives
**Possible cause:** The count might be coming from a different source (e.g., resurrection summary card)

## Quick Checks

### Check API Response
```bash
curl "http://localhost:8000/api/v1/narratives/archived?limit=50&days=30" | jq '.'
```

### Check MongoDB
```bash
mongosh
use crypto_news_aggregator
db.narratives.countDocuments({lifecycle_state: "dormant"})
db.narratives.find({lifecycle_state: "dormant"}).limit(5).pretty()
```

### Check Frontend State
Open browser console and run:
```javascript
// Check what data the frontend has
console.log('Narratives:', window.__narratives_debug);
```

## Expected Behavior

When archive tab is working correctly:
1. API should return narratives with `lifecycle_state='dormant'`
2. Frontend should receive and log them in console
3. Cards should render with purple border and Archive icon
4. Reawakened badge should show if `reawakening_count > 0`

## Next Steps

After running the debug scripts:
1. If API returns 0 narratives → Check database and lifecycle system
2. If API returns narratives but frontend shows none → Check frontend filtering/rendering
3. If narratives exist but aren't marked dormant → Run lifecycle state migration
