# Lifecycle Badge Visibility Improvements

## Summary
Enhanced the visibility of all lifecycle state badges (Rising, Emerging, Cooling, etc.) to match the Hot badge's prominent gradient styling.

## Changes Made

### 1. Updated Narratives.tsx Card Component
**File**: `context-owl-ui/src/pages/Narratives.tsx` (lines 675-704)

Applied gradient backgrounds with white text and glow shadows to all lifecycle badges:

- **Emerging**: Blue to Indigo gradient (`from-blue-500 to-indigo-500`)
- **Rising**: Green to Emerald gradient (`from-green-500 to-emerald-500`)
- **Hot**: Orange to Red gradient (`from-orange-500 to-red-500`) - already existed
- **Heating**: Red to Pink gradient (`from-red-500 to-pink-500`)
- **Mature**: Purple to Violet gradient (`from-purple-500 to-violet-500`)
- **Cooling**: Gray to Slate gradient (`from-gray-500 to-slate-500`)

Each badge now includes:
- White text for maximum contrast
- Gradient background with appropriate colors
- Subtle glow shadow effect (`shadow-lg shadow-{color}-500/50`)
- Icon with white drop-shadow for enhanced visibility

### 2. Updated TimelineView Modal Badge
**File**: `context-owl-ui/src/components/TimelineView.tsx` (lines 259-276)

Applied the same gradient styling to the lifecycle badge in the expanded narrative modal view to maintain consistency across the UI.

## Visual Impact

### Before
- Rising, Emerging, Cooling badges had low-opacity backgrounds with colored text
- Badges were hard to see, especially in dark mode
- Inconsistent styling compared to Hot badge

### After
- All badges now have vibrant gradient backgrounds
- White text provides excellent contrast and readability
- Consistent visual treatment across all lifecycle states
- Glow effects make badges stand out without being overwhelming
- Icons have subtle white drop-shadow for enhanced visibility

## Color Scheme Rationale

- **Emerging (Blue)**: Represents new, fresh narratives
- **Rising (Green)**: Indicates growth and positive momentum
- **Hot (Orange-Red)**: Signals peak activity and urgency
- **Heating (Red-Pink)**: Shows intensifying activity
- **Mature (Purple)**: Represents established, stable narratives
- **Cooling (Gray)**: Indicates declining activity

## Testing

To verify the changes:
1. Navigate to the Narratives page
2. Check that all lifecycle badges are clearly visible
3. Verify badges in both light and dark mode
4. Click on a narrative in Pulse view to see the modal badge styling
5. Confirm all badges have consistent gradient styling

## Technical Notes

- Used explicit gradient class strings instead of dynamic Tailwind classes to ensure proper compilation
- Applied consistent padding, border-radius, and shadow effects
- Maintained backward compatibility with both `lifecycle_state` and `lifecycle` field names
- Icon drop-shadow effect uses `drop-shadow-[0_0_3px_rgba(255,255,255,0.8)]` for subtle glow
