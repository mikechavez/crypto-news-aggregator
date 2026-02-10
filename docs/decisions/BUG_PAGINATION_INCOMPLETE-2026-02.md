# BUG REPORT: Pagination Implementation Incomplete

**Status:** 🔴 BLOCKING
**Severity:** P1 (High)
**Date Discovered:** 2026-01-30
**Discovered By:** Manual testing - Bitcoin Accumulation narrative (69 articles)

---

## Symptom

When expanding a narrative with 69 articles, the UI shows:
```
▼ 69 Articles
Showing 20 of 20
```

Expected: "Showing 20 of 69"
Actual: "Showing 20 of 20" (incorrectly displays 20 as the total)

Users cannot access articles 21-69 even though they exist.

---

## Root Cause Analysis

### Backend Issue: `getNarrativeById` Returns Only 20 Articles

**File:** `src/crypto_news_aggregator/api/v1/endpoints/narratives.py`
**Line:** 694

```python
# Current code - HARDCODED LIMIT
articles = await get_articles_for_narrative(article_ids, limit=20)
```

**File:** `src/crypto_news_aggregator/api/v1/endpoints/narratives.py`
**Lines:** 28-73 - `get_articles_for_narrative()` function

```python
async def get_articles_for_narrative(article_ids: List[str], limit: int = 20) -> List[Dict[str, Any]]:
    """
    Fetch article details for a list of article IDs.
    ...
    limit: Maximum number of articles to return (default 20)
    """
```

**Issue:** This function is called with `limit=20` and only returns 20 articles, even if there are 184+ articles.

### Missing: Pagination Endpoint

**Expected Endpoint (from tests):** `/api/v1/narratives/{narrative_id}/articles?offset=0&limit=20`

**Current Status:** ❌ Does NOT exist

**Test File:** `tests/api/test_narratives_pagination.py`

The test file imports a function that doesn't exist:
```python
from crypto_news_aggregator.api.v1.endpoints.narratives import get_articles_paginated
```

Tests expect this function signature:
```python
result = await get_articles_paginated(
    narrative_id=sample_narrative_id,
    offset=0,
    limit=20,
    db=mock_db
)
```

Expected response:
```python
{
    "articles": [...],
    "total_count": 184,
    "offset": 0,
    "limit": 20,
    "has_more": True
}
```

**All 10 tests reference this function** but it was never implemented.

### Frontend Issue: No Total Count Tracking

**File:** `context-owl-ui/src/pages/Narratives.tsx`
**Line:** 112

```typescript
const totalArticles = articles.length;  // ❌ Gets length of loaded articles, not total
const hasMore = visibleArticles.length < totalArticles;  // ❌ Always false after 20 articles
```

Frontend calculates `totalArticles` from the fetched array length, which is always 20. It doesn't know the true total (69, 184, etc.) because the backend never sends it.

---

## Impact Assessment

### Directly Affected
- ❌ FEATURE-019 (Article Pagination) - Frontend incomplete
- ❌ FEATURE-020 (Skeleton Loaders) - Looks good but no real pagination
- ❌ FEATURE-021 (Error Handling) - Can't test with >20 articles
- ❌ FEATURE-022 (Progress Indicator) - Can't calculate real progress
- ❌ FEATURE-023 (State Preservation) - Works but only for 20 articles
- ❌ FEATURE-024 (Smooth Scrolling) - Can't scroll to newly loaded articles

### PR #139 Status
- ✅ Skeleton loaders implementation is correct
- ✅ PR should remain merged (no issues with FEATURE-020)
- ❌ But pagination is broken, so feature set is incomplete

---

## Implementation Checklist

### Backend Implementation Required

**Task 1: Add `get_articles_paginated()` Function**
- Location: `src/crypto_news_aggregator/api/v1/endpoints/narratives.py`
- Function signature: `async def get_articles_paginated(narrative_id: str, offset: int = 0, limit: int = 20, db = None) -> Dict`
- Validations needed:
  - `offset >= 0` (return 400 if not)
  - `limit > 0 and limit <= 50` (return 400 if not)
  - narrative_id is valid ObjectId format (return 400 if not)
  - narrative exists in DB (return 404 if not)
- Returns: `{"articles": [...], "total_count": int, "offset": int, "limit": int, "has_more": bool}`
- Logic:
  1. Get narrative by ID to fetch `article_ids` list
  2. Calculate `total_count = len(article_ids)`
  3. Slice: `sliced_ids = article_ids[offset:offset+limit]`
  4. Fetch article details for sliced IDs
  5. Calculate `has_more = (offset + limit) < total_count`
  6. Return response dict

**Task 2: Add API Endpoint**
- Route: `GET /api/v1/narratives/{narrative_id}/articles`
- Query parameters:
  - `offset` (int, default=0, ge=0)
  - `limit` (int, default=20, ge=1, le=50)
