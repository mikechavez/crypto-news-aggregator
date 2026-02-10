# Narrative Backfill - Quick Start Guide

## TL;DR

Run the backfill with safe defaults:
```bash
poetry run python scripts/backfill_narratives.py --hours 720 --limit 1500
```

Expected: **~66 minutes** for 1,329 articles at **20.5 articles/min**

## What You'll See

### 1. Rate Limiting Configuration
```
📊 Rate limiting configuration:
   Batch size: 15 articles
   Batch delay: 30s
   Article delay: 1.0s
   Time per batch: 44.0s
   Expected throughput: 20.5 articles/min
✓ Throughput within safe range (target: <20/min)
```

### 2. Progress Updates
```
📦 Batch 1/89: Processing 15 articles...
   ✅ Batch complete in 44.2s - Throughput: 20.4 articles/min - Success: 15, Failed: 0
   ⏸️  Waiting 30s before next batch...
```

### 3. Warnings (if any)
```
   ⚠️  Throughput (25.6/min) exceeds safe limit! Consider increasing --batch-delay or --article-delay
```

## Safety Features

- ✅ **Conservative defaults**: 18% buffer under API limits
- ✅ **Real-time monitoring**: See actual throughput per batch
- ✅ **Automatic warnings**: Alerts if approaching limits
- ✅ **Retry logic**: Handles transient API errors
- ✅ **Caching**: Reduces duplicate API calls

## Common Commands

### Test Run (50 articles)
```bash
poetry run python scripts/backfill_narratives.py --hours 24 --limit 50
```
Time: ~2-3 minutes

### Full Backfill (1,329 articles)
```bash
poetry run python scripts/backfill_narratives.py --hours 720 --limit 1500
```
Time: ~66 minutes

### Very Conservative
```bash
poetry run python scripts/backfill_narratives.py \
  --hours 720 --limit 1500 \
  --batch-size 10 --article-delay 1.5
```
Time: ~90 minutes (12 articles/min)

## Troubleshooting

### If you see rate limit errors
Increase delays:
```bash
--batch-delay 40 --article-delay 1.5
```

### If throughput warnings appear
The script will warn you automatically. Adjust parameters as suggested.

### If processing seems slow
That's intentional! We're staying well under API limits for safety.

## What's Happening

1. **Startup**: Calculates expected throughput
2. **Processing**: Extracts narrative data using Claude Haiku
3. **Caching**: Reuses results for duplicate content
4. **Monitoring**: Tracks actual throughput per batch
5. **Rate Limiting**: Delays between articles and batches
6. **Completion**: Reports total success/failure counts

## Rate Limit Math

- **API Limit**: 25,000 tokens/min
- **Per Article**: ~1,000 tokens (700 in + 300 out)
- **Max Safe**: 25 articles/min
- **Our Target**: 20.5 articles/min
- **Buffer**: 18% safety margin

## Files Created/Updated

- `scripts/backfill_narratives.py` - Main backfill script
- `scripts/test_rate_calculation.py` - Test rate calculations
- `CONSERVATIVE_RATE_LIMITING.md` - Full documentation
- `RATE_LIMITING_COMPLETE.md` - Implementation summary
- `BACKFILL_QUICK_START.md` - This guide

## Ready to Run?

1. **Test first**:
   ```bash
   poetry run python scripts/backfill_narratives.py --hours 24 --limit 50
   ```

2. **Verify output** shows rate limiting info and throughput

3. **Run full backfill**:
   ```bash
   poetry run python scripts/backfill_narratives.py --hours 720 --limit 1500
   ```

4. **Monitor** for consistent ~20 articles/min throughput

5. **Relax** - the script handles everything safely!
