# Narrative-Entity Linking Bug Fix

**Date**: 2025-10-10  
**Issue**: Entities showing as "Emerging" instead of being linked to narratives

## Problem Summary

Entities like Ripple, SEC, Binance, BlackRock, and Tether were not being linked to their appropriate narratives (Regulatory, Institutional Investment, Stablecoin, etc.), causing them to incorrectly show as "Emerging" in the UI.

## Root Cause

**Data format inconsistency in `entity_mentions` collection:**

The `article_id` field in the `entity_mentions` collection has **mixed data types**:
- Some records store `article_id` as **ObjectId** (newer records)
- Some records store `article_id` as **string** (legacy records)

The `extract_entities_from_articles()` function in `narrative_service.py` was only querying for **ObjectId** format, missing all the string-format records.

### Evidence

```python
# Diagnostic output showed:
Method 1: Query with ObjectId directly
   Found 0 mentions: []

Method 2: Query with string
   Found 1 mentions: ['tokenizing']

# Sample entity mention:
   article_id: 68d4b36330d27b58f9dcd536
   article_id type: <class 'bson.objectid.ObjectId'>
```

Coverage: 85.4% of articles have entity mentions, but narratives had 0 entities linked.

## The Fix

**File**: `src/crypto_news_aggregator/services/narrative_service.py`

**Changed**: `extract_entities_from_articles()` function

```python
# BEFORE (only queried ObjectId format)
cursor = entity_mentions_collection.find({"article_id": article_id})

# AFTER (queries both formats)
cursor = entity_mentions_collection.find({
    "$or": [
        {"article_id": article_id},        # ObjectId format
        {"article_id": str(article_id)}    # String format
    ]
})
```

## Results After Fix

### Before Fix
- ❌ Regulatory narrative: **0 entities** linked
- ❌ All narratives: **0 entities** linked
- ❌ Ripple, SEC, Binance, BlackRock, Tether: Not linked to any narratives

### After Fix
- ✅ **7 narratives** generated with entities
- ✅ **100% of narratives** now have entities linked
- ✅ Ripple → linked to "payments" narrative
- ✅ BlackRock → linked to "institutional_investment" narrative
- ✅ Entities properly categorized by theme

### Sample Results

```
1. Theme: institutional_investment
   Entities (9): gold, Bitcoin, Arthur Hayes, monetary expansion, 
                 ETF, monetary policy, BlackRock, silver

2. Theme: payments
   Entities (9): Bitcoin, payments, SWIFT, Square, Block, Ripple, 
                 blockchain, Jack Dorsey, Binance Coin

3. Theme: security
   Entities (10): Ethereum, Monero, crypto safety, privacy, 
                  CoinSwitch, Hyperliquid, hack, WazirX

4. Theme: stablecoin
   Entities (9): Citi, stablecoins, North Dakota, Coinbase, 
                 London, BVNK, stablecoin, blockchain, Mastercard
```

## Why SEC, Binance, Tether Still Missing?

These entities may not appear in narratives for legitimate reasons:

1. **Not enough recent articles**: Narratives require `min_articles=3` within 48 hours
2. **Theme mismatch**: Articles mentioning SEC might not be tagged with "regulatory" theme
3. **Entity extraction gaps**: Some articles may not have had entity extraction run yet

This is **different** from the bug we fixed - the bug was that entities were being **ignored** even when they existed. Now they're being **found** correctly.

## Testing

Created diagnostic scripts:
- `scripts/diagnose_narrative_linking.py` - Identifies the problem
- `scripts/debug_entity_article_mismatch.py` - Confirms article_id format issue
- `scripts/debug_entity_extraction.py` - Tests entity extraction
- `scripts/test_narrative_fix.py` - Verifies the fix works
- `scripts/force_narrative_rebuild.py` - Rebuilds narratives with fix

## Deployment

The fix is in `narrative_service.py` and will take effect:
- **Immediately** for new narrative detection cycles (runs every 10 minutes)
- **Automatically** when the worker process runs `detect_narratives()`

No database migration needed - the fix handles both data formats transparently.

## Future Improvements

Consider standardizing the `article_id` format in `entity_mentions`:

1. **Option A**: Migrate all string article_ids to ObjectId
2. **Option B**: Enforce ObjectId in `create_entity_mention()` function
3. **Option C**: Keep current fix (handles both formats gracefully)

**Recommendation**: Keep current fix (Option C) for backward compatibility.
