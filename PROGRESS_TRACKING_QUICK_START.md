# Progress Tracking Quick Start Guide

## What's New
The narrative backfill script now provides **comprehensive progress tracking** with:
- ✅ Real-time progress percentage
- ✅ Time elapsed and estimated time remaining
- ✅ Success/failure statistics per batch and overall
- ✅ Throughput monitoring
- ✅ Error handling with detailed logging

## Running the Script

### Basic Usage
```bash
poetry run python scripts/backfill_narratives.py --hours 48 --limit 500
```

### With Custom Rate Limiting
```bash
poetry run python scripts/backfill_narratives.py \
  --hours 48 \
  --limit 500 \
  --batch-size 15 \
  --batch-delay 30 \
  --article-delay 1.0
```

## Understanding the Output

### 1. Initial Configuration
```
📊 Rate limiting configuration:
   Batch size: 15 articles
   Batch delay: 30s
   Article delay: 1.0s
   Time per batch: 44.0s
   Expected throughput: 20.5 articles/min
✓ Throughput within safe range (target: <20/min)
```
Shows your rate limiting settings and expected performance.

### 2. Processing Summary
```
📊 Found 500 articles needing narrative data
⏱️  Processing in 34 batches of 15
⏱️  Estimated time: 24.9 minutes
```
Total articles found and estimated completion time.

### 3. Per-Batch Progress
```
📦 Batch 5/34: Processing 15 articles...
   ✅ Batch complete in 43.2s - Success: 15/15 (100%)
   📊 Progress: 75/500 (15.0%) - Throughput: 20.8 articles/min
   ⏱️  Time: 3.6m elapsed, ~20.4m remaining
   📈 Overall: 73 successful, 2 failed (97.3% success rate)
   ⏸️  Waiting 30s before next batch...
```

**Line-by-line breakdown:**
- **Line 1**: Current batch number and size
- **Line 2**: Batch completion time and success rate
- **Line 3**: Overall progress percentage and current throughput
- **Line 4**: Time elapsed and estimated time remaining
- **Line 5**: Cumulative success/failure counts and overall success rate
- **Line 6**: Waiting period before next batch

### 4. Error Handling
```
❌ Error processing article 507f1f77...: Connection timeout
```
Individual article errors are logged with article ID prefix.

### 5. Rate Limit Warnings
```
⚠️  Throughput (23.5/min) approaching limit (25/min)
```
Warns when throughput gets close to API rate limits.

## Key Metrics Explained

### Progress Percentage
- **Formula**: `(articles_processed / total_articles) * 100`
- **Example**: `75/500 (15.0%)` means 75 articles processed out of 500 total

### Time Remaining
- **Calculation**: Based on actual average time per article
- **Updates dynamically**: Gets more accurate as more articles are processed
- **Example**: `~20.4m remaining` means approximately 20.4 minutes left

### Success Rate
- **Formula**: `(successful / (successful + failed)) * 100`
- **Example**: `73 successful, 2 failed (97.3% success rate)`
- **Ideal**: Should stay above 95%

### Throughput
- **Measurement**: Articles processed per minute
- **Target**: 20-22 articles/min (safe under 25/min API limit)
- **Warning threshold**: >22 articles/min triggers warning

## Monitoring Tips

### 1. Watch the Success Rate
- **Good**: 95-100% success rate
- **Investigate**: <95% success rate (check error logs)
- **Action**: If consistently low, check API connectivity or article data quality

### 2. Monitor Throughput
- **Safe**: 18-22 articles/min
- **Warning**: 22-25 articles/min (approaching limit)
- **Danger**: >25 articles/min (may hit rate limits)

### 3. Track Time Estimates
- **First few batches**: Estimates may fluctuate
- **After 5+ batches**: Estimates stabilize and become accurate
- **Use for planning**: Schedule other tasks based on remaining time

### 4. Check for Errors
- **Occasional errors**: Normal (network hiccups, malformed articles)
- **Frequent errors**: Investigate (API issues, data problems)
- **Pattern errors**: Check specific article IDs in logs

