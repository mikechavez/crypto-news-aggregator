# Reactivated State Filtering Fix

## Problem
Reactivated narratives were appearing in the Archive tab instead of only in active views (Pulse/Cards). The Archive tab was incorrectly querying for resurrected narratives (those with `reawakening_count > 0`) instead of dormant narratives.

## Root Cause
1. **Backend**: `get_active_narratives()` didn't filter by `lifecycle_state` - it returned ALL narratives regardless of state
2. **Frontend**: Archive tab called `getResurrectedNarratives()` which returns reactivated narratives, not dormant ones

## Solution

### Backend Changes

#### 1. Updated `get_active_narratives()` in `narratives.py`
**File**: `src/crypto_news_aggregator/db/operations/narratives.py`

- Added filtering to only include active states: `emerging`, `rising`, `hot`, `cooling`, `reactivated`
- Excludes `dormant` and `echo` states from active views
- Maintains backward compatibility for narratives without `lifecycle_state` field

```python
active_states = ['emerging', 'rising', 'hot', 'cooling', 'reactivated']

query = {
    '$or': [
        {'lifecycle_state': {'$in': active_states}},
        {'lifecycle_state': {'$exists': False}}  # Backward compatibility
    ]
}
```

#### 2. Added `get_archived_narratives()` function
**File**: `src/crypto_news_aggregator/db/operations/narratives.py`

- New function specifically for dormant narratives
- Filters for `lifecycle_state = 'dormant'`
- Returns narratives updated within last 30 days (configurable)
- Sorted by most recently updated

```python
query = {
    "lifecycle_state": "dormant",
    "last_updated": {"$gte": cutoff_date}
}
```

#### 3. Added `/archived` API endpoint
**File**: `src/crypto_news_aggregator/api/v1/endpoints/narratives.py`

- New endpoint: `GET /api/v1/narratives/archived`
- Query parameters: `limit` (default 50), `days` (default 30)
- Returns dormant narratives with full metadata

### Frontend Changes

#### 1. Updated API client
**File**: `context-owl-ui/src/api/narratives.ts`

- Added `getArchivedNarratives()` method
- Calls `/api/v1/narratives/archived` endpoint

```typescript
getArchivedNarratives: async (limit: number = 50, days: number = 30): Promise<NarrativesResponse> => {
  return apiClient.get<NarrativesResponse>(`/api/v1/narratives/archived?limit=${limit}&days=${days}`);
}
```

#### 2. Updated Narratives page
**File**: `context-owl-ui/src/pages/Narratives.tsx`

- Changed Archive tab to call `getArchivedNarratives()` instead of `getResurrectedNarratives()`
- Updated description text to reflect dormant narratives

```typescript
queryFn: () => viewMode === 'archive' 
  ? narrativesAPI.getArchivedNarratives(50, 30) 
  : narrativesAPI.getNarratives()
```

## State Filtering Logic

### Active Views (Pulse/Cards)
**States shown**: `emerging`, `rising`, `hot`, `cooling`, `reactivated`
- Endpoint: `/api/v1/narratives/active`
- Excludes: `dormant`, `echo`

### Archive View
**States shown**: `dormant` only
- Endpoint: `/api/v1/narratives/archived`
- Shows narratives that have gone quiet (7+ days without new articles)

### Resurrections View (Separate)
**States shown**: Any state with `reawakening_count > 0`
- Endpoint: `/api/v1/narratives/resurrections`
- Shows narratives that have been reactivated from dormant state
- This is a separate feature for tracking resurrection patterns

## Lifecycle State Definitions

| State | Description | Where It Appears |
|-------|-------------|------------------|
| `emerging` | New narrative, < 4 articles | Active views |
| `rising` | Growing narrative, 1.5+ articles/day | Active views |
| `hot` | High activity, 7+ articles or 3+ articles/day | Active views |
| `cooling` | Recent activity but slowing, 3-7 days since update | Active views |
| `reactivated` | Dormant narrative with sustained new activity (4+ articles in 48h) | Active views |
| `echo` | Brief pulse of activity (1-3 articles in 24h, < 4 in 48h) | Archive view |
| `dormant` | No new articles for 7+ days | Archive view |

## Testing

### Manual Testing Steps

1. **Test Active Views**:
   ```bash
   curl http://localhost:8000/api/v1/narratives/active | jq '.[] | {title, lifecycle_state}'
   ```
   - Should NOT show any `dormant` or `echo` states
   - Should show `reactivated` narratives

2. **Test Archive View**:
   ```bash
   curl http://localhost:8000/api/v1/narratives/archived | jq '.[] | {title, lifecycle_state}'
   ```
   - Should ONLY show `dormant` state
   - Should NOT show `reactivated` narratives

3. **Test Frontend**:
   - Navigate to Narratives page
   - Switch between Cards, Pulse, and Archive tabs
   - Verify reactivated narratives appear in Cards/Pulse but NOT in Archive
   - Verify dormant narratives appear in Archive but NOT in Cards/Pulse

### Expected Behavior

✅ **Correct**:
- Reactivated narratives appear in Pulse/Cards views
- Dormant narratives appear in Archive view
- No overlap between active and archived views

❌ **Incorrect (before fix)**:
- Reactivated narratives appeared in Archive view
- Active views showed dormant narratives

## Files Modified

### Backend
1. `src/crypto_news_aggregator/db/operations/narratives.py`
   - Updated `get_active_narratives()` to filter by lifecycle_state
   - Added `get_archived_narratives()` function

2. `src/crypto_news_aggregator/api/v1/endpoints/narratives.py`
   - Added import for `get_archived_narratives`
   - Added `/archived` endpoint

### Frontend
1. `context-owl-ui/src/api/narratives.ts`
   - Added `getArchivedNarratives()` method

2. `context-owl-ui/src/pages/Narratives.tsx`
   - Updated Archive tab query to use `getArchivedNarratives()`
   - Updated description text

## Deployment Notes

1. **No database migration required** - uses existing `lifecycle_state` field
2. **Backward compatible** - narratives without `lifecycle_state` still appear in active views
3. **No breaking changes** - existing endpoints still work
4. **New endpoint** - `/api/v1/narratives/archived` is additive

## Related Documentation
- `RESURRECTIONS_API_IMPLEMENTATION.md` - Resurrection tracking feature
- `LIFECYCLE_STATE_IMPLEMENTATION.md` - Lifecycle state system
- `ECHO_REACTIVATION_STATES_IMPLEMENTATION.md` - Echo and reactivation states
