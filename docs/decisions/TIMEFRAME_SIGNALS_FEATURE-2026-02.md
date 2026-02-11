# Timeframe Support for Signals API

## Summary
Added multi-timeframe support to the signals API, allowing users to query trending entities across different time windows (24h, 7d, 30d).

## Changes Made

### 1. API Endpoint Updates (`signals.py`)
- **New Parameter**: `timeframe` query parameter with values: `24h`, `7d`, `30d`
- **Default**: `7d` (most useful for trend analysis)
- **Validation**: Returns 400 error for invalid timeframe values
- **Response**: Returns timeframe-specific `signal_score` and `velocity` fields
- **Cache**: Updated cache keys to include timeframe for proper isolation

### 2. Database Operations (`signal_scores.py`)
- Updated `get_trending_entities()` to accept `timeframe` parameter
- Filters and sorts by timeframe-specific score fields:
  - `24h` → uses `score_24h`, `velocity_24h`
  - `7d` → uses `score_7d`, `velocity_7d`
  - `30d` → uses `score_30d`, `velocity_30d`

### 3. Tests (`test_signals.py`)
- Added 6 new test cases covering:
  - Each timeframe option (24h, 7d, 30d)
  - Invalid timeframe handling
  - Different rankings across timeframes
  - Default timeframe verification
- Updated test fixture to include multi-timeframe data
- Fixed AsyncClient usage for httpx 0.28.1 compatibility

## API Usage

### Endpoint
```
GET /api/v1/signals/trending?timeframe={24h|7d|30d}
```

### Parameters
- `timeframe` (optional): Time window for scoring
  - `24h`: Recent short-term trends
  - `7d`: Weekly trends (default)
  - `30d`: Long-term trends
- `limit` (optional): Maximum results (1-100, default 10)
- `min_score` (optional): Minimum signal score (0-10, default 0)
- `entity_type` (optional): Filter by type (ticker, project, event)

### Response Structure
```json
{
  "count": 3,
  "filters": {
    "limit": 10,
    "min_score": 0.0,
    "entity_type": null,
    "timeframe": "7d"
  },
  "signals": [
    {
      "entity": "$BTC",
      "entity_type": "ticker",
      "signal_score": 8.5,
      "velocity": 12.3,
      "source_count": 15,
      "sentiment": {...},
      "is_emerging": false,
      "narratives": [...],
      "recent_articles": [...],
      "first_seen": "2025-10-07T19:00:00Z",
      "last_updated": "2025-10-07T19:15:00Z"
    }
  ]
}
```

## Testing with curl

### Test 24h Timeframe
```bash
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8000/api/v1/signals/trending?timeframe=24h&limit=5"
```

### Test 7d Timeframe (Default)
```bash
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8000/api/v1/signals/trending?timeframe=7d&limit=5"
```

### Test 30d Timeframe
```bash
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8000/api/v1/signals/trending?timeframe=30d&limit=5"
```

### Test Default (Should use 7d)
```bash
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8000/api/v1/signals/trending?limit=5"
```

### Test Invalid Timeframe (Should return 400)
```bash
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8000/api/v1/signals/trending?timeframe=1h"
```

### Compare Rankings Across Timeframes
```bash
# Get 24h rankings
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8000/api/v1/signals/trending?timeframe=24h" \
  | jq '.signals[0].entity'

# Get 30d rankings
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8000/api/v1/signals/trending?timeframe=30d" \
  | jq '.signals[0].entity'
```

## Expected Behavior

1. **Different Rankings**: Entities may rank differently across timeframes
   - A token trending in 24h might not be in top 30d
   - Long-term trends (30d) show sustained interest
   - Short-term trends (24h) show breaking news/events

2. **Recent Articles**: Always shows recent articles regardless of timeframe
   - This provides context for why an entity is trending
   - Articles are sorted by recency, not by timeframe

3. **Cache Isolation**: Each timeframe has its own cache
   - Cache key format: `signals:trending:{limit}:{min_score}:{entity_type}:{timeframe}`
   - 2-minute cache TTL per timeframe

## Implementation Notes

- **Backward Compatibility**: Default timeframe is 7d, maintaining existing behavior
- **Fallback**: If timeframe-specific fields are missing, falls back to legacy `score` and `velocity` fields
- **Validation**: Strict validation ensures only valid timeframes are accepted
- **Performance**: Leverages existing multi-timeframe data from signal calculation service

## Next Steps

1. Update UI to add timeframe selector dropdown
2. Add timeframe to signal alerts configuration
3. Consider adding custom timeframe ranges (e.g., 3d, 14d)
4. Add timeframe comparison view in UI

## Commit
```
feat: add timeframe support to signals API

- Add timeframe query parameter (24h/7d/30d) to /api/v1/signals/trending endpoint
- Default timeframe is 7d (most useful for trend analysis)
- Update get_trending_entities() to filter and sort by timeframe-specific scores
- Return timeframe-specific score and velocity fields in API response
- Add comprehensive tests for all timeframe options
- Validate timeframe parameter with proper error handling
- Update cache keys to include timeframe for proper cache isolation
```

## Branch
`feature/multi-timeframe-signals`
