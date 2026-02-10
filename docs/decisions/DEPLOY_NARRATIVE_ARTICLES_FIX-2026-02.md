# Deploy Narrative Articles Fix

## Quick Summary
**Issue**: Articles not showing in Cards and Pulse tabs  
**Root Cause**: API responses missing `_id` field needed by frontend  
**Fix**: Backend now includes both `id` and `_id` in narrative responses  
**Branch**: `fix/narrative-articles-missing-id`

## Deployment Steps

### 1. Merge to Main
```bash
# Create PR and merge via GitHub
# Or merge locally:
git checkout main
git merge fix/narrative-articles-missing-id
git push origin main
```

### 2. Railway Auto-Deploy
Railway will automatically deploy when main branch is updated.

**Monitor deployment**:
1. Go to Railway dashboard
2. Check deployment logs for errors
3. Verify service starts successfully

### 3. Test the Fix

#### Option A: Use Test Script
```bash
export API_KEY=b9c5e92b426c96d7fe1573e015b0ca7576de9147497916f2b658690faac8988a8
poetry run python scripts/test_narrative_articles_api.py
```

**Expected output**:
```
✅ SUCCESS: API returns X articles
   Article fields: title, url, source, published_at
```

#### Option B: Manual Frontend Test
1. Open https://context-owl.vercel.app
2. Go to Narratives page (Cards view)
3. Click to expand a narrative card
4. **Verify**: Articles load and display with titles, sources, and links
5. Switch to Pulse view
6. Click on a timeline narrative
7. **Verify**: Modal shows narrative details with articles

### 4. Verify API Response Structure

Test the API directly:
```bash
# Get narratives list
curl -H "X-API-Key: $API_KEY" \
  https://context-owl-production.up.railway.app/api/v1/narratives/active | jq '.[0] | keys'

# Should include "_id" in the keys
```

Expected keys in response:
- `_id` ← **This is the critical field that was missing**
- `id`
- `title`
- `summary`
- `articles`
- `article_count`
- etc.

### 5. Check Frontend Console

Open browser DevTools console and look for:
```
[DEBUG] Fetching articles for narrative: <some-id>
[DEBUG] API Response: { _id: "...", articles: [...] }
[DEBUG] Articles in response: <number>
```

**Before fix**: `_id` would be `undefined`  
**After fix**: `_id` should be a valid MongoDB ObjectId string

## Rollback Plan

If issues occur:
```bash
# Revert the commit
git revert HEAD
git push origin main

# Railway will auto-deploy the rollback
```

## Success Criteria

- ✅ API returns `_id` field in narrative list endpoint
- ✅ API returns `_id` field in narrative detail endpoint
- ✅ Frontend can expand cards and see articles
- ✅ Frontend Pulse view shows articles when clicking narratives
- ✅ No console errors about undefined `_id`

## Notes

- **No frontend changes needed** - this is purely a backend fix
- **No database migration needed** - only API response structure changed
- **Backward compatible** - includes both `id` and `_id` for compatibility
- **Test script included** - use `scripts/test_narrative_articles_api.py` for verification
