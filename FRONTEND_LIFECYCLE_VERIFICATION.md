# Frontend Lifecycle Data Verification

**Date:** October 15, 2025  
**Status:** ✅ Partially Complete

## Summary

Verified that the frontend can receive and display new lifecycle data fields from the backend API. The TypeScript types have been updated and the backend API endpoint now returns the new fields.

## Changes Made

### 1. Frontend Type Definitions (`context-owl-ui/src/types/index.ts`)

Added new type definitions and updated the `Narrative` interface:

```typescript
// New supporting types
export interface LifecycleHistoryEntry {
  state: string;              // Lifecycle state (emerging, rising, hot, cooling, dormant)
  timestamp: string;          // ISO timestamp when state changed
  article_count: number;      // Article count at time of change
  velocity: number;           // Velocity at time of change
}

export interface PeakActivity {
  date: string;               // Date of peak activity (YYYY-MM-DD)
  article_count: number;      // Number of articles at peak
  velocity: number;           // Velocity at peak
}

export interface EntityRelationship {
  a: string;                  // First entity name
  b: string;                  // Second entity name
  weight: number;             // Co-occurrence weight
}

// Updated Narrative interface
export interface Narrative {
  // ... existing fields ...
  lifecycle: string;          // Lifecycle stage: emerging, rising, hot, cooling, dormant
  lifecycle_state?: string;   // New lifecycle state field (if backend returns it)
  lifecycle_history?: LifecycleHistoryEntry[]; // History of lifecycle transitions
  fingerprint?: number[];     // Narrative fingerprint vector (if backend returns it)
  momentum?: string;          // Momentum trend: growing, declining, stable, unknown
  recency_score?: number;     // Freshness score (0-1), higher = more recent
  entity_relationships?: EntityRelationship[]; // Top entity co-occurrence pairs
  days_active?: number;       // Number of days narrative has been active
  peak_activity?: PeakActivity; // Peak activity metrics
  // ... other fields ...
}
```

### 2. Backend API Response Model (`src/crypto_news_aggregator/api/v1/endpoints/narratives.py`)

Updated `NarrativeResponse` Pydantic model to include new fields:

```python
class LifecycleHistoryEntry(BaseModel):
    """Lifecycle history entry."""
    state: str = Field(..., description="Lifecycle state (emerging, rising, hot, cooling, dormant)")
    timestamp: str = Field(..., description="ISO timestamp when state changed")
    article_count: int = Field(..., description="Article count at time of change")
    velocity: float = Field(..., description="Velocity at time of change")

class NarrativeResponse(BaseModel):
    """Response model for a narrative."""
    # ... existing fields ...
    lifecycle_state: Optional[str] = Field(default=None, description="New lifecycle state (emerging, rising, hot, cooling, dormant)")
    lifecycle_history: Optional[List[LifecycleHistoryEntry]] = Field(default=None, description="History of lifecycle state transitions")
    fingerprint: Optional[List[float]] = Field(default=None, description="Narrative fingerprint vector for similarity matching")
    # ... other fields ...
```

### 3. Data Normalization in API Endpoint

Added data normalization logic to handle database format differences:

- **Lifecycle History**: Convert datetime timestamps to ISO strings, rename `mention_velocity` to `velocity`
- **Fingerprint**: Extract `vector` field from dict format (old) or use list directly (new)

## Test Results

Created test script `context-owl-ui/src/test-narrative-api.ts` and ran against local backend:

```
✅ Received 5 narratives
✅ API is responding correctly
✅ TypeScript types match API response
✅ lifecycle_state field is present
✅ lifecycle_history field is present
⚠️  fingerprint field is NOT present (backend may not be returning it yet)
```

### Sample Narrative Data

```
Theme: Metaplanet
Title: Metaplanet's Crypto Treasury Troubles Amid Market Volatility
Entities: Metaplanet, Bitcoin
Article Count: 3
Mention Velocity: 164.61
Lifecycle: heating
Lifecycle State: hot
Momentum: growing
Recency Score: 0.21
Days Active: 1

Lifecycle History:
  1. rising @ 2025-10-15T23:54:46.023000 (3 articles, velocity: 1.5)
  2. hot @ 2025-10-16T00:10:44.724000 (3 articles, velocity: 270.37)

Peak Activity:
  Date: 2025-10-15
  Articles: 3
  Velocity: 1.5
```

## Findings

### ✅ Working Fields

1. **lifecycle_state**: Successfully returned from database and API
2. **lifecycle_history**: Successfully returned with proper normalization
   - Timestamps converted from datetime to ISO strings
   - `mention_velocity` renamed to `velocity` for consistency
3. **momentum**: Already present in API
4. **recency_score**: Already present in API
5. **entity_relationships**: Already present in API
6. **days_active**: Already present in API
7. **peak_activity**: Already present in API

### ⚠️ Missing Field

**fingerprint**: Not present in API response

**Root Cause**: The database contains the old action-based fingerprint format:
```python
{
  'nucleus_entity': '...',
  'top_actors': [...],
  'key_actions': [...],
  'timestamp': datetime(...)
}
```

The new format should be a simple list of floats (embedding vector):
```python
[0.123, 0.456, 0.789, ...]
```

**Action Required**: The fingerprint field needs to be backfilled with the new embedding-based format. The current database has the old action-based fingerprint structure which is incompatible with the new API schema.

## Next Steps

1. ✅ Frontend types updated to include all new fields
2. ✅ Backend API endpoint updated to return new fields
3. ✅ Data normalization added for lifecycle_history
4. ⚠️ **TODO**: Backfill fingerprint field with new embedding vector format
5. **TODO**: Deploy backend changes to development/production
6. **TODO**: Update frontend UI components to display lifecycle data

## Files Modified

- `context-owl-ui/src/types/index.ts` - Added new type definitions
- `src/crypto_news_aggregator/api/v1/endpoints/narratives.py` - Updated API response model and data normalization
- `context-owl-ui/src/test-narrative-api.ts` - Created test script (new file)

## Deployment Notes

The backend changes are backward compatible:
- All new fields are optional
- Old clients will continue to work
- New clients can access additional lifecycle data when available
- Fingerprint field will be null until backfill is complete
