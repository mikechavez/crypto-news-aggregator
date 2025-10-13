# Recency Scoring Implementation

## Overview
Added recency scoring to enable freshness-based sorting of narratives. The recency score uses an exponential decay function with a 24-hour half-life to prioritize recent narratives.

## Implementation Details

### Formula
```python
recency_score = exp(-hours_since_last_update / 24)
```

- **Range**: 0.0 to 1.0
- **Higher values**: More recent narratives
- **Half-life**: 24 hours (score = 0.368 at 24h)

### Score Examples
| Time Since Last Article | Recency Score |
|------------------------|---------------|
| 1 hour ago             | 0.959         |
| 12 hours ago           | 0.607         |
| 24 hours ago           | 0.368         |
| 48 hours ago           | 0.135         |
| 72 hours ago           | 0.050         |

## Files Modified

### 1. `src/crypto_news_aggregator/services/narrative_service.py`
- **Import added**: `from math import exp`
- **Calculation location**: After momentum calculation, before lifecycle determination
- **Implementation**: 
  - Calculates hours since newest article
  - Applies exponential decay with 24h half-life
  - Rounds to 3 decimal places
  - Defaults to 0.0 if no articles
- **Applied to**: Both salience-based and theme-based clustering paths

### 2. `src/crypto_news_aggregator/db/operations/narratives.py`
- **Function signature updated**: Added `recency_score: float = 0.0` parameter
- **Database fields**: Added `recency_score` to both update and insert operations
- **Documentation**: Updated docstring to include recency_score parameter

### 3. `src/crypto_news_aggregator/worker.py`
- **Worker update**: Added `recency_score=narrative.get("recency_score", 0.0)` to upsert call
- **Ensures**: Background narrative updates include recency score

### 4. `src/crypto_news_aggregator/api/v1/endpoints/narratives.py`
- **Response model updated**: Added `recency_score` field to `NarrativeResponse`
- **API response**: Included `recency_score` in narrative endpoint response data
- **Documentation**: Updated example response to show recency_score value
- **Enables**: Frontend sorting and filtering by freshness

## Usage

### Sorting by Freshness
Narratives can now be sorted by `recency_score` in descending order to show the freshest content first:

```python
# MongoDB query example
narratives = await collection.find({}).sort("recency_score", -1).limit(10)
```

### Combined Sorting
Can be combined with other metrics for hybrid sorting:

```python
# Example: Sort by combination of recency and velocity
# In application logic:
narratives.sort(key=lambda n: n['recency_score'] * 0.5 + n['mention_velocity'] * 0.5, reverse=True)
```

## Testing

### Syntax Validation
All modified files pass Python compilation:
- ✅ `narrative_service.py`
- ✅ `narratives.py`
- ✅ `worker.py`

### Recency Score Calculation Test
Verified exponential decay function produces expected values across different time ranges.

## Database Schema

### New Field
- **Field name**: `recency_score`
- **Type**: `float`
- **Range**: 0.0 - 1.0
- **Default**: 0.0
- **Precision**: 3 decimal places

## Backward Compatibility

- Existing narratives without `recency_score` will default to 0.0
- Tests using default parameters continue to work
- No migration required (field added via upsert operations)

## Next Steps

1. **API Integration**: Update narrative API endpoints to support sorting by recency
2. **UI Integration**: Add "Sort by Freshness" option in Context Owl UI
3. **Indexing**: Consider adding MongoDB index on `recency_score` for performance
4. **Monitoring**: Track recency score distribution in production

## Related Files
- Implementation: `src/crypto_news_aggregator/services/narrative_service.py`
- Database ops: `src/crypto_news_aggregator/db/operations/narratives.py`
- Background worker: `src/crypto_news_aggregator/worker.py`
