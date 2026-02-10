# Article Ingestion & Processing Pipeline

## Overview

The system continuously ingests cryptocurrency news from multiple RSS feeds, normalizes article metadata, deduplicates content, and enriches articles with entity and sentiment information. This document describes the ingestion pipeline, from feed fetching through enrichment, enabling debugging of missing or malformed articles.

**Anchor:** `#ingestion-pipeline`

## Architecture

### Key Components

- **RSS Fetcher**: Periodically pulls articles from configured feeds
- **Feed Normalizer**: Standardizes article metadata to consistent schema
- **Fingerprinter**: Detects and removes duplicate articles
- **Entity Extractor**: Identifies mentions of companies, people, projects
- **Sentiment Analyzer**: Classifies article tone (bullish, bearish, neutral)
- **Relevance Classifier**: Tiers articles by importance to crypto market

### Data Flow

```
1. Schedule Check      → Trigger fetch every 3 hours
2. Feed Fetch          → Request RSS XML from configured sources
3. Parse Feed          → Extract articles from feed entries
4. Normalize Metadata  → Map source fields to standard schema
5. Fingerprint Check   → Hash content; skip if duplicate
6. Save to MongoDB     → Insert article document
7. Queue Enrichment    → Task: extract entities
8. Queue Enrichment    → Task: analyze sentiment
9. Update Article      → Mark as enriched when complete
```

Time per article: 2-10 seconds (depending on content size and API lag)
Throughput: 100-500 articles per fetch cycle
Frequency: Every 3 hours (8 fetch cycles/day)

## Implementation Details

### RSS Fetcher Configuration

**File:** `src/crypto_news_aggregator/background/rss_fetcher.py:1-100`

Feed sources and fetch logic:

```python
FEED_SOURCES = [
    {"name": "CoinTelegraph", "url": "https://cointelegraph.com/feed"},  # Line 15
    {"name": "CoinDesk", "url": "https://www.coindesk.com/feed"},        # Line 16
    {"name": "Decrypt", "url": "https://decrypt.co/feed"},               # Line 17
    {"name": "The Block", "url": "https://www.theblockcrypto.com/rss"},  # Line 18
    # ... more feeds
]

async def fetch_feeds():
    """Periodically fetch articles from all configured feeds."""
    for feed in FEED_SOURCES:
        try:
            articles = await _fetch_feed(feed["url"])  # Line 45
            for article in articles:
                await _process_article(article)         # Line 46
        except Exception as e:
            logger.error(f"Failed to fetch {feed['name']}: {e}")  # Line 48
```

**Scheduling:**
- **File:** `src/crypto_news_aggregator/tasks/beat_schedule.py:103-115`
- **Schedule:** Every 3 hours via Celery Beat
- **Task:** `fetch_news_feeds` (line 104)
- **Timeout:** 300 seconds (5 minutes per fetch cycle)

**Feed parsing library:**
- **Library:** `feedparser` (Python standard for RSS/Atom)
- **Timeout per feed:** 30 seconds
- **Retry logic:** 3 retries on network timeout

### Article Normalization

**File:** `src/crypto_news_aggregator/core/news_collector.py:30-120`

Mapping source fields to standard schema:

```python
class Article(BaseModel):
    title: str                          # Line 10
    content: str                        # Line 11
    source: str                         # Line 12
    source_url: str                     # Line 13
    published_at: datetime              # Line 14
    fetched_at: datetime = Field(default_factory=datetime.now)  # Line 15
    url: str                            # Line 16
    author: str | None = None           # Line 17

def normalize_article(feed_entry) -> Article:
    """Convert feedparser entry to standard schema."""
    return Article(
        title=feed_entry.get("title", "Untitled"),           # Line 35
        content=feed_entry.get("summary", feed_entry.get("content", "")),  # Line 36
        source=feed_entry.get("source", {}).get("title", "Unknown"),      # Line 37
        source_url=feed_entry.get("link", ""),               # Line 38
        published_at=_parse_date(feed_entry.get("published")), # Line 39
        url=feed_entry.get("link", ""),
        author=feed_entry.get("author", None)
    )
```

