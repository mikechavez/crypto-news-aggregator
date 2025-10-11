# Fix: Entity-Narrative Linking Bug

## Problem
Entities were showing as "Emerging" instead of being linked to narratives. Entities like Ripple, SEC, Binance, BlackRock, and Tether weren't appearing in their appropriate narrative categories (Regulatory, Institutional Investment, Stablecoin, etc.).

## Root Cause
Data format inconsistency in the `entity_mentions` collection:
- Some records have `article_id` as **ObjectId** (newer records)
- Some records have `article_id` as **string** (legacy records)
- The `extract_entities_from_articles()` function only queried for ObjectId format, missing all string-format records

## Solution
Modified `extract_entities_from_articles()` to query both formats using MongoDB `$or` operator:

```python
# Before
cursor = entity_mentions_collection.find({"article_id": article_id})

# After
cursor = entity_mentions_collection.find({
    "$or": [
        {"article_id": article_id},        # ObjectId format
        {"article_id": str(article_id)}    # String format
    ]
})
```

## Changes
- **Fixed**: `src/crypto_news_aggregator/services/narrative_service.py`
  - Updated `extract_entities_from_articles()` to handle mixed article_id formats
- **Updated**: `tests/services/test_narrative_service.py`
  - Fixed existing test to handle new query format
  - Added regression test: `test_extract_entities_handles_mixed_article_id_formats()`
- **Added**: Documentation
  - `INVESTIGATION_SUMMARY.md` - Full investigation details
  - `NARRATIVE_ENTITY_LINKING_FIX.md` - Technical fix documentation

## Testing
✅ All narrative service tests pass (8/8)
```bash
poetry run pytest tests/services/test_narrative_service.py -v
```

✅ Verified with diagnostic scripts:
- Before: 0/7 narratives had entities linked
- After: 7/7 narratives have entities properly linked

## Impact
- **Immediate**: Entities will be properly linked to narratives on next detection cycle (10 minutes)
- **Backward compatible**: Handles both ObjectId and string formats
- **No migration needed**: Works with existing data

## Deployment
- ✅ Feature branch created: `fix/narrative-entity-linking`
- ✅ Tests passing
- ✅ Ready for merge to main
- ✅ Will auto-deploy to Railway on merge

## Verification Steps
After deployment:
1. Wait 10 minutes for narrative detection cycle
2. Check `/api/v1/narratives` endpoint
3. Verify narratives have entities in the `entities` array
4. Check entity detail pages - should show narrative links instead of "Emerging"

## Related Issues
Resolves issue where entities weren't being linked to narratives, causing all entities to incorrectly show as "Emerging" status.
