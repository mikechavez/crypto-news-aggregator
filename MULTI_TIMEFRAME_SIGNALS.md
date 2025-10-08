# Multi-Timeframe Signal Scoring Implementation

## Overview
Added support for calculating signal scores across three timeframes: 24h, 7d, and 30d. Each timeframe uses a velocity-based growth rate calculation.

## Changes Made

### 1. Signal Service (`signal_service.py`)

#### New Functions
- **`calculate_mentions_and_velocity(entity, timeframe_hours)`**: Calculates mention count and velocity as growth rate
  - Velocity = (current_period - previous_period) / previous_period
  - Example: 50 mentions this week vs 30 last week = 67% velocity (0.67)

- **`calculate_recency_factor(entity, timeframe_hours)`**: Measures what percentage of mentions occurred in the most recent 20% of the timeframe
  - Returns value between 0.0 and 1.0
  - Higher values indicate more recent activity

#### Updated Functions
- **`calculate_signal_score(entity, timeframe_hours=None)`**: 
  - If `timeframe_hours` is provided, uses new formula:
    - velocity (growth %) × 0.5
    - source_diversity × 0.3
    - recency_factor × 0.2
  - If `timeframe_hours` is None, uses legacy calculation for backward compatibility

### 2. Database Operations (`signal_scores.py`)

#### Updated `upsert_signal_score()`
Added optional parameters for multi-timeframe data:
- `score_24h`, `score_7d`, `score_30d`: Signal scores per timeframe
- `velocity_24h`, `velocity_7d`, `velocity_30d`: Velocity metrics per timeframe
- `mentions_24h`, `mentions_7d`, `mentions_30d`: Mention counts per timeframe
- `recency_24h`, `recency_7d`, `recency_30d`: Recency factors per timeframe

### 3. Worker (`worker.py`)

#### Updated `update_signal_scores()`
Now calculates scores for all three timeframes:
```python
signal_24h = await calculate_signal_score(entity, timeframe_hours=24)
signal_7d = await calculate_signal_score(entity, timeframe_hours=168)  # 7 days
signal_30d = await calculate_signal_score(entity, timeframe_hours=720)  # 30 days
```

Stores all timeframe data in a single database record per entity.

## Formula Details

### Velocity Calculation
```
velocity = (current_period_mentions - previous_period_mentions) / previous_period_mentions
```

Example:
- Current week: 50 mentions
- Previous week: 30 mentions
- Velocity: (50 - 30) / 30 = 0.67 (67% growth)

### Signal Score Formula
```
raw_score = (velocity × 0.5) + (source_diversity × 0.3) + (recency_factor × 0.2)
normalized_score = min(10.0, (raw_score / 7.7) × 10.0)
```

Component weights:
- **Velocity (50%)**: Growth rate of mentions
- **Source Diversity (30%)**: Number of unique sources
- **Recency Factor (20%)**: Concentration of recent activity

## Test Results

Test script: `scripts/test_multi_timeframe_signals.py`

### Sample Output (Bitcoin)
```
📈 24-HOUR TIMEFRAME:
  Score:          1.59
  Velocity:       0.0 (0.0% growth)
  Mentions:       39

📈 7-DAY TIMEFRAME:
  Score:          3.36
  Velocity:       2.647 (264.7% growth)
  Mentions:       186

📈 30-DAY TIMEFRAME:
  Score:          10.0
  Velocity:       121.5 (12150.0% growth)
  Mentions:       245
```

### Validation
✅ Scores differ across timeframes  
✅ Velocities differ across timeframes  
✅ Database storage working correctly  
✅ Multiple entities tested successfully

## Database Schema

MongoDB `signal_scores` collection now includes:

**Legacy fields** (backward compatible):
- `score`, `velocity`, `source_count`, `sentiment`

**New multi-timeframe fields**:
- `score_24h`, `score_7d`, `score_30d`
- `velocity_24h`, `velocity_7d`, `velocity_30d`
- `mentions_24h`, `mentions_7d`, `mentions_30d`
- `recency_24h`, `recency_7d`, `recency_30d`

## Worker Behavior

The signal scoring worker runs every 2 minutes and:
1. Identifies entities mentioned in the last 30 minutes
2. Calculates scores for all three timeframes (24h, 7d, 30d)
3. Stores all timeframe data in a single upsert operation
4. Logs top entity with all three scores

## Backward Compatibility

- Legacy `calculate_signal_score(entity)` calls still work (without timeframe parameter)
- Existing API endpoints continue to function
- Old signal score records work without multi-timeframe fields
- New fields are optional in database operations

## Usage Examples

### Calculate score for specific timeframe
```python
from crypto_news_aggregator.services.signal_service import calculate_signal_score

# 24-hour score
signal_24h = await calculate_signal_score("Bitcoin", timeframe_hours=24)

# 7-day score
signal_7d = await calculate_signal_score("Bitcoin", timeframe_hours=168)

# 30-day score
signal_30d = await calculate_signal_score("Bitcoin", timeframe_hours=720)
```

### Access stored multi-timeframe data
```python
from crypto_news_aggregator.db.operations.signal_scores import get_entity_signal

signal = await get_entity_signal("Bitcoin")
print(f"24h: {signal['score_24h']}")
print(f"7d: {signal['score_7d']}")
print(f"30d: {signal['score_30d']}")
```

## Next Steps

Consider:
1. Update API endpoints to expose multi-timeframe data
2. Add UI components to display timeframe comparison
3. Create alerts based on timeframe-specific thresholds
4. Add historical tracking of timeframe scores over time