- Response: Use `get_articles_paginated()` function
- Endpoint code: ~20 lines

**Task 3: Run Backend Tests**
```bash
pytest tests/api/test_narratives_pagination.py -v
```
All 10 tests should pass:
- ✅ test_get_articles_pagination_default
- ✅ test_get_articles_pagination_second_page
- ✅ test_get_articles_pagination_last_page
- ✅ test_get_articles_limit_exceeds_max
- ✅ test_get_articles_negative_offset
- ✅ test_get_articles_narrative_with_few_articles
- ✅ test_get_articles_narrative_not_found
- ✅ test_get_articles_invalid_narrative_id
- ✅ test_get_articles_offset_beyond_total
- ✅ test_get_articles_empty_narrative

### Frontend Implementation Required

**Task 1: Update API Client**
- File: `context-owl-ui/src/api/narratives.ts`
- Add method: `getArticlesForNarrative(id: string, offset: number, limit: number)`
- Calls: `/api/v1/narratives/{id}/articles?offset={offset}&limit={limit}`

**Task 2: Update Narratives Component**
- File: `context-owl-ui/src/pages/Narratives.tsx`
- Track `totalCount` in pagination state (not just `articles.length`)
- Update "Showing X of Y" badge to use `totalCount`
- Use pagination endpoint instead of `getNarrativeById`

**Task 3: Manual Testing**
Test cases:
1. ✅ Expand 69-article narrative → shows "Showing 20 of 69"
2. ✅ Click "Load More" → shows "Showing 40 of 69"
3. ✅ Continue until all loaded → shows "Showing 69 of 69"
4. ✅ "Load More" button disappears when all loaded
5. ✅ Collapse/re-expand → state persists

---

## Files Involved

### Backend
- `src/crypto_news_aggregator/api/v1/endpoints/narratives.py` - Missing function + endpoint
- `tests/api/test_narratives_pagination.py` - Tests already written (specifications)

### Frontend
- `context-owl-ui/src/api/narratives.ts` - Missing API method
- `context-owl-ui/src/pages/Narratives.tsx` - Wrong state tracking

### Related
- `docs/tickets/feature-019-article-pagination.md` - Implementation guide (has wrong instructions)
- `PR #139` - Merged but incomplete (FEATURE-020 is good, but pagination is broken)

---

## Testing Evidence

### Test File Shows Expected Implementation
`tests/api/test_narratives_pagination.py` lines 149, 209, 259, etc.:

```python
# Tests import function that doesn't exist
from crypto_news_aggregator.api.v1.endpoints.narratives import get_articles_paginated

# Tests call function with these parameters
result = await get_articles_paginated(
    narrative_id=sample_narrative_id,
    offset=0,
    limit=20,
    db=mock_db
)

# Tests expect this response structure
assert "articles" in result
assert "total_count" in result
assert "offset" in result
assert "limit" in result
assert "has_more" in result
```

**Conclusion:** Tests were written as design specifications, but the actual function was never implemented.

---

## Resolution Steps

1. **Backend First** (45 min - 1 hour):
   - Add `get_articles_paginated()` function
   - Add `/api/v1/narratives/{id}/articles` endpoint
   - Run tests: `pytest tests/api/test_narratives_pagination.py -v`
   - Verify all 10 tests pass

2. **Frontend Second** (1 - 1.5 hours):
   - Add API method to narratives.ts
   - Update Narratives.tsx to use pagination endpoint
   - Track `totalCount` in pagination state
   - Test with 69-article narrative

3. **Manual Verification** (30 min):
   - Expand narratives with 69+, 184+, 200+ articles
   - Load all articles incrementally
   - Verify badge shows correct total
   - Verify "Load More" button disappears at end

4. **PR Update** (Optional):
   - PR #139 already merged (good - skeleton loaders are correct)
   - No need to revert
   - New PR for pagination endpoint fix

---

## Why This Happened

1. FEATURE-019 ticket was marked "complete" but only frontend was done
2. Tests were written (specification-driven) but actual backend code wasn't implemented
3. Frontend code references an endpoint that doesn't exist
4. Manual testing didn't happen until now

---

## Estimated Time to Fix

- Backend implementation: 1 hour
- Frontend implementation: 1 - 1.5 hours
- Testing & verification: 30 min
- **Total: 2.5 - 3 hours**

---

## Blocking Status

🔴 **BLOCKS:**
- All FEATURE-021, 022, 023, 024 work
- Cannot accurately test any load-more functionality
- Cannot measure pagination performance
- User experience is broken (only 20 articles accessible)

---

**Next Action:** Implement backend pagination endpoint using existing test specifications.
