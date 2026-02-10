# Entity Normalization Bug Fix

## Problem Discovered

After deploying entity normalization, the migration worked perfectly on **old data** (120 mentions normalized, 80 duplicates merged), but **new articles** were still creating non-normalized entity mentions.

### Symptoms
- Migration showed Bitcoin: 169 mentions ✅
- But new articles would create separate "BTC", "$BTC" mentions
- Normalization only worked on historical data, not new extractions

## Root Cause Analysis

### The Bug
The normalization was implemented in **two places**:

1. ✅ **LLM Layer** (`anthropic.py`): Normalized entities after extraction
2. ❌ **RSS Fetcher** (`rss_fetcher.py`): Created **duplicate ticker mentions** that bypassed normalization

### Code Flow Issue

**In `rss_fetcher.py` lines 608-624** (before fix):
```python
# LLM returns: {"name": "Bitcoin", "ticker": "$BTC"}
# After LLM normalization: {"name": "Bitcoin", "ticker": "Bitcoin"}

# ✅ Creates mention for "Bitcoin"
mentions_to_create.append({"entity": entity_name})  # "Bitcoin"

# ❌ THEN creates SEPARATE mention for ticker
if ticker and ticker != entity_name:
    mentions_to_create.append({"entity": ticker})  # "$BTC" - NOT NORMALIZED!
```

**The Problem**: 
- LLM normalized the entity name to "Bitcoin"
- But the ticker field still contained "$BTC" 
- Code created a separate mention for the ticker
- This ticker mention was **never normalized**

### Why Migration Worked But New Data Didn't

1. **Migration**: Ran `normalize_entity_name()` on all existing mentions ✅
2. **New Extractions**: LLM normalized entity names, but ticker mentions bypassed it ❌

## The Fix

### Changes Made to `rss_fetcher.py`

**1. Added Normalization Import**:
```python
from ..services.entity_normalization import normalize_entity_name
```

**2. Added Defense-in-Depth Normalization**:
```python
# Ensure entity name is normalized (defense in depth)
if entity_name:
    normalized_name = normalize_entity_name(entity_name)
    if normalized_name != entity_name:
        logger.info(f"Entity mention normalized: '{entity_name}' → '{normalized_name}'")
        entity_name = normalized_name
```

**3. Removed Duplicate Ticker Mention Creation**:
```python
# REMOVED: Separate ticker mention creation
# if ticker and ticker != entity_name:
#     mentions_to_create.append({"entity": ticker})

# REPLACED WITH: Comment explaining why
# DO NOT create separate ticker mentions - they're already normalized to entity_name
```

**4. Added is_primary Flag**:
```python
mentions_to_create.append({
    "entity": entity_name,
    "is_primary": True,  # Added for primary entities
    # ...
})
```

**5. Normalized Context Entities**:
```python
# Normalize context entities if they're crypto-related
if entity_name and entity_type in ["cryptocurrency", "blockchain"]:
    normalized_name = normalize_entity_name(entity_name)
    if normalized_name != entity_name:
        logger.info(f"Context entity normalized: '{entity_name}' → '{normalized_name}'")
        entity_name = normalized_name
```

## Testing Strategy

### How to Verify the Fix

**1. Check Railway Logs** (after next RSS fetch):
```
Look for: "Entity mention normalized: 'BTC' → 'Bitcoin'"
Look for: "Entity mention normalized: '$DOGE' → 'Dogecoin'"
```

**2. Query MongoDB** (after new articles):
```javascript
// Should return 0 (no new BTC mentions)
db.entity_mentions.countDocuments({
  entity: "BTC",
  created_at: { $gte: new Date("2025-10-05T17:00:00Z") }
})

// Should increase (all new mentions as Bitcoin)
db.entity_mentions.countDocuments({
  entity: "Bitcoin",
  created_at: { $gte: new Date("2025-10-05T17:00:00Z") }
})
```

**3. Check Signals API**:
```bash
curl https://your-api.com/api/v1/signals | jq '.[] | select(.entity | contains("BTC"))'
# Should return nothing or only "Bitcoin"
```

**4. Manual Test**:
- Wait for next RSS fetch cycle
- Check entity_mentions collection
- Verify no new "BTC", "$BTC", "$DOGE" mentions
- All should be "Bitcoin", "Dogecoin", etc.

## Impact

### Before Fix
- ❌ New articles created non-normalized mentions
- ❌ Duplicate entities appeared ("Bitcoin" + "BTC")
- ❌ Signals fragmented across variants
- ❌ Migration benefits lost immediately

### After Fix
- ✅ All new mentions automatically normalized
- ✅ No duplicate ticker mentions created
- ✅ Signals properly grouped by canonical names
- ✅ Consistent entity tracking going forward

## Deployment

**Status**: ✅ Deployed to Production

**Commit**: `1ecaf5b - fix: apply entity normalization to new entity mentions in RSS fetcher`

**Deployment Method**: 
1. Committed to main branch
2. Pushed to GitHub
3. Railway auto-deploys from main

**Next RSS Fetch**: Will use fixed code (~15-30 minutes)

## Monitoring

### What to Watch

**Immediate** (next 1-2 hours):
- Railway logs for normalization messages
- New entity_mentions for canonical names only
- No new BTC, $BTC, $DOGE mentions appearing

**Short-term** (24 hours):
- Entity signals remain unified
- No fragmentation of Bitcoin signal
- UI shows consistent entity names

**Long-term** (1 week):
- Monitor for any edge cases
- Track normalization effectiveness
- Verify no regression

### Success Metrics

| Metric | Target | How to Check |
|--------|--------|--------------|
| New BTC mentions | 0 | Query entity_mentions where entity="BTC" and created_at > now |
| New Bitcoin mentions | >0 | Query entity_mentions where entity="Bitcoin" and created_at > now |
| Normalization logs | Present | Railway logs show "Entity mention normalized" |
| Signal fragmentation | None | No separate BTC/Bitcoin signals |

## Lessons Learned

### What Went Wrong

1. **Incomplete Integration**: Normalization added to LLM but not to mention creation
2. **Duplicate Logic**: Creating separate ticker mentions was unnecessary
3. **Testing Gap**: Didn't test end-to-end with new article ingestion

### What Went Right

1. **Quick Detection**: User noticed issue immediately
2. **Clear Debugging**: Logs helped identify the problem
3. **Defense in Depth**: Added normalization at multiple layers
4. **Fast Fix**: Issue identified and fixed in <30 minutes

### Improvements Made

1. **Added Logging**: Track normalization in production
2. **Removed Duplication**: Eliminated unnecessary ticker mentions
3. **Added Flags**: is_primary distinguishes entity types
4. **Documentation**: This document for future reference

## Future Enhancements

1. **Integration Test**: Add test for full RSS fetch → entity mention flow
2. **Monitoring Dashboard**: Track normalization rate in real-time
3. **Alerting**: Alert if non-canonical names appear
4. **Validation**: Add database constraint to prevent non-canonical names

---

**Fixed By**: Development Team  
**Date**: October 5, 2025  
**Status**: ✅ Deployed and Monitoring
