# Historical State Visualization - Visual Example

## Feature Overview
When scrubbing the timeline to a past date, narratives display their lifecycle state from that historical date, with transition indicators showing how the state has changed.

## Visual Examples

### Example 1: Narrative State Transition
```
Timeline Scrubber: October 10, 2025 (selected date)

┌─────────────────────────────────────────────────────────────────┐
│ 🔥 Bitcoin ETF Approval                    (15 articles)        │
│    [was Hot, now Cooling]  🪙 Bitcoin  📊 ETF                   │
│                                                                  │
│ ████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

Explanation:
- 🔥 Icon shows the state was "Hot" on October 10
- Orange/red gradient bar indicates Hot state
- Amber badge "was Hot, now Cooling" shows the transition
- Current state is "Cooling" but not displayed as primary
```

### Example 2: No State Change
```
Timeline Scrubber: October 15, 2025 (selected date)

┌─────────────────────────────────────────────────────────────────┐
│ ✨ DeFi Protocol Launch                    (8 articles)         │
│    🪙 Ethereum  🔗 DeFi                                          │
│                                                                  │
│ ░░░░░░░░░░░░░░░░████████████████████████░░░░░░░░░░░░░░░░░░░░░  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

Explanation:
- ✨ Icon shows "Emerging" state
- Blue gradient bar indicates Emerging state
- No transition badge (state hasn't changed)
- This narrative was Emerging then and still is now
```

### Example 3: Multiple Transitions
```
Timeline Scrubber: October 5, 2025 (selected date)

┌─────────────────────────────────────────────────────────────────┐
│ 📈 Solana Network Upgrade                  (23 articles)        │
│    [was Rising, now Mature]  🪙 Solana  ⚡ Network              │
│                                                                  │
│ ░░░░░░░░████████████████████████████████████████████░░░░░░░░░  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

Explanation:
- 📈 Icon shows "Rising" state from October 5
- Green gradient bar indicates Rising state
- Amber badge shows transition to "Mature"
- Narrative has progressed through lifecycle stages
```

## Hover Tooltip Enhancement

### Before (Current State Only)
```
┌──────────────────────────┐
│ Bitcoin ETF Approval     │
│                          │
│ Start: Oct 1, 2025       │
│ Latest: Oct 16, 2025     │
│ Articles: 15             │
│ Stage: Cooling           │
│ Velocity: 2.3 per day    │
└──────────────────────────┘
```

### After (With Historical Context)
```
┌────────────────────────────────────────┐
│ Bitcoin ETF Approval                   │
│                                        │
│ Start: Oct 1, 2025                     │
│ Latest: Oct 16, 2025                   │
│ Articles: 15                           │
│ Stage: Hot (historical, now Cooling)   │
│ Velocity: 2.3 per day                  │
└────────────────────────────────────────┘
```

## Timeline Scrubber States

### State 1: No Date Selected (Default)
```
Timeline Filter
Showing all current narratives

[Oct 1] ═══════════════════════════════════○ [Oct 16]
                                            ↑
                                      (at current)

15 total narratives
```
- All narratives show their **current** lifecycle state
- No transition indicators

### State 2: Historical Date Selected
```
Timeline Filter
Showing narratives active on Oct 10, 2025     [Reset to Current]

[Oct 1] ═══════════════════○═══════════════ [Oct 16]
                            ↑
                      (Oct 10, 2025)

12 of 15 narratives active on this date
```
- Narratives show their **historical** lifecycle state from Oct 10
- Transition indicators appear for changed states
- Only narratives active on that date are shown

## Color Coding

### Lifecycle States with Colors
- **✨ Emerging** - Blue (#3B82F6)
- **📈 Rising** - Green (#10B981)
- **🔥 Hot** - Orange (#F97316)
- **⚡ Heating** - Red (#EF4444)
- **⭐ Mature** - Purple (#A855F7)
- **💨 Cooling** - Gray (#6B7280)
- **💤 Dormant** - Light Gray (#9CA3AF)

### Transition Indicator
- **Amber Badge** - (#F59E0B) - Shows state changes
- Format: "was {past_state}, now {current_state}"

## User Interaction Flow

1. **User opens Narratives page** → Sees current states
2. **User clicks Pulse view** → Timeline scrubber appears
3. **User drags scrubber left** → Date changes, states update
4. **User sees transition badges** → Understands state evolution
5. **User hovers over narrative** → Sees detailed historical info
6. **User clicks Reset** → Returns to current view

## Benefits

### For Users
- **Historical Context**: Understand how narratives evolved over time
- **State Transitions**: See which narratives gained or lost momentum
- **Trend Analysis**: Identify patterns in narrative lifecycle
- **Time Travel**: Explore what was hot at any point in time

### For Analysis
- **Momentum Tracking**: See which narratives are heating up vs cooling down
- **Peak Detection**: Identify when narratives reached their peak
- **Lifecycle Patterns**: Understand typical narrative evolution
- **Resurrection Detection**: Spot narratives that went dormant and came back

## Implementation Notes

### Data Requirements
- Requires `lifecycle_history` array in narrative data
- Each entry needs: `state`, `timestamp`, `article_count`, `velocity`
- Falls back gracefully if history is missing

### Performance
- Historical state lookup is O(n log n) per narrative
- Memoization could be added for large datasets
- Current implementation handles 100+ narratives smoothly

### Accessibility
- Color is not the only indicator (icons + text labels)
- Transition badges provide clear text description
- Tooltips enhance understanding without requiring them
