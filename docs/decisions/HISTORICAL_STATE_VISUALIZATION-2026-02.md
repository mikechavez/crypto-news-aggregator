# Historical State Visualization Implementation

## Overview
Implemented historical lifecycle state visualization for the timeline scrubber in the Pulse view. When users scrub to a past date, narratives now display their lifecycle state from that date, not their current state.

## Changes Made

### 1. TimelineView Component (`context-owl-ui/src/components/TimelineView.tsx`)

#### Added Props
- **`TimelineViewProps.selectedDate`**: Optional `Date | null` prop to receive the selected date from the timeline scrubber
- **`TimelineRowProps.selectedDate`**: Passed down to individual timeline rows

#### New Helper Function
```typescript
getHistoricalLifecycleState(narrative: Narrative, selectedDate: Date): { state: string; isHistorical: boolean }
```
- Searches through `narrative.lifecycle_history` to find the most recent state entry before or on the selected date
- Returns the historical state and a flag indicating if it differs from the current state
- Handles edge cases:
  - No lifecycle history: returns current state
  - Selected date before all history entries: returns earliest state
  - Selected date after all history entries: returns most recent historical state

#### Enhanced Lifecycle Display
- **Historical State Badge**: Shows the lifecycle state that was active on the selected date
- **State Transition Indicator**: When historical state differs from current state, displays an amber badge showing:
  - Format: "was {historical_state}, now {current_state}"
  - Example: "was Hot, now Cooling"
- **Tooltip Enhancement**: Hover tooltip also shows historical state with transition info

#### Lifecycle Config Updates
- Added `label` property to all lifecycle states for consistent display
- Added `dormant` state configuration for complete lifecycle coverage

### 2. Narratives Page (`context-owl-ui/src/pages/Narratives.tsx`)

#### Updated TimelineView Usage
```typescript
<TimelineView narratives={filteredNarratives || []} selectedDate={selectedDate} />
```
- Passes the `selectedDate` state from the timeline scrubber to the TimelineView component

## User Experience

### Timeline Scrubber Behavior
1. **Default State**: When no date is selected, narratives show their current lifecycle state
2. **Historical View**: When user scrubs to a past date:
   - Each narrative displays the lifecycle state it had on that date
   - If the state has changed since then, an amber badge shows the transition
   - Example: A narrative that was "Hot" on the selected date but is now "Cooling" will show:
     - Icon and color for "Hot" state
     - Badge: "was Hot, now Cooling"

### Visual Indicators
- **Historical State Icon**: Uses the icon and color scheme of the historical state
- **Transition Badge**: Amber-colored badge with format "was X, now Y"
- **Tooltip**: Shows historical state with note about current state if different

## Technical Details

### Lifecycle History Structure
The implementation relies on the `lifecycle_history` field in the Narrative type:
```typescript
interface LifecycleHistoryEntry {
  state: string;              // Lifecycle state (emerging, rising, hot, cooling, dormant)
  timestamp: string;          // ISO timestamp when state changed
  article_count: number;      // Article count at time of change
  velocity: number;           // Velocity at time of change
}
```

### State Lookup Algorithm
1. Filter lifecycle history entries to those on or before the selected date
2. Sort by timestamp descending (most recent first)
3. Take the first entry (most recent before selected date)
4. Compare with current state to determine if historical
5. Return historical state and transition flag

### Edge Case Handling
- **No lifecycle history**: Falls back to current state, no transition indicator
- **Date before all history**: Uses earliest historical state
- **Missing state config**: Falls back to "emerging" configuration

## Testing Recommendations

### Manual Testing
1. Navigate to Narratives page → Pulse view
2. Use timeline scrubber to select different dates
3. Verify:
   - Lifecycle badges update to show historical states
   - Transition indicators appear when states differ
   - Tooltips show correct historical information
   - Visual styling is consistent across all states

### Test Scenarios
- **Scenario 1**: Narrative with multiple state transitions
  - Expected: Shows correct state for each date in timeline
- **Scenario 2**: Narrative with no lifecycle history
  - Expected: Shows current state, no transition indicator
- **Scenario 3**: Selected date before narrative creation
  - Expected: Narrative filtered out by existing date filter
- **Scenario 4**: Selected date during state transition
  - Expected: Shows the state that was active at that moment

## Future Enhancements

### Potential Improvements
1. **Animation**: Smooth transitions when scrubbing through dates
2. **State Timeline**: Visual indicator on timeline bar showing when state changes occurred
3. **Detailed History**: Expandable view showing all state transitions with timestamps
4. **Performance**: Memoize historical state lookups for large datasets

### Related Features
- Could extend to show historical article counts, velocity, and other metrics
- Could add "playback" mode to animate through timeline automatically
- Could integrate with entity mention history for deeper insights

## Dependencies
- No new dependencies added
- Uses existing `date-fns` library for date parsing and comparison
- Leverages existing TypeScript types from `src/types/index.ts`

## Validation
- ✅ TypeScript compilation successful (no errors)
- ✅ All existing tests pass
- ✅ Props correctly typed and passed through component hierarchy
- ✅ Backward compatible with narratives lacking lifecycle_history

## Files Modified
1. `context-owl-ui/src/components/TimelineView.tsx` - Core implementation
2. `context-owl-ui/src/pages/Narratives.tsx` - Props integration
