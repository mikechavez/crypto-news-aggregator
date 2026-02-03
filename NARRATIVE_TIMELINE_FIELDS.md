# Narrative Timeline Fields Documentation

## Overview
Documentation of timeline-related fields in the narratives API endpoint and MongoDB collection.

**API Endpoint**: `/api/v1/narratives/`  
**Database**: MongoDB `narratives` collection  
**Response Model**: `NarrativeResponse` (Pydantic)

---

## Timeline Fields Summary

### Primary Timestamp Fields

| Field | Type | Description | Included in API | Example |
|-------|------|-------------|-----------------|---------|
| `first_seen` | string (ISO) | When narrative was first detected | ✅ All endpoints | `"2025-10-01T19:30:00Z"` |
| `last_updated` | string (ISO) | Last update timestamp | ✅ All endpoints | `"2025-10-06T14:20:00Z"` |
| `reawakened_from` | string (ISO) | When narrative went dormant before reactivation | ✅ All endpoints | `"2025-09-28T10:15:00Z"` |

**Fallbacks**:
- `first_seen` falls back to `created_at` if missing
- `last_updated` falls back to `updated_at` if missing

---

### Derived Timeline Fields

| Field | Type | Description | Included in API | Example |
|-------|------|-------------|-----------------|---------|
| `days_active` | integer | Number of days narrative has been active | ✅ All endpoints | `6` |

**Calculation**: `max(1, (now - first_seen).days + 1)`

---

### Peak Activity Tracking

**Field**: `peak_activity` (object, optional)

```typescript
{
  date: string;           // Date of peak (YYYY-MM-DD)
  article_count: number;  // Articles at peak
  velocity: number;       // Velocity at peak
}
```

**Included**: ✅ All endpoints  
**Example**:
```json
{
  "date": "2025-10-05",
  "article_count": 18,
  "velocity": 4.2
}
```

---

### Timeline Snapshots (Heavy Field)

**Field**: `timeline_data` (array)

```typescript
Array<{
  date: string;           // Date (YYYY-MM-DD)
  article_count: number;  // Articles on this day
  entities: string[];     // Top entities (max 10)
  velocity: number;       // Articles per day rate
}>
```

**Included**: 
- ❌ Excluded from `/active` and `/archived` (performance)
- ✅ Available via `/narratives/{id}/timeline` endpoint

**Update Frequency**: Once per day (UTC)

---

### Lifecycle History (Heavy Field)

**Field**: `lifecycle_history` (array, optional)

```typescript
Array<{
  state: string;          // emerging, rising, hot, cooling, dormant
  timestamp: string;      // ISO timestamp
  article_count: number;  // Count at transition
  velocity: number;       // Velocity at transition
}>
```

**Included**:
- ❌ Excluded from `/active` endpoint (performance)
- ✅ Included in `/archived` and `/resurrections` endpoints
- ✅ Included in `/narratives/{id}` endpoint

---

## API Endpoint Projection Summary

### `/active` Endpoint (Lines 201-222)
**Included Fields**:
- ✅ `first_seen`, `last_updated`, `days_active`, `peak_activity`
- ✅ `reawakening_count`, `reawakened_from`, `resurrection_velocity`

**Excluded Fields** (for performance):
- ❌ `timeline_data`
- ❌ `lifecycle_history`
- ❌ `fingerprint`

### `/archived` Endpoint
**Included Fields**:
- ✅ All timestamp fields
- ✅ `lifecycle_history` (full)
- ✅ `fingerprint`

### `/resurrections` Endpoint
**Included Fields**:
- ✅ All timestamp fields
- ✅ `lifecycle_history` (full)
- ✅ `fingerprint`

### `/narratives/{id}` Endpoint
**Included Fields**:
- ✅ All fields including heavy fields

### `/narratives/{id}/timeline` Endpoint
**Returns**: Full `timeline_data` array only

---

## Database Schema (MongoDB)

**Collection**: `narratives`

**Timestamp Fields**:
```javascript
{
  first_seen: ISODate,        // When first detected
  last_updated: ISODate,      // Last update
  created_at: ISODate,        // Legacy field (fallback)
  updated_at: ISODate,        // Legacy field (fallback)
  reawakened_from: ISODate,   // Resurrection tracking
  
  days_active: Number,        // Calculated field
  
  peak_activity: {
    date: String,             // YYYY-MM-DD
    article_count: Number,
    velocity: Number
  },
  
  timeline_data: [{
    date: String,             // YYYY-MM-DD
    article_count: Number,
    entities: [String],
    velocity: Number
  }],
  
  lifecycle_history: [{
    state: String,
    timestamp: ISODate,
    article_count: Number,
    velocity: Number
  }]
}
```

---

## Key Implementation Details

### Timeline Snapshot Logic (Lines 13-43 in operations/narratives.py)
- Snapshots are appended **once per day** (UTC)
- If snapshot already exists for today, it's **updated** (not duplicated)
- Function: `_should_append_timeline_snapshot()`

### Days Active Calculation (Lines 46-61)
- Formula: `max(1, (now - first_seen).days + 1)`
- Minimum value: 1 (counts partial days)
- Function: `_calculate_days_active()`

### Peak Activity Tracking (Lines 145-152)
- Updated when `article_count > peak_activity.article_count`
- Stores date, count, and velocity at peak

---

## Usage Recommendations

### For Timeline Visualization
1. Use `/narratives/{id}/timeline` to fetch full `timeline_data`
2. Parse `date` field for x-axis
3. Use `article_count` or `velocity` for y-axis

### For Activity Heatmap
1. Fetch `timeline_data` for selected narratives
2. Group by date across narratives
3. Aggregate `article_count` or `velocity`

### For Lifecycle Tracking
1. Use `lifecycle_history` from `/archived` or `/resurrections` endpoints
2. Plot state transitions over time
3. Correlate with `article_count` and `velocity`

### For Performance
- Use `/active` endpoint for list views (excludes heavy fields)
- Fetch individual narrative details on-demand via `/narratives/{id}`
- Cache timeline data client-side (1-minute TTL on server)

---

## Related Files

- **API Endpoints**: `src/crypto_news_aggregator/api/v1/endpoints/narratives.py`
- **Database Operations**: `src/crypto_news_aggregator/db/operations/narratives.py`
- **Response Models**: Lines 76-147 in `narratives.py`
