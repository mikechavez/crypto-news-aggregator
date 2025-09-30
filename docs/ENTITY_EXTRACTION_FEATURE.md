# Batched Entity Extraction Feature

## Overview
Added batched entity extraction to the RSS enrichment pipeline using Claude Haiku 3.5 for efficient processing of crypto news articles.

## Implementation Details

### 1. LLM Provider Enhancement
**File:** `src/crypto_news_aggregator/llm/base.py`, `src/crypto_news_aggregator/llm/anthropic.py`

- Added `extract_entities_batch()` method to LLM base class
- Implemented batch processing in Anthropic provider using Claude Haiku 3.5
- Model configurable via `ANTHROPIC_ENTITY_MODEL` setting (default: `claude-haiku-3-5-20241022`)

### 2. Entity Types Extracted
The system extracts four types of entities from each article:

1. **Ticker Symbols**: `$BTC`, `$ETH`, `$SOL`, etc.
2. **Project Names**: Bitcoin, Ethereum, Solana, Aster Protocol, etc.
3. **Event Types**: launch, hack, partnership, regulation, upgrade, acquisition, listing, delisting, airdrop, other
4. **Sentiment**: positive, negative, neutral (per article)

### 3. Batch Processing
**File:** `src/crypto_news_aggregator/background/rss_fetcher.py`

- Articles are processed in batches of 10 (configurable via `ENTITY_EXTRACTION_BATCH_SIZE`)
- Each batch makes a single API call to Claude Haiku
- Long article text is truncated to 2000 characters to optimize token usage
- Results are mapped back to individual articles by article ID

### 4. Data Storage

#### Articles Collection
Entities are stored in the `articles` collection with the following structure:
```json
{
  "_id": "article_id",
  "title": "Article Title",
  "entities": [
    {"type": "ticker", "value": "$BTC", "confidence": 0.95},
    {"type": "project", "value": "Bitcoin", "confidence": 0.95},
    {"type": "event", "value": "regulation", "confidence": 0.85}
  ],
  ...
}
```

#### Entity Mentions Collection
**File:** `src/crypto_news_aggregator/db/operations/entity_mentions.py`

A new `entity_mentions` collection tracks each entity mention:
```json
{
  "_id": "mention_id",
  "entity": "$BTC",
  "entity_type": "ticker",
  "article_id": "article_123",
  "sentiment": "positive",
  "confidence": 0.95,
  "timestamp": "2025-09-30T17:00:00Z",
  "metadata": {
    "article_title": "Bitcoin Soars",
    "extraction_batch": true
  }
}
```

### 5. Cost Tracking
The system tracks and logs:
- Model used for extraction
- Input tokens consumed
- Output tokens generated
- Total tokens
- Input cost (per 1K tokens)
- Output cost (per 1K tokens)
- Total cost per batch
- Cumulative cost per enrichment cycle

**Configuration:**
```env
ANTHROPIC_ENTITY_MODEL=claude-haiku-3-5-20241022
ANTHROPIC_ENTITY_INPUT_COST_PER_1K_TOKENS=0.0008
ANTHROPIC_ENTITY_OUTPUT_COST_PER_1K_TOKENS=0.004
ENTITY_EXTRACTION_BATCH_SIZE=10
```

### 6. Logging
The system logs:
```
INFO - Processing entity extraction batch 0-10 of 25 articles
INFO - Entity extraction batch cost: $0.001800 (model: claude-haiku-3-5-20241022, tokens: 1500 in / 300 out)
INFO - Enriched 25 article(s) with sentiment, themes, keywords, and entities
INFO - Total entity extraction cost: $0.004500
```

## API Operations

### Entity Mentions Operations
**File:** `src/crypto_news_aggregator/db/operations/entity_mentions.py`

#### Create Single Mention
```python
mention_id = await create_entity_mention(
    entity="$BTC",
    entity_type="ticker",
    article_id="article_123",
    sentiment="positive",
    confidence=0.95,
    metadata={"source": "batch_extraction"}
)
```

#### Create Batch Mentions
```python
mentions = [
    {"entity": "$BTC", "entity_type": "ticker", "article_id": "article_1", "sentiment": "positive"},
    {"entity": "$ETH", "entity_type": "ticker", "article_id": "article_2", "sentiment": "neutral"}
]
mention_ids = await create_entity_mentions_batch(mentions)
```

#### Query Mentions
```python
# Get all mentions for an entity
btc_mentions = await get_entity_mentions(entity="$BTC", limit=100)

# Get mentions by type
ticker_mentions = await get_entity_mentions(entity_type="ticker")

# Get mentions for an article
article_mentions = await get_entity_mentions(article_id="article_123")

# Get mentions by sentiment
positive_mentions = await get_entity_mentions(sentiment="positive")
```

#### Get Entity Statistics
```python
stats = await get_entity_stats("$BTC")
# Returns:
# {
#   "entity": "$BTC",
#   "total_mentions": 42,
#   "sentiment_distribution": {"positive": 25, "negative": 10, "neutral": 7},
#   "recent_mentions": [...]
# }
```

## Testing

### Unit Tests
**File:** `tests/background/test_entity_extraction.py`

- Tests batch processing with mock LLM client
- Validates entity types, confidence scores, and sentiment
- Tests cost tracking calculations
- Tests error handling and edge cases
- All 11 tests passing ✅

### Integration Tests
**File:** `tests/db/test_entity_mentions.py`

- Tests entity mention creation and retrieval
- Tests filtering by entity, type, article, sentiment
- Tests batch operations
- Tests entity statistics aggregation
- Tests metadata storage

## Usage Example

The entity extraction runs automatically as part of the RSS enrichment pipeline:

```python
from crypto_news_aggregator.background.rss_fetcher import fetch_and_process_rss_feeds

# Fetch RSS feeds and process articles
await fetch_and_process_rss_feeds()

# The pipeline will:
# 1. Fetch new articles from RSS feeds
# 2. Store articles in MongoDB
# 3. Batch articles (10 at a time)
# 4. Extract entities using Claude Haiku
# 5. Store entities in articles collection
# 6. Create entity mentions for tracking
# 7. Log costs and metrics
```

## Performance Considerations

1. **Batch Size**: Default 10 articles per batch balances API efficiency with prompt size
2. **Text Truncation**: Articles truncated to 2000 chars to reduce token costs
3. **Single API Call**: Each batch requires only one API call vs. individual calls per article
4. **Cost Efficiency**: Claude Haiku 3.5 is optimized for speed and cost

## Future Enhancements

1. Add entity deduplication and normalization (e.g., "BTC" vs "$BTC")
2. Implement entity trending analysis
3. Add entity-based article recommendations
4. Create entity sentiment time series
5. Add entity co-occurrence analysis
6. Implement entity-based alerts

## Branch Information

- **Branch**: `feature/batched-entity-extraction`
- **Status**: Implemented and tested
- **Commit**: Added batched entity extraction to RSS enrichment pipeline

## Files Modified/Created

### Modified
- `src/crypto_news_aggregator/llm/base.py`
- `src/crypto_news_aggregator/llm/anthropic.py`
- `src/crypto_news_aggregator/background/rss_fetcher.py`
- `src/crypto_news_aggregator/core/config.py`

### Created
- `src/crypto_news_aggregator/db/operations/entity_mentions.py`
- `tests/background/test_entity_extraction.py`
- `tests/db/test_entity_mentions.py`
- `docs/ENTITY_EXTRACTION_FEATURE.md`
