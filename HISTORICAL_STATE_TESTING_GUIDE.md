# Historical State Visualization - Testing Guide

## Quick Start

### Prerequisites
- Backend API running with narratives that have `lifecycle_history` data
- Frontend dev server running: `cd context-owl-ui && npm run dev`

### Test Steps

#### 1. Basic Functionality Test
```bash
# Start the frontend
cd context-owl-ui
npm run dev
```

1. Navigate to **Narratives** page
2. Click **Pulse** view button
3. Verify timeline scrubber appears
4. Verify narratives display with current lifecycle states

#### 2. Historical State Test
1. Drag the timeline scrubber to a past date
2. **Expected Results**:
   - Narrative lifecycle badges update to show historical states
   - If state has changed, amber badge appears: "was X, now Y"
   - Only narratives active on that date are shown
   - Results count updates: "X of Y narratives active on this date"

#### 3. State Transition Test
Look for narratives with transition badges:
- **Format**: "was {historical_state}, now {current_state}"
- **Color**: Amber background (#F59E0B)
- **Examples**:
  - "was Hot, now Cooling"
  - "was Rising, now Mature"
  - "was Emerging, now Hot"

#### 4. Tooltip Test
1. Hover over a narrative timeline bar
2. **Expected Tooltip Content**:
   ```
   Title: [Narrative Title]
   Start: [Date]
   Latest: [Date]
   Articles: [Count]
   Stage: [Historical State] (historical, now [Current State])
   Velocity: [Number] per day
   ```

#### 5. Reset Test
1. Select a historical date
2. Click **Reset to Current** button
3. **Expected Results**:
   - Timeline scrubber moves to current date
   - All narratives show current states
   - Transition badges disappear
   - Results count shows: "X total narratives"

## Test Scenarios

### Scenario 1: Narrative with Multiple State Changes
**Setup**: Find a narrative that has gone through multiple lifecycle states

**Test**:
1. Scrub to earliest date
2. Note the lifecycle state (e.g., "Emerging")
3. Scrub forward in time
4. Observe state changes (e.g., "Emerging" → "Rising" → "Hot" → "Cooling")

**Expected**:
- Icon and color change to match historical state
- Transition badge updates as you scrub
- Tooltip shows correct historical context

### Scenario 2: Narrative with No State Changes
**Setup**: Find a narrative that has maintained the same state

**Test**:
1. Scrub to different dates
2. Observe the lifecycle badge

**Expected**:
- Icon and color remain consistent
- No transition badge appears
- State shown matches current state

### Scenario 3: Narrative Without Lifecycle History
**Setup**: If backend returns narratives without `lifecycle_history` field

**Test**:
1. Scrub to any date
2. Observe the narrative display

**Expected**:
- Shows current lifecycle state
- No transition badge
- No errors in console
- Graceful fallback behavior

### Scenario 4: Edge Cases

#### Test 4a: Date Before Narrative Creation
1. Find a narrative's `first_seen` date
2. Scrub to a date before that
3. **Expected**: Narrative is filtered out (not shown)

#### Test 4b: Date After Latest Update
1. Scrub to current date
2. **Expected**: Shows current state, no transition badge

#### Test 4c: Date During State Transition
1. Find exact timestamp of a state change in lifecycle_history
2. Scrub to that date
3. **Expected**: Shows the new state (state after transition)

## Visual Verification Checklist

### Lifecycle State Icons
- [ ] ✨ Emerging - Blue icon and gradient
- [ ] 📈 Rising - Green icon and gradient
- [ ] 🔥 Hot - Orange icon and gradient
- [ ] ⚡ Heating - Red icon and gradient
- [ ] ⭐ Mature - Purple icon and gradient
- [ ] 💨 Cooling - Gray icon and gradient
- [ ] 💤 Dormant - Light gray icon and gradient

### Transition Badge
- [ ] Appears only when historical state differs from current
- [ ] Amber background color
- [ ] Format: "was X, now Y"
- [ ] Readable text color (dark amber)
- [ ] Proper spacing and padding

### Timeline Scrubber
- [ ] Smooth dragging interaction
- [ ] Selected date display updates
- [ ] Results count updates dynamically
- [ ] Reset button appears when date selected
- [ ] Reset button works correctly

## Browser Testing

### Desktop Browsers
- [ ] Chrome/Edge (Chromium)
- [ ] Firefox
- [ ] Safari

### Mobile Browsers (Responsive)
- [ ] Chrome Mobile
- [ ] Safari iOS
- [ ] Firefox Mobile

### Dark Mode
- [ ] Light theme displays correctly
- [ ] Dark theme displays correctly
- [ ] Transition badges readable in both modes

## Performance Testing

### Load Test
1. Navigate to Pulse view with 50+ narratives
2. Scrub through timeline rapidly
3. **Expected**:
   - No lag or stuttering
   - Smooth state updates
   - No memory leaks
   - Console remains error-free

### Data Volume Test
1. Test with varying narrative counts:
   - 10 narratives
   - 50 narratives
   - 100+ narratives
2. **Expected**: Consistent performance across all volumes

## API Data Verification

### Check Backend Response
```bash
# Fetch narratives and inspect lifecycle_history
curl http://localhost:8000/api/narratives | jq '.[0].lifecycle_history'
```

**Expected Structure**:
```json
[
  {
    "state": "emerging",
    "timestamp": "2025-10-01T12:00:00Z",
    "article_count": 3,
    "velocity": 1.5
  },
  {
    "state": "rising",
    "timestamp": "2025-10-05T14:30:00Z",
    "article_count": 8,
    "velocity": 2.8
  },
  {
    "state": "hot",
    "timestamp": "2025-10-10T09:15:00Z",
    "article_count": 15,
    "velocity": 4.2
  }
]
```

### Verify Data Quality
- [ ] `lifecycle_history` array exists
- [ ] Entries are sorted by timestamp (oldest to newest)
- [ ] All entries have required fields: `state`, `timestamp`, `article_count`, `velocity`
- [ ] Timestamps are valid ISO 8601 format
- [ ] States match known lifecycle values

## Console Debugging

### Enable Debug Logging
Add to `TimelineView.tsx` for debugging:
```typescript
console.log('Selected Date:', selectedDate);
console.log('Historical State:', getHistoricalLifecycleState(narrative, selectedDate));
```

### Common Issues

#### Issue 1: Transition Badge Not Appearing
**Debug**:
- Check if `lifecycle_history` exists in narrative data
- Verify historical state differs from current state
- Check console for errors

#### Issue 2: Wrong Historical State Shown
**Debug**:
- Verify `lifecycle_history` is sorted correctly
- Check date comparison logic
- Ensure timezone handling is correct

#### Issue 3: Performance Issues
**Debug**:
- Check number of narratives being rendered
- Profile React component re-renders
- Consider memoization for large datasets

## Acceptance Criteria

### Must Have ✅
- [x] Timeline scrubber passes selectedDate to TimelineView
- [x] Historical lifecycle state displayed when date selected
- [x] Transition badge shows when state has changed
- [x] Tooltip includes historical state information
- [x] Reset button returns to current view
- [x] No TypeScript errors
- [x] Build succeeds
- [x] Graceful fallback for missing lifecycle_history

### Should Have 🎯
- [ ] Smooth animations when scrubbing
- [ ] Responsive design works on mobile
- [ ] Dark mode styling consistent
- [ ] Performance optimized for 100+ narratives

### Nice to Have 💡
- [ ] Visual indicator on timeline bar showing state changes
- [ ] Expandable state history view
- [ ] Keyboard navigation support
- [ ] Animation playback mode

## Deployment Checklist

Before deploying to production:
- [ ] All tests pass
- [ ] No console errors
- [ ] Performance acceptable
- [ ] Cross-browser tested
- [ ] Mobile responsive verified
- [ ] Dark mode tested
- [ ] API integration verified
- [ ] Documentation updated
- [ ] Feature branch created
- [ ] PR submitted for review

## Rollback Plan

If issues arise in production:
1. Verify backend is returning `lifecycle_history` data
2. Check browser console for errors
3. If critical issue, revert PR
4. If minor issue, create hotfix branch

## Support Resources

### Documentation
- `HISTORICAL_STATE_VISUALIZATION.md` - Implementation details
- `HISTORICAL_STATE_EXAMPLE.md` - Visual examples
- `src/types/index.ts` - Type definitions

### Code References
- `context-owl-ui/src/components/TimelineView.tsx` - Main implementation
- `context-owl-ui/src/pages/Narratives.tsx` - Integration point
- `getHistoricalLifecycleState()` - Core lookup function
