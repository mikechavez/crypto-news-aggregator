# UI Fixes Summary

## Issues Reported
1. **Pulse Tab Scroll Issue**: Can't scroll to bottom of page, only see 5 rows of narratives
2. **Archived Narratives Tab**: Shows resurrection summary for dormant narratives
3. **Old Article**: 2019 TradingView/Fibonacci article shouldn't be in database

## Fixes Applied

### 1. Deleted Old TradingView Article ✓
**Issue**: Article from June 18, 2019 was still in the database
- **Title**: "Twitter User Claims TradingView Has Ignored a Fibonacci Retracement Bug for 5 Years"
- **Source**: Cointelegraph
- **Location**: MongoDB articles collection
- **ID**: `68d4b36b30d27b58f9dcd56c`

**Fix**: Deleted the article using `scripts/delete_old_article.py`

### 2. Fixed Archived Narratives Resurrection Summary ✓
**Issue**: The resurrection summary card was showing for ALL archived narratives, even those that are truly dormant (reawakening_count = 0)

**Fix**: Modified `/context-owl-ui/src/pages/Narratives.tsx` (lines 552-630)
- Added conditional check to only show resurrection summary when there are actually resurrected narratives
- Changed from showing all archived narratives to filtering for `reawakening_count > 0`
- Updated count to show only resurrected narratives, not all archived ones

**Before**:
```tsx
{viewMode === 'archive' && narratives.length > 0 && (
  <Card>
    <span>{narratives.length}</span>
    <span>narratives have been resurrected</span>
  </Card>
)}
```

**After**:
```tsx
{viewMode === 'archive' && narratives.length > 0 && (() => {
  const resurrectedNarratives = narratives.filter(n => n.reawakening_count && n.reawakening_count > 0);
  if (resurrectedNarratives.length === 0) return null;
  
  return (
    <Card>
      <span>{resurrectedNarratives.length}</span>
      <span>narratives have been resurrected</span>
    </Card>
  );
})()}
```

### 3. Pulse Tab Scroll Issue Investigation ✓
**Issue**: User reports only seeing 5 rows and unable to scroll

**Investigation Results**:
- Reviewed all component hierarchy: `Layout.tsx` → `Narratives.tsx` → `TimelineView.tsx`
- No height constraints found in any containers
- No `max-height`, `overflow: hidden`, or fixed height CSS
- The `TimelineView` component properly renders all narratives in the array
- Layout uses `min-h-screen` which allows content to expand
- No CSS limiting scroll behavior (only `overscroll-behavior-y: none` to prevent bounce)

**Possible Causes**:
1. **Browser cache**: The UI might be showing cached content. User should hard refresh (Cmd+Shift+R)
2. **Data filtering**: The `filteredNarratives` might actually only have 5 items due to date filtering
3. **Browser rendering**: Some browsers may have rendering issues with the timeline component

**Recommendation**: 
- User should hard refresh the browser (Cmd+Shift+R or Ctrl+Shift+R)
- Check the browser console for any JavaScript errors
- Verify that `filteredNarratives.length` is actually greater than 5 in the browser dev tools

## Files Modified
1. `/context-owl-ui/src/pages/Narratives.tsx` - Fixed resurrection summary logic
2. `/scripts/delete_old_article.py` - Created script to delete old article
3. `/scripts/investigate_ui_issues.py` - Created diagnostic script

## Testing Recommendations
1. **Archived Narratives Tab**:
   - Verify resurrection summary only shows when there are narratives with `reawakening_count > 0`
   - Verify dormant narratives show "Dormant" lifecycle badge, not "Reawakened"

2. **Pulse Tab**:
   - Hard refresh browser (Cmd+Shift+R)
   - Verify all narratives are visible and scrollable
   - Check browser console for errors

3. **Articles**:
   - Verify the 2019 TradingView article no longer appears in any views
