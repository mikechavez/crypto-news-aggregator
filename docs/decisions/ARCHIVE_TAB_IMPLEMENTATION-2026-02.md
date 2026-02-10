# Archive Tab Implementation

## Overview
Added a third tab to the Narratives page for viewing dormant and resurrected narratives. The Archive tab displays narratives that have been reactivated from dormant state in the past 7 days.

## Changes Made

### 1. API Client (`context-owl-ui/src/api/narratives.ts`)

#### Added `getResurrectedNarratives` Function
```typescript
getResurrectedNarratives: async (limit: number = 20, days: number = 7): Promise<NarrativesResponse> => {
  return apiClient.get<NarrativesResponse>(`/api/v1/narratives/resurrections?limit=${limit}&days=${days}`);
}
```
- **Parameters**: 
  - `limit`: Number of narratives to fetch (default: 20)
  - `days`: Lookback window in days (default: 7)
- **Endpoint**: `/api/v1/narratives/resurrections`

### 2. Narratives Page (`context-owl-ui/src/pages/Narratives.tsx`)

#### Updated View Mode State
- Changed from `'cards' | 'pulse'` to `'cards' | 'pulse' | 'archive'`
- Added `viewMode` to the query key for proper cache management

#### Updated Data Fetching Logic
```typescript
queryFn: () => viewMode === 'archive' 
  ? narrativesAPI.getResurrectedNarratives(20, 7) 
  : narrativesAPI.getNarratives()
```
- Conditionally fetches from resurrections endpoint when in archive mode
- Maintains 60-second refetch interval

#### Added Archive Icon Import
- Imported `Archive` icon from `lucide-react`

#### Added Third Toggle Button
- Label: "Archive"
- Icon: Archive icon from lucide-react
- Active state: Blue background (`bg-blue-600`)
- Inactive state: Gray background with hover effect

#### Dynamic Page Header
- **Archive Mode**: "Archived Narratives" with description "Dormant narratives that have been reactivated in the past 7 days"
- **Other Modes**: "Emerging Narratives" with original description

#### Special Styling for Archived Narratives
When `viewMode === 'archive'`:
- **Card Border**: 2px purple border (`border-2 border-purple-300 dark:border-purple-700`)
- **Card Background**: Purple tinted background (`bg-purple-50/30 dark:bg-purple-900/10`)
- **Archive Icon**: Purple Archive icon displayed next to the title (`text-purple-600 dark:text-purple-400`)

## UI Behavior

### Archive Tab Features
1. **Card View Only**: Archive mode displays narratives in card view (not timeline)
2. **Visual Distinction**: Purple-themed styling clearly indicates archived status
3. **Archive Icon**: Each archived narrative shows an Archive icon next to its title
4. **Same Card Structure**: Maintains all existing card features (lifecycle badges, article count, expandable articles, etc.)

### View Mode Toggle
```
[Cards] [Pulse] [Archive]
```
- Three buttons with consistent styling
- Active button highlighted in blue
- Smooth transitions between modes

## Data Flow

1. User clicks "Archive" button
2. `viewMode` state updates to `'archive'`
3. React Query refetches data using `getResurrectedNarratives(20, 7)`
4. API calls `/api/v1/narratives/resurrections?limit=20&days=7`
5. Resurrected narratives displayed in card view with purple styling

## Integration Points

- **Backend API**: `/api/v1/narratives/resurrections` endpoint (implemented in RESURRECTIONS_API_IMPLEMENTATION.md)
- **Query Caching**: Separate cache keys for each view mode (`['narratives', viewMode]`)
- **Auto-refresh**: 60-second polling for all modes including archive

## Testing Recommendations

1. **Toggle Between Modes**: Verify smooth transitions between Cards, Pulse, and Archive
2. **Archive Styling**: Confirm purple border, background, and icon appear correctly
3. **Data Fetching**: Verify correct endpoint is called for each mode
4. **Empty State**: Test behavior when no resurrected narratives exist
5. **Dark Mode**: Verify purple styling works in both light and dark themes
6. **Responsive Design**: Test on mobile and desktop viewports

## Future Enhancements

Potential improvements for the Archive tab:
- Add filter controls for `limit` and `days` parameters
- Display resurrection metrics (reawakening_count, resurrection_velocity)
- Add "Reawakened from" timestamp display
- Sort options (by reawakening date, article count, etc.)
- Export archived narratives functionality
