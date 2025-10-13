# Momentum-Aware Lifecycle Implementation

## Summary
Successfully implemented momentum-aware lifecycle calculation for narratives to address the issue where all narratives were showing "Emerging" due to overly high thresholds.

## Changes Made

### 1. New `calculate_momentum()` Function
**Location:** `src/crypto_news_aggregator/services/narrative_service.py` (lines 48-83)

Calculates momentum based on velocity change over time:
- Splits article dates into older and recent halves
- Calculates velocity (articles per hour) for each half
- Compares velocities to determine momentum trend
- Returns: `"growing"` (≥1.3x), `"declining"` (≤0.7x), `"stable"`, or `"unknown"` (<3 articles)

### 2. Updated `determine_lifecycle_stage()` Function
**Location:** `src/crypto_news_aggregator/services/narrative_service.py` (lines 86-120)

**Old Behavior:**
- High thresholds: velocity > 2.0 for "hot", > 3.0 for "mature"
- Result: Most narratives stuck at "emerging"

**New Behavior:**
- **Adjusted thresholds:**
  - `velocity >= 5` → "mature"
  - `velocity >= 1.5` OR `article_count >= 5` → "hot"
  - Otherwise → "emerging"

- **Momentum integration:**
  - `mature` + `declining` → **"cooling"**
  - `hot` + `growing` → **"heating"**
  - `emerging` + `growing` → **"rising"**

**New lifecycle stages:** emerging, rising, hot, heating, mature, cooling, declining

### 3. Updated `detect_narratives()` Function
**Location:** `src/crypto_news_aggregator/services/narrative_service.py`

**Salience-based path (lines 231-246):**
- Extracts article dates from cluster
- Calculates momentum using `calculate_momentum()`
- Passes momentum to `determine_lifecycle_stage()`
- Adds momentum to narrative_data

**Theme-based fallback path (lines 327-332):**
- Extracts sorted article dates
- Calculates momentum
- Uses momentum-aware lifecycle determination

### 4. Database Operations
**Location:** `src/crypto_news_aggregator/db/operations/narratives.py`

**Updated `upsert_narrative()` signature:**
- Added `momentum: str = "unknown"` parameter (line 73)
- Updated docstring to include momentum field
- Stores momentum in both update and insert operations (lines 148, 176)

### 5. Worker Integration
**Location:** `src/crypto_news_aggregator/worker.py` (line 200)

Updated narrative deduplication to include momentum field:
```python
momentum=narrative.get("momentum", "unknown")
```

## Database Schema Addition
New field added to narratives collection:
- **`momentum`**: string ("growing", "declining", "stable", "unknown")

## Benefits

1. **More accurate lifecycle stages:** Lower thresholds allow narratives to progress beyond "emerging"
2. **Momentum awareness:** Captures narrative trajectory (accelerating vs. decelerating)
3. **Richer lifecycle states:** New states like "heating", "cooling", "rising" provide nuance
4. **Backward compatible:** Default momentum value ensures existing code continues to work

## Testing Recommendations

1. Run narrative detection on recent articles to verify new lifecycle stages
2. Check that momentum values are being calculated correctly
3. Verify database stores momentum field
4. Monitor for narratives progressing through lifecycle stages

## Next Steps

- Monitor narrative lifecycle distribution in production
- Adjust thresholds if needed based on real-world data
- Consider adding momentum to API responses
- Update UI to display momentum indicators
