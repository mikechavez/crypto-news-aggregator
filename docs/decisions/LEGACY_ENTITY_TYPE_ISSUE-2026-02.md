# Legacy Entity Type Issue - "CRYPTO_ENTITY"

## 🔍 Verification Results

**Date**: 2025-10-05  
**API Endpoint**: https://context-owl-production.up.railway.app/api/v1/signals/trending?limit=10

### Raw API Response Analysis

#### ✅ Entities with Correct Types
```json
{
  "entity": "Bitwise",
  "entity_type": "company"  ✓
}
{
  "entity": "Dogecoin",
  "entity_type": "cryptocurrency"  ✓
}
{
  "entity": "JPMorgan",
  "entity_type": "company"  ✓
}
{
  "entity": "US government",
  "entity_type": "organization"  ✓
}
{
  "entity": "Federal Reserve",
  "entity_type": "organization"  ✓
}
```

#### ❌ Entities with Legacy "CRYPTO_ENTITY" Type
```json
{
  "entity": "FTX",
  "entity_type": "CRYPTO_ENTITY",  ⚠️ LEGACY
  "signal_score": 2.1,
  "first_seen": "2025-09-23T21:24:54"  ← OLD DATA (Sept 23)
}
{
  "entity": "Bitcoin",
  "entity_type": "CRYPTO_ENTITY",  ⚠️ LEGACY
  "signal_score": 0.97,
  "first_seen": "2025-09-02T16:03:25"  ← VERY OLD DATA (Sept 2)
}
```

---

## 🧬 Root Cause

### Timeline Analysis

**September 2-23, 2025**: Early system development
- Entity extraction was using a different classification system
- Entities were being tagged as "CRYPTO_ENTITY" (generic catch-all type)
- These records were created and stored in MongoDB

**October 5, 2025**: Current system
- LLM now returns detailed types: `cryptocurrency`, `company`, `organization`, etc.
- New entities get proper types (Dogecoin → `cryptocurrency`, Bitwise → `company`)
- **But old records were never migrated!**

### Why Only FTX and Bitcoin?

These are **legacy records** that survived from the early system:
1. **Created before** the proper entity type system was implemented
2. **Never updated** because signal scores only update metrics, not entity_type
3. **Still in database** because they have ongoing mentions

---

## 🎯 The Real Problem

### Two Issues, Not One

**Issue #1: Legacy Data** ✅ **IDENTIFIED**
- FTX and Bitcoin have `"CRYPTO_ENTITY"` stored in MongoDB
- Created during early development phase
- Need database migration to fix

**Issue #2: Frontend Display** ✅ **ALREADY FIXED**
- Frontend now properly formats entity types
- `formatEntityType()` will display "Crypto Entity" (capitalized)
- Colored badge will use gray fallback color

---

## ✅ Solution

### Step 1: Database Migration (Required)

Run the migration script to fix legacy entity types:

```bash
# Set production MongoDB credentials
export MONGODB_URI="your_production_mongodb_uri"
export MONGODB_DB_NAME="crypto_news"

# Run migration
poetry run python scripts/fix_legacy_entity_types.py
```

**What it does**:
- Finds all signals with `entity_type: "CRYPTO_ENTITY"`
- Maps to correct types:
  - Bitcoin → `cryptocurrency`
  - FTX → `company` (it's an exchange company)
- Updates MongoDB records
- Verifies changes

### Step 2: Verify Fix

After migration, check the API again:
```bash
curl "https://context-owl-production.up.railway.app/api/v1/signals/trending?limit=10" | python3 -m json.tool | grep -A 3 "FTX\|Bitcoin"
```

Expected result:
```json
{
  "entity": "FTX",
  "entity_type": "company"  ✓ FIXED
}
{
  "entity": "Bitcoin",
  "entity_type": "cryptocurrency"  ✓ FIXED
}
```

### Step 3: Frontend Already Handles It

The frontend changes deployed today will properly display:
- **Before migration**: "Crypto Entity" (gray badge) - fallback formatting
- **After migration**: "Company" (green badge) for FTX, "Cryptocurrency" (blue badge) for Bitcoin

---

## 📊 Entity Type Mapping

For the migration script:

| Entity | Current Type | Correct Type | Reasoning |
|--------|-------------|--------------|-----------|
| Bitcoin | CRYPTO_ENTITY | cryptocurrency | It's a cryptocurrency |
| FTX | CRYPTO_ENTITY | company | It's an exchange company |
| Ethereum | CRYPTO_ENTITY | cryptocurrency | It's a cryptocurrency |
| Solana | CRYPTO_ENTITY | cryptocurrency | It's a cryptocurrency |
| Binance | CRYPTO_ENTITY | company | It's an exchange company |
| Coinbase | CRYPTO_ENTITY | company | It's an exchange company |

---

## 🔮 Prevention

### How to Prevent Future Legacy Data

**Option 1: Signal Score Update Logic**
Modify `worker.py` to update entity_type if it's "CRYPTO_ENTITY":

```python
# In worker.py, before upsert_signal_score
if entity_type == "CRYPTO_ENTITY":
    # Reclassify based on entity name
    entity_type = reclassify_legacy_entity(entity)
```

**Option 2: Database Constraint**
Add validation in `upsert_signal_score()` to reject invalid types:

```python
VALID_ENTITY_TYPES = [
    "cryptocurrency", "blockchain", "protocol", 
    "company", "organization", "event", 
    "concept", "person", "location"
]

if entity_type not in VALID_ENTITY_TYPES:
    logger.warning(f"Invalid entity_type '{entity_type}' for {entity}, defaulting to 'cryptocurrency'")
    entity_type = "cryptocurrency"
```

**Option 3: Periodic Cleanup Job**
Add a background task to periodically check for and fix legacy types:

```python
@celery_app.task
def cleanup_legacy_entity_types():
    """Run weekly to catch any legacy entity types"""
    # Find and fix CRYPTO_ENTITY types
    pass
```

---

## 📝 Summary

### What We Found
1. ✅ Frontend display fix is working correctly
2. ❌ MongoDB has legacy "CRYPTO_ENTITY" values for FTX and Bitcoin
3. ✅ New entities get proper types from the LLM
4. ❌ Old records were never migrated

### What Needs to Be Done
1. **Run database migration** - Fix FTX and Bitcoin entity types
2. **Verify on production** - Check API returns correct types
3. **Add prevention** - Ensure no new "CRYPTO_ENTITY" types are created

### Impact
- **User-facing**: Frontend already handles it gracefully with fallback formatting
- **Data quality**: Need to fix for proper filtering and analytics
- **Priority**: Medium - not breaking, but should be fixed for data consistency

---

## 🚀 Action Items

- [ ] Run `scripts/fix_legacy_entity_types.py` on production MongoDB
- [ ] Verify FTX shows as "company" in API response
- [ ] Verify Bitcoin shows as "cryptocurrency" in API response
- [ ] Check production UI shows proper colored badges
- [ ] Add validation to prevent future "CRYPTO_ENTITY" values
- [ ] Document in system architecture docs
