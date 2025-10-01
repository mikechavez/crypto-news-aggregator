# Entity Extraction Backfill Script

## Overview

The `backfill_entities.py` script extracts entities from existing articles that don't have entity data. It uses the same batch entity extraction pipeline as the RSS enrichment process.

## Features

- ✅ Queries articles without entities or with empty entities array
- ✅ Processes in batches of 10 (configurable via `ENTITY_EXTRACTION_BATCH_SIZE`)
- ✅ Updates articles with extracted entities
- ✅ Creates `entity_mentions` records for tracking
- ✅ Logs progress with running count and costs
- ✅ Safety features: dry-run mode, limit, confirmation prompt, failure detection

## Usage

### Basic Usage

```bash
# Dry run to preview (no changes)
poetry run python scripts/backfill_entities.py --dry-run

# Process all articles (with confirmation)
poetry run python scripts/backfill_entities.py

# Process with automatic yes (skip confirmation)
poetry run python scripts/backfill_entities.py --yes
```

### Testing with Limits

```bash
# Test with 10 articles
poetry run python scripts/backfill_entities.py --limit 10 --dry-run

# Process only 10 articles (live)
poetry run python scripts/backfill_entities.py --limit 10 --yes
```

### Command-Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--limit N` | Process only N articles (for testing) | None (all) |
| `--dry-run` | Preview without making changes | False |
| `--yes` | Skip confirmation prompt | False |
| `--max-failures N` | Stop after N consecutive failures | 3 |

## Output Format

The script provides detailed progress logging:

```
Processing batch 1/21 (10 articles)
  - Article abc123: 5 entities extracted
  - Article def456: 3 entities extracted
Batch cost: $0.0003, Total: $0.0012
```

### Summary Report

At the end, you'll see a comprehensive summary:

```
============================================================
BACKFILL SUMMARY
============================================================
Total articles found:     203
Successfully processed:   200
Failed:                   3
Total entities extracted: 847
Total cost:               $0.0245
Average entities/article: 4.2
Average cost/article:     $0.000123

Failed article IDs (3):
  - 68d5da0d03be63369aa3580a
  - 68d5da0703be63369aa357ed
  - 68d5da0803be63369aa357ef
============================================================
```

## Safety Features

### 1. Dry Run Mode

Use `--dry-run` to preview what will happen without making any changes:

```bash
poetry run python scripts/backfill_entities.py --limit 10 --dry-run
```

### 2. Confirmation Prompt

By default, the script asks for confirmation before processing:

```
Found 203 articles without entities
Will process ALL articles
Mode: LIVE (changes will be saved)

Proceed with backfill of 203 articles? [y/N]:
```

Skip with `--yes` flag.

### 3. Consecutive Failure Detection

The script stops if it encounters 3 consecutive failures (configurable with `--max-failures`):

```
❌ STOPPING: 3 consecutive failures detected
```

### 4. Limit for Testing

Always test with `--limit` first:

```bash
# Test with 5 articles
poetry run python scripts/backfill_entities.py --limit 5 --dry-run

# If successful, run live
poetry run python scripts/backfill_entities.py --limit 5 --yes
```

## What Gets Updated

For each article, the script:

1. **Extracts entities** using the LLM (same as RSS enrichment)
   - Ticker symbols (e.g., $BTC, $ETH)
   - Project names (e.g., Bitcoin, Ethereum)
   - Event types (e.g., regulation, upgrade, hack)

2. **Updates the article** with:
   ```json
   {
     "entities": [
       {
         "type": "ticker",
         "value": "$BTC",
         "confidence": 0.95
       },
       ...
     ],
     "updated_at": "2025-10-01T22:52:35Z"
   }
   ```

3. **Creates entity_mentions** records:
   ```json
   {
     "entity": "$BTC",
     "entity_type": "ticker",
     "article_id": "68d5da0d03be63369aa3580a",
     "sentiment": "positive",
     "confidence": 0.95,
     "metadata": {
       "article_title": "Bitcoin Reaches New High",
       "extraction_batch": true,
       "backfill": true
     }
   }
   ```

