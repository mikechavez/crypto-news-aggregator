# Activity Heatmap Visual Guide

## What Users Will See

### Layout Structure
```
┌─────────────────────────────────────────────────────────────────┐
│ Timeline Filter                                    [Reset Button]│
│ Showing narratives active on Oct 15, 2025                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ Activity by Day                                                  │
│ ┌─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┐ │
│ │ │ │ │█│█│█│█│ │ │ │█│█│█│█│█│ │ │ │█│█│█│ │ │ │ │ │ │ │ │ │ │
│ │ │ │█│█│█│█│█│ │ │█│█│█│█│█│█│ │ │█│█│█│█│█│ │ │ │ │ │ │ │ │ │
│ │ │█│█│█│█│█│█│█│█│█│█│█│█│█│█│█│█│█│█│█│█│█│ │ │ │ │ │ │ │ │ │
│ │█│█│█│█│█│█│█│█│█│█│█│█│█│█│█│█│█│█│█│█│█│█│█│ │ │ │ │ │ │ │ │
│ └─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┘ │
│                                                                  │
│ Oct 1, 2025                                      Oct 30, 2025   │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                           ◉                                      │
│                      Oct 15, 2025                                │
│                                                                  │
│ 12 of 45 narratives active on this date                         │
└─────────────────────────────────────────────────────────────────┘
```

### Color Coding

The heatmap uses a gradient color system to indicate activity levels:

| Activity Level | Color | Visual Example | Description |
|---------------|-------|----------------|-------------|
| **No Activity (0%)** | Gray | `░` | No narratives active |
| **Low (1-25%)** | Light Orange | `▒` | Minimal activity |
| **Medium (25-50%)** | Medium Orange | `▓` | Moderate activity |
| **High (50-75%)** | Dark Orange | `█` | High activity |
| **Peak (75-100%)** | Red | `█` | Maximum activity |

### Interactive Behaviors

#### 1. Hover State
```
When hovering over a bar:
┌─────────────────────┐
│ Oct 15, 2025: 12    │ ← Tooltip appears
└─────────────────────┘
         ▼
        ┌─┐
        │█│ ← Bar slightly fades (opacity: 0.8)
        └─┘
```

#### 2. Selected State
```
When a bar is clicked:
        ┌─┐
        │█│ ← Blue ring appears around selected bar
        └─┘
         ◉  ← Timeline scrubber jumps to this date
```

#### 3. Click Action
```
User clicks bar → setSelectedDate(day.date) → Filters narratives → Updates timeline
```

## Real-World Example

### Scenario: Bitcoin ETF Approval Week

```
Activity by Day
┌─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┐
│ │ │ │ │█│█│█│█│█│█│ │ │ │ │  ← Peak activity during announcement
│ │ │ │█│█│█│█│█│█│█│█│ │ │ │
│ │ │█│█│█│█│█│█│█│█│█│█│ │ │
│ │█│█│█│█│█│█│█│█│█│█│█│█│ │
└─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┘
Jan 8  Jan 10  Jan 12  Jan 14  Jan 16

Color Intensity:
- Jan 8-9: Gray/Light Orange (pre-announcement, low activity)
- Jan 10-14: Orange to Red (ETF approval, peak activity)
- Jan 15-16: Light Orange (post-announcement, cooling down)
```

## User Benefits

1. **Quick Scanning**: Instantly see which dates had the most narrative activity
2. **Pattern Recognition**: Identify trends and spikes in crypto news coverage
3. **Efficient Navigation**: Click high-activity days to explore important events
4. **Context Awareness**: Understand the temporal distribution of narratives

## Technical Specifications

### Dimensions
- **Height**: 64px (h-16)
- **Gap**: 2px (gap-0.5)
- **Bar Width**: Auto-calculated (flex-1)
- **Min Bar Height**: 5% (for visibility)

### Styling Classes
```css
Container: flex items-end h-16 gap-0.5
Bar: flex-1 transition-all duration-200 rounded-t hover:opacity-80 relative group
Selected: ring-2 ring-blue-600 ring-offset-2
Tooltip: absolute bottom-full left-1/2 -translate-x-1/2 mb-2
```

### Color Classes
```css
No Activity: bg-gray-200 dark:bg-gray-700
Low (0-25%): bg-orange-200 dark:bg-orange-900/40
Medium (25-50%): bg-orange-300 dark:bg-orange-800/60
High (50-75%): bg-orange-400 dark:bg-orange-700/80
Peak (75-100%): bg-red-500 dark:bg-red-600
```

## Accessibility

- **Title Attribute**: Each bar has a title with date and count
- **Keyboard Navigation**: Bars are buttons, accessible via Tab key
- **Screen Readers**: Tooltip text provides context
- **Color Contrast**: Meets WCAG AA standards in both light and dark modes

## Performance

- **Memoization**: Activity calculation cached with `useMemo`
- **Efficient Rendering**: Only recalculates when narratives or date range changes
- **Smooth Animations**: CSS transitions for hover and selection states
- **Minimal Re-renders**: State updates isolated to date selection

## Integration with Timeline Scrubber

The heatmap works in tandem with the timeline scrubber below it:

1. **Heatmap**: Provides visual overview of activity distribution
2. **Scrubber**: Allows fine-grained date selection
3. **Both**: Update the same `selectedDate` state
4. **Result**: Filtered narratives shown in TimelineView component

This dual-control system gives users both macro (heatmap) and micro (scrubber) control over date filtering.
