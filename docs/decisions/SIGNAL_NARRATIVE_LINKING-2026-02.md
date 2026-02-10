# Signal-to-Narrative Linking Implementation

**Status**: ✅ Complete  
**Date**: 2025-10-06

## Overview

Implemented linking between signals and narratives to provide users with context about whether a trending entity is part of an established narrative or an emerging signal.

## Changes Made

### 1. Backend: Signal Service (`signal_service.py`)

**Added `get_narratives_for_entity()` function:**
- Queries the narratives collection for narratives containing a specific entity
- Returns list of narrative ObjectIds as strings

**Updated `calculate_signal_score()` function:**
- Now queries narratives for each entity
- Adds `narrative_ids` array to return value
- Adds `is_emerging` boolean flag (true if narrative_ids is empty)

### 2. Backend: Database Operations (`signal_scores.py`)

**Updated `upsert_signal_score()` function:**
- Added `narrative_ids` parameter (List[str])
- Added `is_emerging` parameter (bool)
- Both fields are stored in MongoDB signal_scores collection

**Updated worker.py:**
- Modified signal score upsert call to pass narrative_ids and is_emerging from signal_data

### 3. Backend: API Endpoint (`signals.py`)

**Added `get_narrative_details()` helper function:**
- Fetches full narrative details (id, title, theme, lifecycle) for a list of narrative IDs
- Handles ObjectId conversion and error cases

**Updated `/api/v1/signals/trending` endpoint:**
- Fetches narrative details for each signal
- Response now includes:
  - `is_emerging`: boolean flag
  - `narratives`: array of narrative summaries with id, title, theme, lifecycle

### 4. Frontend: TypeScript Types (`types/index.ts`)

**Added `NarrativeSummary` interface:**
```typescript
export interface NarrativeSummary {
  id: string;
  title: string;
  theme: string;
  lifecycle: string;
}
```

**Updated `Signal` interface:**
- Added `is_emerging: boolean`
- Added `narratives: NarrativeSummary[]`

### 5. Frontend: Formatters (`lib/formatters.ts`)

**Added theme formatting functions:**
- `formatTheme()`: Maps technical theme names to user-friendly labels
- `getThemeColor()`: Returns Tailwind CSS classes for theme badge styling

### 6. Frontend: Signals Page (`pages/Signals.tsx`)

**Added narrative context section to each signal card:**

**For emerging signals (not in any narrative):**
```
🆕 Emerging
Not yet part of any narrative
```

**For signals in narratives:**
```
Part of:
[Regulatory] [Institutional] [DeFi Adoption]
```
- Clickable theme badges
- Clicking navigates to /narratives page
- Color-coded by theme
- Shows narrative title on hover

## Data Flow

1. **Signal Calculation** (worker.py):
   - Entity mentions are analyzed
   - `calculate_signal_score()` queries narratives collection
   - Returns signal data with narrative_ids and is_emerging

2. **Storage** (signal_scores collection):
   ```json
   {
     "entity": "Bitcoin",
     "score": 8.5,
     "narrative_ids": ["507f1f77bcf86cd799439011", "507f191e810c19729de860ea"],
     "is_emerging": false
   }
   ```

3. **API Response** (/api/v1/signals/trending):
   ```json
   {
     "signals": [{
       "entity": "Bitcoin",
       "signal_score": 8.5,
       "is_emerging": false,
       "narratives": [
         {
           "id": "507f1f77bcf86cd799439011",
           "title": "SEC Enforcement Actions",
           "theme": "regulatory",
           "lifecycle": "hot"
         }
       ]
     }]
   }
   ```

4. **UI Display**:
   - Shows "🆕 Emerging" badge if `is_emerging === true`
   - Shows clickable theme badges if narratives array has items
   - Provides context for understanding signal significance

## Testing

Created `tests/services/test_signal_narrative_linking.py`:
- ✅ Verifies signal_score includes narrative_ids field
- ✅ Verifies signal_score includes is_emerging field
- ✅ Validates data types are correct

## Benefits

1. **User Context**: Users can see if a signal is part of a known narrative or truly emerging
2. **Navigation**: Clickable badges allow users to explore related narratives
3. **Visual Clarity**: Color-coded theme badges make it easy to scan signal context
4. **Early Detection**: "Emerging" badge highlights potentially new trends before they form narratives

## Future Enhancements

- Add entity detail pages that show all narratives containing that entity
- Filter signals by narrative theme
- Show narrative lifecycle stage in signal cards
- Add "View Narrative" link that deep-links to specific narrative

## Files Modified

**Backend:**
- `src/crypto_news_aggregator/services/signal_service.py`
- `src/crypto_news_aggregator/db/operations/signal_scores.py`
- `src/crypto_news_aggregator/api/v1/endpoints/signals.py`
- `src/crypto_news_aggregator/worker.py`

**Frontend:**
- `context-owl-ui/src/types/index.ts`
- `context-owl-ui/src/lib/formatters.ts`
- `context-owl-ui/src/pages/Signals.tsx`

**Tests:**
- `tests/services/test_signal_narrative_linking.py`

## Deployment Notes

- No database migration required (MongoDB is schemaless)
- Existing signal_scores documents will have empty narrative_ids arrays
- Next signal calculation run will populate the new fields
- Frontend gracefully handles missing fields with optional chaining
