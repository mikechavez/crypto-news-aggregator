# Narrative UI Filtering Analysis

**Analysis Date:** October 16, 2025  
**Issue:** UI shows only 13 narratives (10 in Pulse, 3 in Archive) when database has 164 total

## Root Cause Identified

The issue is **NOT a date filter** but a **hard-coded limit** in the database query function.

### Database Query Limits

1. **`get_active_narratives()` function** (line 240-270 in `db/operations/narratives.py`):
   - **Default limit: 10 narratives**
   - Only returns the 10 most recently updated narratives
   - No date filtering - just sorts by `last_updated` DESC and limits results

2. **`get_resurrected_narratives()` function** (line 321-359):
   - **Default limit: 20 narratives**
   - Filters by: `reawakening_count > 0` AND `last_updated >= (now - 7 days)`
   - Only 3 narratives meet these criteria

### API Endpoint Configuration

**`/api/v1/narratives/active`** (line 141-299 in `api/v1/endpoints/narratives.py`):
```python
async def get_active_narratives_endpoint(
    limit: int = Query(10, ge=1, le=20, description="Maximum number of narratives to return")
):
```
- Default: 10 narratives
- Maximum allowed: 20 narratives
- Frontend doesn't pass a limit parameter, so it gets the default 10

**`/api/v1/narratives/resurrections`** (line 302-427):
```python
async def get_resurrected_narratives_endpoint(
    limit: int = Query(20, ge=1, le=100, description="Maximum number of narratives to return"),
    days: int = Query(7, ge=1, le=30, description="Look back X days for resurrected narratives")
):
```
- Default: 20 narratives, 7 days lookback
- Only returns narratives with `reawakening_count > 0` updated in last 7 days

## Database State Analysis

### Total Narratives: 164

#### By Lifecycle State:
| State | Count | Percentage |
|-------|-------|------------|
| **hot** | 101 | 61.6% |
| **No lifecycle_state field** | 36 | 22.0% |
| **emerging** | 19 | 11.6% |
| **rising** | 6 | 3.7% |
| **dormant** | 2 | 1.2% |

#### Date Ranges by State:

**Hot (101 narratives):**
- Oldest first_seen: Oct 15, 2025 23:50:27
- Most recent last_updated: Oct 16, 2025 22:00:39

**Emerging (19 narratives):**
- Oldest first_seen: Oct 16, 2025 00:10:09
- Most recent last_updated: Oct 16, 2025 22:00:38

**Rising (6 narratives):**
- Oldest first_seen: Oct 15, 2025 23:53:53
- Most recent last_updated: Oct 15, 2025 23:54:19

**Dormant (2 narratives):**
- Oldest first_seen: Oct 15, 2025 23:50:25
- Most recent last_updated: Oct 16, 2025 18:14:09

**No lifecycle_state field (36 narratives):**
- These are older narratives that haven't been updated with the new lifecycle system
- Most recent last_updated: Oct 16, 2025 22:00:39
- Oldest last_updated: Oct 12, 2025 16:57:23

### All Narratives Updated Recently
- **Last 7 days:** 164 narratives (100%)
- **Last 30 days:** 164 narratives (100%)
- **Older than 30 days:** 0 narratives

This confirms there's NO date filtering issue - all narratives are recent.

## Why UI Shows Only 13 Narratives

### Pulse View (10 narratives shown):
- Frontend calls `/api/v1/narratives/active` without limit parameter
- API uses default limit of 10
- Returns 10 most recently updated narratives

### Archive View (3 narratives shown):
- Frontend calls `/api/v1/narratives/resurrections` with default params
- API filters for `reawakening_count > 0` AND `last_updated >= (now - 7 days)`
- Only 3 narratives have been resurrected (reactivated from dormant state) in the last 7 days

### Cards View:
- Uses same data as Pulse view (10 narratives)
- Just displays them differently

## Solutions

### Option 1: Increase API Limit (Quick Fix)
**Change the default limit in the API endpoint:**

```python
# In api/v1/endpoints/narratives.py, line 143
async def get_active_narratives_endpoint(
    limit: int = Query(100, ge=1, le=200, description="Maximum number of narratives to return")
):
```

**Pros:**
- Simple one-line change
- Shows all narratives immediately

**Cons:**
- Returns all narratives every time (may be slow with thousands of narratives)
- No pagination

### Option 2: Add Pagination (Recommended)
**Add skip/limit parameters for proper pagination:**

```python
async def get_active_narratives_endpoint(
    skip: int = Query(0, ge=0, description="Number of narratives to skip"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of narratives to return")
):
```

**Pros:**
- Scalable solution
- Better performance
- Allows "Load More" functionality in UI

**Cons:**
- Requires frontend changes to support pagination

### Option 3: Add Lifecycle State Filtering (Best UX)
**Allow filtering by lifecycle state:**

```python
async def get_active_narratives_endpoint(
    limit: int = Query(100, ge=1, le=200),
    lifecycle_state: Optional[str] = Query(None, description="Filter by lifecycle state")
):
```

Then update `get_active_narratives()` to use `lifecycle_state` field:

```python
if lifecycle_filter:
    query["lifecycle_state"] = lifecycle_filter  # Changed from "lifecycle"
```

**Pros:**
- Users can filter by hot/emerging/rising/dormant
- Better UX for exploring narratives
- Reduces data transfer

**Cons:**
- More complex implementation
- Requires UI changes

## Immediate Recommendation

**Increase the default limit to 100** as a quick fix:

1. Change API endpoint default from 10 to 100
2. Change max limit from 20 to 200
3. This will show all 164 narratives immediately

Then implement pagination in a future update for scalability.

## Additional Findings

### Missing lifecycle_state Field
36 narratives (22%) don't have the `lifecycle_state` field. These are likely:
- Older narratives created before the lifecycle system was implemented
- Narratives that haven't been processed by the new lifecycle detection code

**Recommendation:** Run a migration script to backfill `lifecycle_state` for these narratives based on their current metrics.

---

**Scripts Used:**
- `scripts/check_narrative_states.py` - Analyze narrative lifecycle states
- `scripts/check_narrative_coverage.py` - Analyze article narrative coverage

**Run Commands:**
```bash
poetry run python scripts/check_narrative_states.py
poetry run python scripts/check_narrative_coverage.py
```
