# Entity Type Display Fix

## Issue
The frontend was displaying entity types like "CRYPTO_ENTITY" instead of proper, user-friendly labels like "Cryptocurrency", "Company", etc.

## Root Cause Analysis

### Data Flow
1. **LLM Extraction** (`src/crypto_news_aggregator/llm/anthropic.py`)
   - Claude returns detailed entity types: `cryptocurrency`, `blockchain`, `protocol`, `company`, `organization`, `event`, `concept`, `person`, `location`
   
2. **Entity Mentions Storage** (`src/crypto_news_aggregator/background/rss_fetcher.py`)
   - Entity types from LLM are stored as-is in `entity_mentions` collection
   
3. **Signal Calculation** (`src/crypto_news_aggregator/worker.py`)
   - Worker reads entity_type from `entity_mentions` and passes it to `signal_scores`
   
4. **API Response** (`src/crypto_news_aggregator/api/v1/endpoints/signals.py`)
   - API returns entity_type directly from `signal_scores`
   
5. **Frontend Display** (`context-owl-ui/src/pages/Signals.tsx`)
   - Frontend was using simple string replacement: `entity_type.replace(/_/g, ' ')`
   - This worked for snake_case but didn't provide proper capitalization or formatting

### What Was Happening
- If MongoDB had "CRYPTO_ENTITY" (which shouldn't happen with current LLM), it would display as "CRYPTO ENTITY"
- Proper LLM types like "cryptocurrency" would display as "cryptocurrency" (lowercase, not ideal)
- The display lacked visual distinction between different entity types

## Solution

### Frontend Improvements
Added two new formatter functions in `context-owl-ui/src/lib/formatters.ts`:

1. **`formatEntityType(entityType: string)`**
   - Maps technical entity types to user-friendly labels
   - Handles all expected types from the LLM
   - Falls back to smart capitalization for unknown types

2. **`getEntityTypeColor(entityType: string)`**
   - Returns Tailwind CSS classes for colored badges
   - Each entity type gets a distinct color scheme
   - Improves visual scanning and recognition

### Updated Display
Modified `context-owl-ui/src/pages/Signals.tsx`:
- Changed from plain text to colored badge display
- Uses `formatEntityType()` for proper labeling
- Uses `getEntityTypeColor()` for visual distinction

## Entity Type Mapping

| LLM Type | Display Label | Color |
|----------|---------------|-------|
| cryptocurrency | Cryptocurrency | Blue |
| blockchain | Blockchain | Purple |
| protocol | Protocol | Indigo |
| company | Company | Green |
| organization | Organization | Orange |
| event | Event | Red |
| concept | Concept | Gray |
| person | Person | Pink |
| location | Location | Teal |

## Testing

### Local Testing
```bash
cd context-owl-ui
npm run dev
```

Visit http://localhost:5173/signals and verify:
- Entity types display with proper capitalization
- Each type has a colored badge
- Unknown types fall back to smart formatting

### Production Verification
After deployment to Vercel:
1. Check https://context-owl-5zwt1nrjk-mikes-projects-92d90cb6.vercel.app/signals
2. Verify entity types display correctly
3. Check that colors render properly

## Notes

### Why Not Change Backend?
- The detailed entity types from the LLM are valuable metadata
- They provide more granular classification than simplified types
- Frontend formatting is more flexible and easier to iterate on
- No database migration needed

### Future Enhancements
- Add entity type filtering in the UI
- Group signals by entity type
- Add entity type icons alongside colors
- Create entity type legend/documentation

## Files Changed
- `context-owl-ui/src/lib/formatters.ts` - Added formatEntityType() and getEntityTypeColor()
- `context-owl-ui/src/pages/Signals.tsx` - Updated to use new formatters with badge display
