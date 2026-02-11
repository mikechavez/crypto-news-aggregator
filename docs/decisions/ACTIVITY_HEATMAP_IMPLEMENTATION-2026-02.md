# Activity Heatmap Implementation

## Overview
Added an activity heatmap visualization above the timeline scrubber in the Narratives page (pulse view) to help users identify dates with high narrative activity.

## Implementation Details

### Location
- **File**: `context-owl-ui/src/pages/Narratives.tsx`
- **View**: Pulse view only (above timeline scrubber)

### Features Implemented

#### 1. Activity Calculation
- **Function**: `activityByDay` useMemo hook (lines 84-115)
- Iterates through each day in the date range
- Counts narratives active on each day (where day falls between `first_seen` and `last_updated`)
- Returns array of `{ date, count }` objects

#### 2. Color Gradient System
- **Function**: `getActivityColor` (lines 144-154)
- Implements gradient from gray (low activity) to red/orange (high activity)
- Color scale:
  - 0% activity: Gray (`bg-gray-200 dark:bg-gray-700`)
  - <25% activity: Light orange (`bg-orange-200 dark:bg-orange-900/40`)
  - 25-50% activity: Medium orange (`bg-orange-300 dark:bg-orange-800/60`)
  - 50-75% activity: Dark orange (`bg-orange-400 dark:bg-orange-700/80`)
  - 75-100% activity: Red (`bg-red-500 dark:bg-red-600`)

#### 3. Heatmap Visualization
- **Location**: Lines 245-278
- **Layout**: Horizontal bar chart with `h-16` height
- **Styling**: 
  - Flex layout with `gap-0.5` between bars
  - Bars aligned to bottom with `items-end`
  - Each bar is `flex-1` for equal width distribution
- **Height**: Proportional to activity count (minimum 5% for visibility)

#### 4. Interactive Features
- **Clickable bars**: Click any bar to jump to that date
- **Visual feedback**:
  - Hover effect: `hover:opacity-80`
  - Selected state: Blue ring (`ring-2 ring-blue-600`)
  - Smooth transitions: `transition-all duration-200`
- **Tooltips**: 
  - Show on hover with date and narrative count
  - Positioned above bars with dark background
  - Fade in/out with `opacity-0 group-hover:opacity-100`

#### 5. Label
- **Text**: "Activity by Day"
- **Styling**: Small semibold font in gray
- **Position**: Above the heatmap bars

### User Experience

1. **Visual Scanning**: Users can quickly identify high-activity periods by color intensity
2. **Date Navigation**: Click any bar to filter narratives to that specific date
3. **Context**: Tooltip provides exact count on hover
4. **Selection Feedback**: Selected date is highlighted with a ring
5. **Integration**: Works seamlessly with existing timeline scrubber below

### Technical Considerations

- **Performance**: Uses `useMemo` for efficient recalculation only when narratives or date range changes
- **Accessibility**: Includes `title` attributes for screen readers
- **Dark Mode**: Full support with dark mode color variants
- **Responsive**: Bars automatically resize based on container width

## Testing Recommendations

1. **Visual Testing**:
   - Verify gradient colors display correctly
   - Check bar heights are proportional to activity
   - Confirm tooltips appear on hover

2. **Interaction Testing**:
   - Click bars to verify date selection
   - Check selected state visual feedback
   - Test with various date ranges

3. **Edge Cases**:
   - Empty narratives array
   - Single day date range
   - All days with zero activity
   - Very long date ranges (many bars)

## Future Enhancements

- Add animation when bars first render
- Show mini sparkline of activity trend
- Add legend explaining color scale
- Support for custom date range selection
- Export heatmap data as CSV
