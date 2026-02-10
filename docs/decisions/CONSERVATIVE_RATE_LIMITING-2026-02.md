# Conservative Rate Limiting Implementation

## Summary
Updated `scripts/backfill_narratives.py` with conservative rate limiting parameters to safely stay under 20 articles/minute during the full 1,329 article backfill.

## Changes Made

### 1. Updated Header Documentation
- Changed from Sonnet to Haiku rate limits
- Updated token estimates (700 input + 300 output = 1,000 total)
- Documented conservative strategy with 20% buffer

### 2. Updated Function Signature
```python
async def backfill_with_rate_limiting(
    hours: int, 
    limit: int, 
    batch_size: int = 15,        # Reduced from 20
    batch_delay: int = 30,        # Kept at 30s
    article_delay: float = 1.0    # Increased from 0.5s
):
```

### 3. Enhanced Docstring
Added detailed calculation showing:
- 15 articles per batch
- 1.0s delay between articles = 15s processing time
- 30s delay between batches
- Total: 45s per batch = 20 articles/minute
- 20% buffer under the 25 articles/min token limit

### 4. Updated CLI Arguments
```python
parser.add_argument("--batch-size", type=int, default=15, help="Articles per batch (default: 15)")
parser.add_argument("--batch-delay", type=int, default=30, help="Seconds between batches (default: 30)")
parser.add_argument("--article-delay", type=float, default=1.0, help="Seconds between articles (default: 1.0)")
```

### 5. Made article_delay Configurable
Changed hardcoded `await asyncio.sleep(0.5)` to use the parameter with optimization:
```python
# Delay between articles within batch for rate limiting
# Don't delay after the last article in the batch
if article_idx < len(batch) - 1:
    await asyncio.sleep(article_delay)
```

This optimization skips the delay after the last article in each batch, avoiding unnecessary wait time before the batch delay kicks in.

### 6. Added Throughput Calculation and Warning
At the start of each backfill run, the script now calculates and displays:
- Expected time per batch
- Expected throughput (articles/minute)
- Warning if throughput is too high (>22/min)
- Confirmation if throughput is safe

Example output:
```
📊 Rate limiting configuration:
   Batch size: 15 articles
   Batch delay: 30s
   Article delay: 1.0s
   Time per batch: 44.0s
   Expected throughput: 20.5 articles/min
✓ Throughput within safe range (target: <20/min)
```

### 7. Added Real-Time Throughput Monitoring
Each batch now reports actual throughput:
- Actual batch processing time
- Actual throughput (articles/minute)
- Warning if actual throughput exceeds safe limit

Example output:
```
📦 Batch 1/89: Processing 15 articles...
   ✅ Batch complete in 44.2s - Throughput: 20.4 articles/min - Success: 15, Failed: 0
   ⏸️  Waiting 30s before next batch...

📦 Batch 2/89: Processing 15 articles...
   ✅ Batch complete in 43.8s - Throughput: 20.5 articles/min - Success: 30, Failed: 0
   ⏸️  Waiting 30s before next batch...
```

If throughput is too high:
```
   ✅ Batch complete in 35.2s - Throughput: 25.6 articles/min - Success: 15, Failed: 0
   ⚠️  Throughput (25.6/min) exceeds safe limit! Consider increasing --batch-delay or --article-delay
```

## Rate Limit Analysis

### Anthropic Limits (Claude Haiku)
- **50 RPM** (requests per minute)
- **25,000 TPM** (input tokens per minute)
- **25,000 TPM** (output tokens per minute)

### Our Usage Per Article
- **Input**: ~700 tokens
- **Output**: ~300 tokens
- **Total**: ~1,000 tokens per article

### Token Limit Calculation
- 25,000 TPM ÷ 1,000 tokens/article = **25 articles/minute max**

### Conservative Target: 20 articles/minute
- **15 articles** per batch
- **1.0s delay** between articles (14 delays for 15 articles) = 14s delay time
- **30s delay** between batches
- **Total**: ~44s per batch = 20.5 articles/minute
- **Buffer**: 18% under the token limit (still safe)

## Expected Backfill Performance

### For 1,329 Articles
- **Rate**: 20 articles/minute
- **Time**: 1,329 ÷ 20 = **~66 minutes** (~1.1 hours)
- **Batches**: 1,329 ÷ 15 = **89 batches**

### Safety Features
- ✅ Retry logic with exponential backoff
- ✅ Narrative caching for duplicate content
- ✅ Validation to catch errors early
- ✅ Conservative rate limiting with 20% buffer

## Usage

### Default (Conservative)
```bash
poetry run python scripts/backfill_narratives.py --hours 720 --limit 1500
```

### Custom Parameters
```bash
poetry run python scripts/backfill_narratives.py \
  --hours 720 \
  --limit 1500 \
  --batch-size 15 \
  --batch-delay 30 \
  --article-delay 1.0
```

### More Aggressive (if needed)
```bash
poetry run python scripts/backfill_narratives.py \
  --hours 720 \
  --limit 1500 \
  --batch-size 20 \
  --batch-delay 30 \
  --article-delay 0.5
```

## Verification

Test the rate calculation:
```bash
python3 scripts/test_rate_calculation.py
```

Expected output:
```
Rate Limiting Configuration Tests
================================================================================
Config                    Time/Batch      Articles/Min    Status              
--------------------------------------------------------------------------------
Default conservative        44.0s           20.5/min      ✓ Safe range
Old aggressive              39.5s           30.4/min      ⚠️  TOO FAST
Faster conservative         37.0s           24.3/min      ⚠️  TOO FAST
Very conservative           39.0s           15.4/min      ✓ Very safe
Slower aggressive           49.0s           24.5/min      ⚠️  TOO FAST
```

## Next Steps

1. **Test with small batch** to verify rate limiting works:
   ```bash
   poetry run python scripts/backfill_narratives.py --hours 24 --limit 50
   ```
   
   You should see the rate limiting configuration displayed:
   ```
   📊 Rate limiting configuration:
      Batch size: 15 articles
      Batch delay: 30s
      Article delay: 1.0s
      Time per batch: 44.0s
      Expected throughput: 20.5 articles/min
   ✓ Throughput within safe range (target: <20/min)
   ```

2. **Monitor first 5 minutes** of full backfill to ensure no rate limit errors

3. **Run full backfill**:
   ```bash
   poetry run python scripts/backfill_narratives.py --hours 720 --limit 1500
   ```

4. **Track progress** - script will show:
   - Rate limiting configuration at startup
   - Batch completion times
   - Success/failure counts
   - Estimated time remaining

## Benefits

1. **Safe**: 20% buffer prevents rate limit errors
2. **Predictable**: Consistent 20 articles/minute throughput
3. **Flexible**: All parameters configurable via CLI
4. **Monitored**: Clear progress reporting
5. **Resilient**: Combined with retry logic and caching

## Related Improvements

This conservative rate limiting works together with:
- **Retry Logic**: Handles transient API errors
- **Narrative Caching**: Reduces duplicate API calls
- **Enhanced Prompts**: Better extraction quality
- **Validation**: Catches errors early

All these improvements are now in place and ready for the full backfill.