## Cost Tracking

The script tracks API costs based on token usage:

- Input tokens: `ANTHROPIC_ENTITY_INPUT_COST_PER_1K_TOKENS`
- Output tokens: `ANTHROPIC_ENTITY_OUTPUT_COST_PER_1K_TOKENS`

**Note:** If costs show as $0.000000, the cost settings may not be configured in your `.env` file.

## Batch Processing

Articles are processed in batches of 10 (configurable via `ENTITY_EXTRACTION_BATCH_SIZE` in settings):

- Reduces API calls
- Improves efficiency
- Provides better error handling

## Error Handling

### Individual Article Failures

If an article fails to update, it's logged but doesn't stop the batch:

```
  - Article abc123: 5 entities extracted
    WARNING: Failed to update article abc123
```

### Batch Failures

If an entire batch fails, the script:
1. Logs the error
2. Increments consecutive failure counter
3. Continues to next batch (unless max failures reached)

### Consecutive Failure Limit

After 3 consecutive batch failures (default), the script stops to prevent wasting API credits.

## Verification

After running the backfill, verify the results:

```bash
# Check article counts
poetry run python -c "
import asyncio, sys
sys.path.insert(0, 'src')
from crypto_news_aggregator.db.mongodb import mongo_manager

async def check():
    await mongo_manager.initialize()
    db = await mongo_manager.get_async_database()
    collection = db.articles
    
    with_entities = await collection.count_documents({'entities': {'\$exists': True, '\$ne': []}})
    without_entities = await collection.count_documents({'\$or': [{'entities': {'\$exists': False}}, {'entities': []}, {'entities': None}]})
    
    print(f'Articles with entities: {with_entities}')
    print(f'Articles without entities: {without_entities}')
    
    await mongo_manager.close()

asyncio.run(check())
"
```

## Troubleshooting

### No articles found

```
No articles found without entities.
```

All articles already have entities. You can re-run on specific articles by clearing their entities first.

### Connection errors

```
ERROR: 'MongoManager' object has no attribute 'initialize'
```

Make sure you're using the latest version of the codebase.

### API errors

```
ERROR processing batch: 403 Forbidden
```

Check your `ANTHROPIC_API_KEY` in `.env` file.

## Best Practices

1. **Always test first**: Use `--limit 10 --dry-run` before processing all articles
2. **Monitor costs**: Check the cost estimates in dry-run mode
3. **Run during off-hours**: Large backfills can take time and use API credits
4. **Check logs**: Review the summary for any failed articles
5. **Verify results**: Query the database after completion to confirm

## Example Workflow

```bash
# Step 1: Check how many articles need processing
poetry run python -c "
import asyncio, sys
sys.path.insert(0, 'src')
from crypto_news_aggregator.db.mongodb import mongo_manager

async def check():
    await mongo_manager.initialize()
    db = await mongo_manager.get_async_database()
    count = await db.articles.count_documents({'\$or': [{'entities': {'\$exists': False}}, {'entities': []}]})
    print(f'{count} articles need entity extraction')
    await mongo_manager.close()

asyncio.run(check())
"

# Step 2: Test with small batch
poetry run python scripts/backfill_entities.py --limit 10 --dry-run

# Step 3: Run small batch live
poetry run python scripts/backfill_entities.py --limit 10 --yes

# Step 4: If successful, run full backfill
poetry run python scripts/backfill_entities.py --yes

# Step 5: Verify results
poetry run python -c "..." # (see Verification section)
```

## Related Documentation

- [Entity Extraction Feature](../ENTITY_EXTRACTION_FEATURE.md)
- [Entity Extraction Fix](../ENTITY_EXTRACTION_FIX_SUMMARY.md)
- [RSS Fetcher](../docs/services/rss_fetcher.md)