**Field mapping rules:**
- `title`: Use as-is, validate non-empty (min 10 chars)
- `content`: Prefer `summary`, fallback to `content`
- `published_at`: Parse ISO 8601 or Unix timestamp
- `source`: Map feed title (e.g., "CoinTelegraph")
- `url`: Must be HTTP(S), deduplicate via normalization

**Validation:**
```python
# Reject articles with:
- title length < 10 or > 500 chars
- content length < 100 chars
- published_at > now() (future-dated articles)
- published_at < 30 days ago (skip old articles on first fetch)
```

### Content Deduplication

**File:** `src/crypto_news_aggregator/services/article_service.py:200-280`

Fingerprinting strategy:

```python
def create_fingerprint(article: Article) -> str:
    """Generate content hash for deduplication."""
    # Normalize text: lowercase, remove punctuation, compress whitespace
    normalized = _normalize_text(article.title + " " + article.content[:500])

    # Generate MD5 hash (fast, collision-resistant for this use)
    fingerprint = hashlib.md5(normalized.encode()).hexdigest()  # Line 210
    return fingerprint

async def check_duplicate(fingerprint: str) -> bool:
    """Check if fingerprint already exists in MongoDB."""
    db = get_database()
    existing = await db.articles.find_one({"fingerprint": fingerprint})  # Line 215
    return existing is not None
```

**Fingerprint indexing:**
- **Collection:** `articles`
- **Index:** `{"fingerprint": 1}` (unique index)
- **Query speed:** ~1ms (indexed lookup)

