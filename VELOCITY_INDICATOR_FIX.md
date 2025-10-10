# Velocity Indicator Fix

## Problem
All signals were showing "Active" velocity indicator instead of varied indicators (🔥 Surging, ↑ Rising, → Growing).

## Root Cause
**Backend-Frontend Mismatch:**
- **Backend** returned velocity as a **decimal growth rate** (e.g., `0.67` for 67% growth)
- **Frontend** expected velocity as a **percentage number** (e.g., `67` for 67% growth)

**Frontend Thresholds (Signals.tsx):**
```typescript
if (velocity >= 50) → 🔥 Surging
else if (velocity >= 20) → ↑ Rising
else if (velocity >= 5) → → Growing
else if (velocity >= 0) → Active
else → ↓ Declining
```

**Backend Calculation (Before Fix):**
```python
velocity = (current_mentions - previous_mentions) / previous_mentions
# Returns: 0.67 for 67% growth, NOT 67
```

**Result:** All velocity values like `0.67`, `1.5`, etc. were less than `5`, so everything showed "Active".

## Solution
Modified `signal_service.py` to return velocity as percentage:

### Changes Made

**1. Updated `calculate_mentions_and_velocity()` function:**
```python
# Before:
velocity = (current_mentions - previous_mentions) / previous_mentions

# After:
velocity = ((current_mentions - previous_mentions) / previous_mentions) * 100
```

**2. Updated signal score calculation to handle percentage values:**
```python
# Before:
velocity_component = metrics["velocity"] * 0.5  # velocity was 0-3.0

# After:
velocity_component = (metrics["velocity"] / 100) * 0.5  # velocity is now 0-300
```

**3. Updated test expectations:**
```python
# Before:
assert result["velocity"] == pytest.approx(0.667, abs=0.01)

# After:
assert result["velocity"] == pytest.approx(66.67, abs=0.1)
```

## Files Modified
- `src/crypto_news_aggregator/services/signal_service.py`
  - `calculate_mentions_and_velocity()` - Returns percentage instead of decimal
  - `calculate_signal_score()` - Scales velocity percentage for scoring
  - Updated docstrings to reflect percentage format
- `tests/services/test_signal_service.py`
  - Updated test expectations for percentage values

## Verification
Created `test_velocity_fix.py` to verify the fix:
- 67% growth → 66.67 velocity → 🔥 Surging ✅
- 100% growth → 100.0 velocity → 🔥 Surging ✅
- 20% growth → 20.0 velocity → ↑ Rising ✅
- 10% growth → 10.0 velocity → → Growing ✅
- 4% growth → 4.0 velocity → Active ✅
- -10% growth → -10.0 velocity → ↓ Declining ✅

## Migration Required
Run the migration script to recalculate existing signals with new percentage format:
```bash
poetry run python scripts/recalculate_velocity_percentages.py
```

This will:
1. Fetch all existing signal scores
2. Recalculate velocity for all three timeframes (24h, 7d, 30d)
3. Update database with new percentage values
4. Display sample of updated velocities

## Expected Impact
After deployment and migration:
- Signals with 50%+ growth will show 🔥 Surging
- Signals with 20-49% growth will show ↑ Rising
- Signals with 5-19% growth will show → Growing
- Signals with 0-4% growth will show Active
- Signals with negative growth will show ↓ Declining

This makes the velocity indicators **dynamic and meaningful**, providing users with better insight into trending entities.

## API Response Format
The API now returns velocity as percentage in all endpoints:
```json
{
  "entity": "Solana",
  "velocity": 67.50,  // Percentage (was 0.675)
  "velocity_24h": 45.20,
  "velocity_7d": 67.50,
  "velocity_30d": 120.00
}
```

## Backward Compatibility
- The change is **not backward compatible** with old frontend code expecting decimals
- Frontend code already expects percentages, so this fix aligns backend with frontend
- Existing signal scores need migration to update velocity values
