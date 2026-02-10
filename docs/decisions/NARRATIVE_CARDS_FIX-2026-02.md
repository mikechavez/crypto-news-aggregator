# Narrative Cards UI Fixes

## Summary
Fixed three critical issues in the Narratives Cards tab:
1. **Cards not clickable** - Added onClick handler to expand/collapse article details
2. **Hot icon poor visibility** - Enhanced flame icon with gradient background and glow effect
3. **Inflated velocity numbers** - Fixed calculation to use recent activity (last 7 days) instead of total time span

## Changes Made

### 1. Velocity Calculation Fix (`narrative_service.py`)

**Problem**: Velocity was calculated as `total_articles / days_since_first_seen`, which accumulated over time and produced inflated numbers like "+32.96 articles/day" for only 14 articles.

**Solution**: Created `calculate_recent_velocity()` function that:
- Looks at articles from the last 7 days only
- Calculates velocity as `recent_articles / time_span_days`
- Provides accurate measure of current narrative momentum

**Files Modified**:
- `src/crypto_news_aggregator/services/narrative_service.py`
  - Added `calculate_recent_velocity()` helper function (lines 53-89)
  - Updated existing narrative velocity calculation (lines 655-668)
  - Updated new narrative velocity calculation (lines 734-750)

**Impact**: Velocity numbers now accurately reflect recent activity:
- Before: "+32.96 articles/day" for 14 articles over 30 days
- After: "+2.0 articles/day" for 14 articles in last 7 days

### 2. Clickable Cards (`Narratives.tsx`)

**Problem**: Cards had no onClick handler, making them feel static and unresponsive.

**Solution**: 
- Added `toggleExpanded()` function to handle card clicks
- Wrapped card content in clickable div
- Added `cursor-pointer` class to Card component
- Added `stopPropagation()` to article links to prevent card toggle when clicking links

**Files Modified**:
- `context-owl-ui/src/pages/Narratives.tsx`
  - Added `isExpanded` state variable (line 638)
  - Added `toggleExpanded()` function (lines 640-648)
  - Added onClick handler to card wrapper (line 658)
  - Updated article section to use `isExpanded` (lines 727-728)
  - Added stopPropagation to article links (line 740)

**Impact**: Users can now click anywhere on a card to expand/collapse article details.

### 3. Hot Icon Visibility (`Narratives.tsx`)

**Problem**: The flame icon for "Hot" narratives had poor contrast and was hard to see.

**Solution**:
- Added gradient background: `from-orange-500 to-red-500`
- Added shadow glow effect: `shadow-lg shadow-orange-500/50`
- Added white text for better contrast
- Added drop-shadow to icon itself for extra visibility

**Files Modified**:
- `context-owl-ui/src/pages/Narratives.tsx`
  - Enhanced lifecycle badge rendering (lines 682-695)
  - Special styling for `hot` state with gradient and glow

**Impact**: Hot narratives now stand out visually with a vibrant gradient badge and glowing effect.

## Testing

### Backend Testing
```bash
# Run narrative service tests
poetry run pytest tests/services/test_narrative_service.py -v

# Check velocity calculation manually
poetry run python -c "
from datetime import datetime, timezone, timedelta
from src.crypto_news_aggregator.services.narrative_service import calculate_recent_velocity

# Test with 14 articles over 7 days
dates = [datetime.now(timezone.utc) - timedelta(days=i/2) for i in range(14)]
velocity = calculate_recent_velocity(dates, lookback_days=7)
print(f'Velocity: {velocity:.2f} articles/day')
"
```

### Frontend Testing
```bash
# Start the UI dev server
cd context-owl-ui
npm run dev

# Test in browser:
# 1. Navigate to Narratives page
# 2. Click on Cards tab
# 3. Click on any card to expand/collapse
# 4. Verify velocity numbers are reasonable (< 10 articles/day typically)
# 5. Check that Hot badges are highly visible with gradient
```

## Expected Behavior

### Velocity Display
- **Emerging narratives** (< 7 days old): Velocity based on actual time span
- **Mature narratives** (> 7 days old): Velocity based on last 7 days only
- **Dormant narratives**: Velocity = 0 (no recent articles)

### Card Interaction
- Click anywhere on card → expand/collapse articles
- Click article link → open in new tab (doesn't toggle card)
- Hover over card → subtle lift animation

### Hot Badge
- Gradient background: orange → red
- White text for high contrast
- Glowing shadow effect
- Icon has drop-shadow for extra visibility

## Migration Notes

**No database migration required** - velocity is recalculated on each narrative update.

Existing narratives will show updated velocity values on their next update cycle (when new articles are added or during the next clustering run).

## Related Files
- `src/crypto_news_aggregator/services/narrative_service.py` - Velocity calculation logic
- `context-owl-ui/src/pages/Narratives.tsx` - Cards UI and interaction
- `context-owl-ui/src/components/Card.tsx` - Base card component (unchanged)
