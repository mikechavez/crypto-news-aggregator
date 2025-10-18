# Lifecycle Badge Visibility - Verification Guide

## What Changed
All lifecycle state badges now have vibrant gradient backgrounds with white text and glow effects, matching the Hot badge's prominent styling.

## How to Verify

### 1. Open the Application
- Navigate to http://localhost:5173
- Go to the Narratives page

### 2. Check Badge Visibility in Cards View
Look for narrative cards and verify each lifecycle badge has:
- ✅ Gradient background (not flat color)
- ✅ White text (not colored text)
- ✅ Subtle glow shadow around the badge
- ✅ White icon with drop-shadow effect

### 3. Expected Badge Styles

| Lifecycle State | Gradient Colors | Shadow Color |
|----------------|-----------------|--------------|
| **Emerging** | Blue → Indigo | Blue glow |
| **Rising** | Green → Emerald | Green glow |
| **Hot** | Orange → Red | Orange glow |
| **Heating** | Red → Pink | Red glow |
| **Mature** | Purple → Violet | Purple glow |
| **Cooling** | Gray → Slate | Gray glow |

### 4. Check in Different Views
- **Cards View**: Main narrative cards should show gradient badges
- **Pulse View**: Timeline view narratives should show gradient badges
- **Archive View**: Archived narratives should show gradient badges
- **Modal View**: Click any narrative in Pulse view - the modal should show gradient badge

### 5. Test Dark Mode
- Toggle dark mode (if available)
- Verify badges remain visible and vibrant
- Check that glow effects are visible in dark mode

### 6. Compare Before/After

**Before:**
```
Rising badge: Light green background, green text (hard to see)
Emerging badge: Light blue background, blue text (hard to see)
Cooling badge: Light gray background, gray text (very hard to see)
```

**After:**
```
Rising badge: Green-to-emerald gradient, white text, green glow (highly visible)
Emerging badge: Blue-to-indigo gradient, white text, blue glow (highly visible)
Cooling badge: Gray-to-slate gradient, white text, gray glow (clearly visible)
```

## Quick Visual Test
1. Find a narrative with "Rising" state → Should see green gradient with white text
2. Find a narrative with "Emerging" state → Should see blue gradient with white text
3. Find a narrative with "Cooling" state → Should see gray gradient with white text
4. Find a narrative with "Hot" state → Should see orange-red gradient (unchanged)

## Success Criteria
- ✅ All lifecycle badges are easily readable
- ✅ Badges stand out from the background
- ✅ Consistent styling across all lifecycle states
- ✅ No visual regressions in other UI elements
- ✅ Works in both light and dark mode