## Example Session

```bash
$ poetry run python scripts/backfill_narratives.py --hours 48 --limit 100

🔌 Connecting to MongoDB...
🔄 Backfilling narrative data for articles from last 48h (limit: 100)...

📊 Rate limiting configuration:
   Batch size: 15 articles
   Batch delay: 30s
   Article delay: 1.0s
   Time per batch: 44.0s
   Expected throughput: 20.5 articles/min
✓ Throughput within safe range (target: <20/min)

📊 Found 100 articles needing narrative data
⏱️  Processing in 7 batches of 15
⏱️  Estimated time: 5.1 minutes

📦 Batch 1/7: Processing 15 articles...
   ✅ Batch complete in 43.8s - Success: 15/15 (100%)
   📊 Progress: 15/100 (15.0%) - Throughput: 20.5 articles/min
   ⏱️  Time: 0.7m elapsed, ~4.0m remaining
   📈 Overall: 15 successful, 0 failed (100.0% success rate)
   ⏸️  Waiting 30s before next batch...

📦 Batch 2/7: Processing 15 articles...
   ✅ Batch complete in 44.2s - Success: 15/15 (100%)
   📊 Progress: 30/100 (30.0%) - Throughput: 20.4 articles/min
   ⏱️  Time: 2.0m elapsed, ~3.3m remaining
   📈 Overall: 30 successful, 0 failed (100.0% success rate)
   ⏸️  Waiting 30s before next batch...

[... continues for remaining batches ...]

✅ Updated 100 articles with narrative data
```

## Troubleshooting

### Time Estimate Seems Off
- **Cause**: First few batches used for calibration
- **Solution**: Wait for 3-5 batches, estimates will stabilize

### Throughput Too High
- **Warning**: `⚠️  Throughput (23.5/min) approaching limit`
- **Solution**: Increase `--batch-delay` or `--article-delay`
- **Example**: `--batch-delay 35` or `--article-delay 1.5`

### Low Success Rate
- **Check**: Error messages in logs
- **Common causes**: API timeouts, malformed articles, rate limiting
- **Solution**: Investigate specific article IDs, check API status

### Script Seems Stuck
- **Check**: Look for batch completion messages
- **Normal**: Long pauses between batches (30s default)
- **Abnormal**: No output for >2 minutes (check logs, network)

## Performance Tuning

### Faster Processing (Use Carefully!)
```bash
# Reduce delays (watch for rate limit warnings!)
poetry run python scripts/backfill_narratives.py \
  --batch-size 20 \
  --batch-delay 25 \
  --article-delay 0.8
```

### Safer Processing (For Large Batches)
```bash
# Increase delays for extra safety margin
poetry run python scripts/backfill_narratives.py \
  --batch-size 12 \
  --batch-delay 35 \
  --article-delay 1.2
```

### Testing (Small Batch)
```bash
# Test with small batch to verify everything works
poetry run python scripts/backfill_narratives.py \
  --limit 30 \
  --batch-size 5
```

## What to Expect

### For 500 Articles
- **Batches**: ~34 batches of 15 articles
- **Time**: ~25-30 minutes
- **Success rate**: 95-100%
- **Throughput**: 18-22 articles/min

### For 1000 Articles
- **Batches**: ~67 batches of 15 articles
- **Time**: ~50-60 minutes
- **Success rate**: 95-100%
- **Throughput**: 18-22 articles/min

## Best Practices

1. **Start small**: Test with `--limit 30` first
2. **Monitor first few batches**: Ensure success rate is high
3. **Watch throughput**: Should stay under 22 articles/min
4. **Plan accordingly**: Use time estimates for scheduling
5. **Check logs**: Review any error messages
6. **Run during off-peak**: Less likely to hit rate limits

## Support

If you encounter issues:
1. Check the error messages in the output
2. Review the `PROGRESS_TRACKING_IMPLEMENTATION.md` for technical details
3. Verify API credentials and connectivity
4. Check MongoDB connection
5. Review rate limiting configuration
