# Velocity Indicator Analysis

## Problem Statement
All signal velocities show "Surging" 🔥 instead of varied indicators (Rising, Growing, Active, Declining).

## Root Cause
**The velocity values are stored as percentages (4700 = 4700% growth), but the UI thresholds expect much smaller values.**

### Current State

#### Backend Calculation (signal_service.py)
```python
# Velocity = (current_period - previous_period) / previous_period
# Example: 50 mentions now vs 30 before = (50-30)/30 = 0.67 (67% growth)
# BUT: If previous_period = 0, velocity = 1.0 (100%)
# AND: For new entities, we're seeing velocities of 800, 4700, 9500, etc.
```

#### UI Thresholds (Signals.tsx)
```typescript
if (velocity >= 50)  → 🔥 Surging
if (velocity >= 20)  → ↑ Rising
if (velocity >= 5)   → → Growing
if (velocity >= 0)   → Active
if (velocity < 0)    → ↓ Declining
```

### Actual Data from Database

**Sample Entities (7d timeframe):**
| Entity | Velocity_7d | UI Label | Score_7d | Mentions_7d |
|--------|-------------|----------|----------|-------------|
| BlackRock | 4700.000 | 🔥 Surging | 10.00 | 48 |
| Ripple | 3000.000 | 🔥 Surging | 10.00 | 93 |
| SEC | 2900.000 | 🔥 Surging | 10.00 | 60 |
| Coinbase | 9500.000 | 🔥 Surging | 10.00 | 96 |
| Solana | 1375.000 | 🔥 Surging | 10.00 | 118 |
| Ethereum | 5500.000 | 🔥 Surging | 10.00 | 224 |
| Bitcoin | 1379.070 | 🔥 Surging | 10.00 | 636 |

**Velocity Distribution (7d):**
- Surging (>=50): **135 entities** ← Problem: Too many!
- Rising (20-50): **0 entities**
- Growing (5-20): **1 entity**
- Active (0-5): **138 entities**
- Declining (<0): **1 entity**

**Entity Coverage:**
- Total unique entities: 657
- Entities with signal_scores: 280
- Entities with 7d velocity data: 275

## Why Velocities Are So High

Looking at the backend calculation in `calculate_mentions_and_velocity()`:

```python
if previous_mentions == 0:
    # If no previous data, velocity is 100% if we have current mentions, else 0%
    velocity = 1.0 if current_mentions > 0 else 0.0
else:
    # Growth rate: (current - previous) / previous
    velocity = (current_mentions - previous_mentions) / previous_mentions
```

**The issue:** When an entity goes from 1 mention to 48 mentions:
- velocity = (48 - 1) / 1 = **47.0** (4700% growth!)

This is mathematically correct but creates extreme values for emerging entities.

## Solution Options

### Option 1: Adjust UI Thresholds (RECOMMENDED)
**Pros:** 
- No backend changes needed
- Preserves mathematical accuracy of velocity calculation
- Quick fix

**Cons:**
- Need to determine appropriate thresholds from real data

**Recommended Thresholds:**
```typescript
if (velocity >= 1000) → 🔥 Surging    // 1000%+ growth (10x)
if (velocity >= 100)  → ↑ Rising      // 100%+ growth (2x)
if (velocity >= 10)   → → Growing     // 10%+ growth
if (velocity >= 0)    → Active        // Any positive growth
if (velocity < 0)     → ↓ Declining   // Negative growth
```

### Option 2: Cap Velocity in Backend
**Pros:**
- Prevents extreme outliers
- More stable UI display

**Cons:**
- Loses information about true growth rates
- Arbitrary cap value

**Implementation:**
```python
# In calculate_mentions_and_velocity()
velocity = min(velocity, 10.0)  # Cap at 1000% growth
```

### Option 3: Logarithmic Scale
**Pros:**
- Handles wide range of values
- More nuanced differentiation

**Cons:**
- More complex
- Less intuitive

**Implementation:**
```python
import math
velocity_display = math.log10(max(velocity, 0.1)) * 100
```

## Recommended Action

**Adjust UI thresholds** to match the actual velocity ranges in the data:

```typescript
// In context-owl-ui/src/pages/Signals.tsx
const getVelocityIndicator = (velocity: number) => {
  if (velocity >= 1000) {
    return { emoji: '🔥', label: 'Surging', colorClass: 'bg-red-100 text-red-700' };
  } else if (velocity >= 100) {
    return { emoji: '↑', label: 'Rising', colorClass: 'bg-green-100 text-green-700' };
  } else if (velocity >= 10) {
    return { emoji: '→', label: 'Growing', colorClass: 'bg-blue-100 text-blue-700' };
  } else if (velocity >= 0) {
    return { emoji: '', label: 'Active', colorClass: 'bg-gray-100 text-gray-700' };
  } else {
    return { emoji: '↓', label: 'Declining', colorClass: 'bg-orange-100 text-orange-700' };
  }
};
```

This would result in a better distribution:
- **Surging**: Entities with 1000%+ growth (10x mentions)
- **Rising**: Entities with 100-1000% growth (2-10x mentions)
- **Growing**: Entities with 10-100% growth
- **Active**: Entities with 0-10% growth
- **Declining**: Entities with negative growth

## Testing Plan

1. Update UI thresholds
2. Test with current data
3. Monitor distribution over time
4. Adjust thresholds if needed based on real usage patterns

## Files to Modify

- `context-owl-ui/src/pages/Signals.tsx` - Update `getVelocityIndicator()` function