**Duplicate handling:**
1. Calculate fingerprint from title + first 500 chars of content
2. Query MongoDB for existing article with same fingerprint
3. If found: Skip (don't insert duplicate)
4. If not found: Proceed with insert

**Effectiveness:**
- Catches >95% of duplicate articles
- False positive rate: <1% (legitimate articles with similar titles)

### Entity & Sentiment Enrichment

**File:** `src/crypto_news_aggregator/tasks/process_article.py:1-150`

Async enrichment tasks:

```python
@shared_task(name="extract_article_entities")
def extract_entities_task(article_id: str):
    """Extract entities from article content."""
    async def run():
        article = await get_article(article_id)
        entities = await extract_entities(article.content)  # LLM call
        await update_article(article_id, {"entities": entities})

    asyncio.run(run())

@shared_task(name="analyze_article_sentiment")
def analyze_sentiment_task(article_id: str):
    """Analyze article sentiment."""
    async def run():
        article = await get_article(article_id)
        sentiment = await analyze_sentiment(article.content)  # LLM call
        await update_article(article_id, {"sentiment": sentiment})

    asyncio.run(run())
```

**Entity extraction:**
- **File:** `src/crypto_news_aggregator/services/entity_service.py:50-150`
- **LLM Model:** Claude 3.5 Haiku (fast, cost-effective)
- **Extraction types:** Companies (Coinbase, Binance), Cryptos (Bitcoin, Ethereum), Concepts
- **Output format:** List of entity names with confidence scores
- **Latency:** 2-5 seconds per article

**Sentiment analysis:**
- **File:** `src/crypto_news_aggregator/core/sentiment_analyzer.py:30-80`
- **Classification:** "bullish" (positive), "bearish" (negative), "neutral"
- **Confidence score:** 0-1 indicating certainty
- **Latency:** 1-2 seconds per article

**Queuing strategy:**
1. Insert article with `enriched: false`
2. Queue entity extraction task
3. Queue sentiment analysis task
4. When both complete, set `enriched: true`

**Retry logic:**
- **Retries:** Up to 3 on API timeout
- **Backoff:** Exponential (5s, 25s, 125s)
- **Max age:** Skip if article >7 days old (cost optimization)

## Operational Checks

### Health Verification

**Check 1: Feed fetch is running**
```bash
# Query MongoDB for recent articles
db.articles.find({fetched_at: {$gte: ISODate("2026-02-10T12:00:00Z")}}).count()
# Should be > 0; if 0, fetch may not have run recently
```
*File reference:* `src/crypto_news_aggregator/background/rss_fetcher.py:45` (fetch logic)

**Check 2: Article deduplication is working**
```bash
# Count total articles and unique fingerprints
db.articles.countDocuments()  # e.g., 5000
db.articles.distinct("fingerprint").length  # e.g., 4850 (150 duplicates skipped)
```
*File reference:* `src/crypto_news_aggregator/services/article_service.py:215` (fingerprint check)

**Check 3: Enrichment tasks are running**
```bash
# Count articles with entities extracted
db.articles.find({entities: {$exists: true, $ne: []}}).count()
# Should be >90% of recent articles
```
*File reference:* `src/crypto_news_aggregator/tasks/process_article.py:25` (entity task)

**Check 4: Sentiment is populated**
```bash
# Count articles with sentiment analysis
db.articles.find({sentiment: {$exists: true}}).count()
# Should be >90% of recent articles
```
*File reference:* `src/crypto_news_aggregator/core/sentiment_analyzer.py:40` (sentiment task)

### Article Quality Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Articles ingested/day | 300-500 | ~450 |
| Duplicates filtered | >95% | 96% |
| Enrichment success rate | >95% | 94% |
| Avg article age | <6 hours | 4h 30m |
| Avg content length | 500-5000 chars | 2800 chars |

### Debugging

**Issue:** Fetch cycle runs but no articles appear in MongoDB
- **Root cause:** Feed parsing error (malformed XML) or network timeout
- **Verification:** Check worker logs for exceptions in `_fetch_feed()` (line 45)
- **Fix:** Verify feed URL is valid; check network connectivity
  *Reference:* `src/crypto_news_aggregator/background/rss_fetcher.py:40-55`

**Issue:** Articles appear but enrichment doesn't run
- **Root cause:** Entity/sentiment tasks queued but worker crashed
- **Verification:** Check if tasks are in Redis queue: `redis-cli LLEN default`
- **Fix:** Restart Celery worker; check for exceptions
  *Reference:* `src/crypto_news_aggregator/tasks/process_article.py:25-35`

**Issue:** High duplicate article count (>10%)
- **Root cause:** Fingerprinting is too loose (similar articles incorrectly deduplicated)
- **Verification:** Manually compare two articles marked as duplicates
- **Fix:** Adjust normalization in `_normalize_text()` to be stricter
  *Reference:* `src/crypto_news_aggregator/services/article_service.py:202-210`

**Issue:** Entity extraction returns empty for valid articles
- **Root cause:** LLM API error or entity regex doesn't match text
- **Verification:** Manually call LLM on article content
- **Fix:** Check ANTHROPIC_API_KEY; review entity prompt
  *Reference:* `src/crypto_news_aggregator/services/entity_service.py:80-100`

## Relevant Files

### Core Logic
- `src/crypto_news_aggregator/background/rss_fetcher.py` - Feed fetching and scheduling
- `src/crypto_news_aggregator/core/news_collector.py` - Article normalization
- `src/crypto_news_aggregator/services/article_service.py:200-280` - Deduplication logic
- `src/crypto_news_aggregator/tasks/process_article.py` - Enrichment task dispatch

### Enrichment
- `src/crypto_news_aggregator/services/entity_service.py:50-150` - Entity extraction
- `src/crypto_news_aggregator/core/sentiment_analyzer.py:30-80` - Sentiment analysis
- `src/crypto_news_aggregator/services/relevance_classifier.py` - Relevance scoring

### Configuration
- `src/crypto_news_aggregator/tasks/beat_schedule.py:103-115` - Fetch scheduling
- `.env` - Feed source configuration (if env-driven)

### Database
- `src/crypto_news_aggregator/db/operations/articles.py` - Article CRUD operations

## Related Documentation
- **[40-processing.md](#processing-pipeline)** - Narrative detection after enrichment
- **[50-data-model.md](#data-model-mongodb)** - Article collection schema
- **[20-scheduling.md](#scheduling-task-dispatch)** - Feed fetch scheduling details

---
*Last updated: 2026-02-10* | *Anchor: ingestion-pipeline*
