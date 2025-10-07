# Narrative Timeline Tracking Implementation

**Date:** 2025-10-06  
**Status:** ✅ Complete - Data infrastructure ready

## Overview

Implemented timeline tracking infrastructure for narratives to capture daily snapshots of narrative evolution. This enables future charting of narrative growth, velocity changes, and entity involvement over time.

## What Was Built

### 1. Database Schema Updates

**New fields added to narrative documents:**

```python
{
  "timeline_data": [
    {
      "date": "2025-10-06",           # ISO date string (YYYY-MM-DD)
      "article_count": 15,             # Articles on this day
      "entities": ["SEC", "Bitcoin"],  # Top entities (max 10)
      "velocity": 7.5                  # Articles per day rate
    }
  ],
  "peak_activity": {
    "date": "2025-10-05",              # Date of peak activity
    "article_count": 18,               # Highest article count
    "velocity": 4.2                    # Velocity at peak
  },
  "days_active": 6                     # Days since first_seen
}
```

### 2. Smart Daily Snapshot Logic

**File:** `src/crypto_news_aggregator/db/operations/narratives.py`

- **One snapshot per day:** Only appends new snapshot if date changes
- **Same-day updates:** Replaces last snapshot if updated multiple times in one day
- **Peak tracking:** Automatically updates `peak_activity` when article count exceeds previous peak
- **Days active:** Auto-calculates from `first_seen` timestamp

**Helper functions:**
- `_should_append_timeline_snapshot()` - Determines if new snapshot needed
- `_calculate_days_active()` - Calculates days since narrative started

### 3. API Endpoint

**New endpoint:** `GET /api/v1/narratives/{id}/timeline`

**Response:**
```json
[
  {
    "date": "2025-10-01",
    "article_count": 3,
    "entities": ["SEC", "Bitcoin"],
    "velocity": 1.5
  },
  {
    "date": "2025-10-02",
    "article_count": 5,
    "entities": ["SEC", "Bitcoin", "Coinbase"],
    "velocity": 2.5
  }
]
```

**Use case:** Perfect for charting narrative growth over time

### 4. Updated Response Models

**File:** `src/crypto_news_aggregator/api/v1/endpoints/narratives.py`

**New Pydantic models:**
- `TimelineSnapshot` - Single day snapshot
- `PeakActivity` - Peak metrics

**Updated `NarrativeResponse`:**
- Added `days_active: int`
- Added `peak_activity: Optional[PeakActivity]`

**Backward compatible:** Handles old narratives without timeline fields

## Test Coverage

**20 new tests added:**

### Database Tests (`tests/db/test_narrative_timeline.py`)
- ✅ Helper function tests (7 tests)
- ✅ Timeline creation and updates (4 tests)
- ✅ Peak activity tracking (1 test)
- ✅ Timeline retrieval (3 tests)

### API Tests (`tests/api/test_narrative_timeline_endpoint.py`)
- ✅ Timeline endpoint tests (4 tests)
- ✅ Response model validation (2 tests)

**All tests passing:** 20/20 ✅

## How It Works

### Daily Snapshot Flow

1. **Narrative detection runs** (via `detect_narratives()`)
2. **For each narrative:**
   - Check if narrative exists in DB
   - Create today's snapshot with current metrics
   - If new day: append to `timeline_data`
   - If same day: replace last snapshot
   - Update `peak_activity` if count increased
   - Calculate `days_active` from `first_seen`

### Example Timeline Evolution

**Day 1 (2025-10-01):**
```json
{
  "timeline_data": [
    {"date": "2025-10-01", "article_count": 3, "velocity": 1.5}
  ],
  "peak_activity": {"date": "2025-10-01", "article_count": 3},
  "days_active": 1
}
```

**Day 2 (2025-10-02):**
```json
{
  "timeline_data": [
    {"date": "2025-10-01", "article_count": 3, "velocity": 1.5},
    {"date": "2025-10-02", "article_count": 5, "velocity": 2.5}
  ],
  "peak_activity": {"date": "2025-10-02", "article_count": 5},
  "days_active": 2
}
```

**Day 2 (later same day):**
```json
{
  "timeline_data": [
    {"date": "2025-10-01", "article_count": 3, "velocity": 1.5},
    {"date": "2025-10-02", "article_count": 7, "velocity": 3.5}  // Updated
  ],
  "peak_activity": {"date": "2025-10-02", "article_count": 7},
  "days_active": 2
}
```

## Data Collection Strategy

**Starting now:** Timeline data begins accumulating automatically
**After 7 days:** Sufficient data for meaningful charts
**No UI yet:** Data infrastructure only - charting comes later

## API Usage Examples

### Get Active Narratives (with timeline fields)
```bash
curl http://localhost:8000/api/v1/narratives/active?limit=10
```

Response includes new fields:
```json
{
  "theme": "regulatory",
  "title": "SEC Enforcement Actions",
  "days_active": 5,
  "peak_activity": {
    "date": "2025-10-05",
    "article_count": 18,
    "velocity": 4.2
  }
}
```

### Get Timeline for Specific Narrative
```bash
curl http://localhost:8000/api/v1/narratives/{narrative_id}/timeline
```

Returns array of daily snapshots for charting.

## Next Steps (Future Work)

### Phase 1: Data Collection (Current)
- ✅ Timeline infrastructure implemented
- ✅ Daily snapshots collecting automatically
- ⏳ Wait 7 days for meaningful data

### Phase 2: Visualization (After 7 days)
- [ ] Add timeline chart component to UI
- [ ] Show narrative growth over time
- [ ] Visualize velocity changes
- [ ] Display entity evolution
- [ ] Add trend indicators (↑ growing, ↓ declining)

### Phase 3: Analytics (Future)
- [ ] Narrative lifecycle predictions
- [ ] Anomaly detection (sudden spikes)
- [ ] Comparative timeline views
- [ ] Export timeline data

## Files Modified

### Core Logic
- `src/crypto_news_aggregator/db/operations/narratives.py` - Timeline tracking logic
- `src/crypto_news_aggregator/api/v1/endpoints/narratives.py` - API endpoint + models

### Tests
- `tests/db/test_narrative_timeline.py` - Database operations tests
- `tests/api/test_narrative_timeline_endpoint.py` - API endpoint tests

## Technical Notes

### Performance
- Timeline data stored as array in MongoDB (efficient)
- No additional queries needed for timeline retrieval
- Snapshots limited to 10 entities to control size

### Data Retention
- Timeline data persists with narrative
- Old narratives cleaned up by existing `delete_old_narratives()` function
- No separate cleanup needed for timeline data

### Backward Compatibility
- Old narratives without timeline fields handled gracefully
- API returns defaults: `days_active=1`, `peak_activity=None`
- No migration needed - fields added on next update

## Deployment Notes

**No special deployment steps required:**
- Schema changes are additive (no breaking changes)
- Existing narratives continue working
- Timeline data starts accumulating on next narrative detection run
- No database migration needed

**Monitor after deployment:**
- Check narrative detection runs successfully
- Verify timeline_data arrays are populating
- Confirm daily snapshots append correctly

---

**Implementation complete!** 🎉  
Timeline data will begin accumulating automatically. Check back in 7 days for charting implementation.
