# PR: Narrative Clustering with Co-occurrence Detection

## Summary

Implements narrative clustering to identify groups of co-occurring crypto entities and generate AI-powered thematic summaries. This feature helps users understand emerging narratives in the crypto space by connecting related entities that appear together in news articles.

## Implementation Details

### 1. Narrative Service (`src/crypto_news_aggregator/services/narrative_service.py`)

**Core Functions:**

- `find_cooccurring_entities(top_entities, min_shared_articles=2)`: Identifies entities that appear together in at least N articles
- `generate_narrative_summary(entity_group)`: Uses Claude Sonnet to generate thematic summaries from sample articles
- `detect_narratives(min_score=5.0, max_narratives=5)`: Main entry point that orchestrates narrative detection

**Algorithm:**
1. Fetch top 20 trending entities (score >= 5.0)
2. Build entity-to-articles mapping
3. Find entities sharing >= 2 articles
4. Sort groups by article count
5. Generate AI summaries for top 5 groups

### 2. Database Operations (`src/crypto_news_aggregator/db/operations/narratives.py`)

**Functions:**
- `upsert_narrative(theme, entities, story, article_count)`: Create or update narrative records
- `get_active_narratives(limit=10)`: Retrieve most recent narratives
- `delete_old_narratives(days=7)`: Cleanup old narratives
- `ensure_indexes()`: Create required indexes (updated_at, theme)

**Schema:**
```python
{
    "theme": str,           # Short title
    "entities": [str],      # List of entity names
    "story": str,           # 1-2 sentence summary
    "article_count": int,   # Number of supporting articles
    "created_at": datetime,
    "updated_at": datetime
}
```

### 3. Background Worker (`src/crypto_news_aggregator/worker.py`)

**Additions:**
- `update_narratives()`: Runs narrative detection and upserts to database
- `schedule_narrative_updates(interval_seconds)`: Continuous scheduler
- Scheduled to run every 10 minutes (600 seconds)

### 4. API Endpoint (`src/crypto_news_aggregator/api/v1/endpoints/narratives.py`)

**Endpoint:** `GET /api/v1/narratives/active`

**Query Parameters:**
- `limit`: Maximum narratives to return (1-20, default 10)

**Response Model:**
```json
{
  "theme": "Bitcoin ETF Approval",
  "entities": ["Bitcoin", "SEC", "ETF"],
  "story": "Multiple articles discuss the SEC's consideration of Bitcoin ETF applications...",
  "article_count": 15,
  "updated_at": "2025-10-01T19:30:00Z"
}
```

**Features:**
- Redis caching with 10-minute TTL
- Graceful fallback if Redis unavailable
- Error handling with 500 status on failure

### 5. Supporting Files

**Added from signal detection feature:**
- `src/crypto_news_aggregator/db/operations/signal_scores.py`: Trending entity queries
- `src/crypto_news_aggregator/db/operations/entity_mentions.py`: Entity mention operations

**Bug Fix:**
- Added missing `get_email_service()` function in `email_service.py`

## Testing

**Test Coverage:**
- `tests/services/test_narrative_service.py`: 5 tests for narrative service
- `tests/api/test_narratives_endpoint.py`: 6 tests for API endpoint
- **All 11 tests passing ✅**

**Test Scenarios:**
- Co-occurrence detection with multiple entities
- Narrative summary generation (success and fallback)
- Empty entity handling
- API caching behavior
- Error handling
- Limit validation

## Key Design Decisions

1. **Simple Co-occurrence**: Uses straightforward set intersection instead of complex graph algorithms for maintainability
2. **Claude Sonnet**: Generates human-readable narrative summaries from article samples
3. **10-minute Updates**: Balances freshness with API/compute costs
4. **Redis Caching**: Reduces database load for frequently accessed endpoint
5. **Fallback Handling**: Graceful degradation when JSON parsing fails or services unavailable

## Dependencies

- Requires trending entities from signal detection system
- Uses existing LLM provider factory (Claude/OpenAI)
- Leverages MongoDB for persistence
- Optional Redis for caching

## Usage Example

```bash
# Get active narratives
curl http://localhost:8000/api/v1/narratives/active?limit=5

# Response
[
  {
    "theme": "Bitcoin ETF Approval",
    "entities": ["Bitcoin", "SEC", "ETF"],
    "story": "SEC reviews Bitcoin ETF applications from major institutions.",
    "article_count": 15,
    "updated_at": "2025-10-01T19:30:00Z"
  },
  {
    "theme": "Ethereum Upgrade",
    "entities": ["Ethereum", "Dencun", "Layer2"],
    "story": "Ethereum's Dencun upgrade brings improvements to Layer 2 scaling.",
    "article_count": 12,
    "updated_at": "2025-10-01T19:25:00Z"
  }
]
```

## Future Enhancements

1. **Graph-based clustering**: Implement more sophisticated entity relationship detection
2. **Narrative evolution tracking**: Track how narratives change over time
3. **Sentiment analysis**: Add aggregate sentiment for each narrative
4. **User subscriptions**: Allow users to follow specific narratives
5. **Historical narratives**: Archive and query past narratives

## Deployment Notes

- No database migrations required (MongoDB schema-less)
- Ensure MongoDB indexes are created on first run
- Redis optional but recommended for production
- Worker must be running for automatic updates
- API endpoint accessible without authentication (API key protected)

## Related PRs

- Signal Detection System (prerequisite)
- Entity Extraction (prerequisite)

## Checklist

- ✅ Code implemented
- ✅ Tests written and passing (11/11)
- ✅ Documentation added
- ✅ Follows development practices (feature branch, conventional commits)
- ✅ No breaking changes
- ✅ Ready for PR review
