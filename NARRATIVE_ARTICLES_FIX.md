# Narrative Articles Fix - Missing _id Field

## Problem
Articles were not showing in the Cards and Pulse tabs after deployment. When users expanded narrative cards or clicked on timeline narratives, no articles were displayed.

## Root Cause Analysis

### Investigation Steps
1. **Created API test script** (`scripts/test_narrative_articles_api.py`)
   - Tests the full flow: fetch narratives → get specific narrative → verify articles
   - Discovered the API was returning narratives but without the `_id` field

2. **Backend endpoint verification**
   - `GET /api/v1/narratives/active` - Returns list of narratives ✅
   - `GET /api/v1/narratives/{id}` - Returns single narrative with articles ✅
   - Both endpoints correctly fetch and include articles in the response

3. **Frontend integration check**
   - `context-owl-ui/src/api/narratives.ts` - API client correctly configured ✅
   - `context-owl-ui/src/pages/Narratives.tsx` - Uses `narrative._id` to fetch articles
   - `context-owl-ui/src/components/TimelineView.tsx` - Uses `narrative._id` to fetch articles

### The Issue
The `NarrativeResponse` Pydantic model defined:
```python
id: Optional[str] = Field(default=None, alias="_id", ...)
```

The backend was adding `"_id"` to the response dict, but Pydantic was:
1. Accepting `"_id"` as input (due to `populate_by_name = True`)
2. Mapping it to the `id` field internally
3. **NOT serializing it back as `_id` in the JSON response**

This meant the frontend received narratives without an `_id` field, so it couldn't call `getNarrativeById(narrative._id)` to fetch articles.

## Solution
Modified both narrative endpoints to include **both** `id` and `_id` fields in the response:

```python
narrative_id = str(narrative.get("_id", ""))
response_data = {
    "id": narrative_id,      # For Pydantic model
    "_id": narrative_id,     # For frontend compatibility
    "theme": narrative.get("theme", ""),
    # ... rest of fields
}
```

### Files Changed
- `src/crypto_news_aggregator/api/v1/endpoints/narratives.py`
  - Line 261-264: Added both fields to list endpoint
  - Line 684-687: Added both fields to detail endpoint

## Testing

### Test Script
Run the test script to verify the fix:
```bash
export API_KEY=<your-api-key>
poetry run python scripts/test_narrative_articles_api.py
```

Expected output:
- ✅ API returns narratives with `_id` field
- ✅ API returns narrative detail with articles array
- ✅ Articles include: title, url, source, published_at

### Manual Testing
1. Open the frontend at https://context-owl.vercel.app
2. Navigate to Narratives page
3. Click on a narrative card to expand it
4. **Expected**: Articles should load and display
5. Switch to Pulse view
6. Click on a timeline narrative
7. **Expected**: Modal should show articles

## Deployment

### Backend (Railway)
The fix is in the `fix/narrative-articles-missing-id` branch. Railway will auto-deploy when merged to main.

### Frontend (Vercel)
No frontend changes needed - the issue was purely backend.

## Prevention
- Added test script to verify API response structure
- Consider adding integration tests that verify the full flow from API to frontend
- Document expected response structure in API documentation

## Related Issues
- Frontend was already logging debug info when articles weren't loading
- The console logs would have shown `narrative._id` as `undefined`
- This fix resolves the root cause, making those debug logs unnecessary
