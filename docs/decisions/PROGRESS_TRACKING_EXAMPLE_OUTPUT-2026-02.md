# Progress Tracking Example Output

## Full Session Example

This shows what you'll see when running the enhanced narrative backfill script.

```
$ poetry run python scripts/backfill_narratives.py --hours 48 --limit 500

🔌 Connecting to MongoDB...
🔄 Backfilling narrative data for articles from last 48h (limit: 500)...

📊 Rate limiting configuration:
   Batch size: 15 articles
   Batch delay: 30s
   Article delay: 1.0s
   Time per batch: 44.0s
   Expected throughput: 20.5 articles/min
✓ Throughput within safe range (target: <20/min)

📊 Found 500 articles needing narrative data
⏱️  Processing in 34 batches of 15
⏱️  Estimated time: 24.9 minutes

📦 Batch 1/34: Processing 15 articles...
   ✅ Batch complete in 43.2s - Success: 15/15 (100%)
   📊 Progress: 15/500 (3.0%) - Throughput: 20.8 articles/min
   ⏱️  Time: 0.7m elapsed, ~23.1m remaining
   📈 Overall: 15 successful, 0 failed (100.0% success rate)
   ⏸️  Waiting 30s before next batch...

📦 Batch 2/34: Processing 15 articles...
   ✅ Batch complete in 44.1s - Success: 14/15 (93%)
   📊 Progress: 30/500 (6.0%) - Throughput: 20.4 articles/min
   ⏱️  Time: 2.2m elapsed, ~21.8m remaining
   📈 Overall: 29 successful, 1 failed (96.7% success rate)
   ⏸️  Waiting 30s before next batch...

📦 Batch 3/34: Processing 15 articles...
   ✅ Batch complete in 43.8s - Success: 15/15 (100%)
   📊 Progress: 45/500 (9.0%) - Throughput: 20.5 articles/min
   ⏱️  Time: 3.6m elapsed, ~20.4m remaining
   📈 Overall: 44 successful, 1 failed (97.8% success rate)
   ⏸️  Waiting 30s before next batch...

📦 Batch 4/34: Processing 15 articles...
   ✅ Batch complete in 44.5s - Success: 15/15 (100%)
   📊 Progress: 60/500 (12.0%) - Throughput: 20.2 articles/min
   ⏱️  Time: 5.1m elapsed, ~19.2m remaining
   📈 Overall: 59 successful, 1 failed (98.3% success rate)
   ⏸️  Waiting 30s before next batch...

📦 Batch 5/34: Processing 15 articles...
   ✅ Batch complete in 43.9s - Success: 15/15 (100%)
   📊 Progress: 75/500 (15.0%) - Throughput: 20.5 articles/min
   ⏱️  Time: 6.6m elapsed, ~18.0m remaining
   📈 Overall: 74 successful, 1 failed (98.7% success rate)
   ⏸️  Waiting 30s before next batch...

📦 Batch 6/34: Processing 15 articles...
   ✅ Batch complete in 44.2s - Success: 15/15 (100%)
   📊 Progress: 90/500 (18.0%) - Throughput: 20.4 articles/min
   ⏱️  Time: 8.0m elapsed, ~16.7m remaining
   📈 Overall: 89 successful, 1 failed (98.9% success rate)
   ⏸️  Waiting 30s before next batch...

📦 Batch 7/34: Processing 15 articles...
   ✅ Batch complete in 43.7s - Success: 14/15 (93%)
   📊 Progress: 105/500 (21.0%) - Throughput: 20.6 articles/min
   ⏱️  Time: 9.5m elapsed, ~15.5m remaining
   📈 Overall: 103 successful, 2 failed (98.1% success rate)
   ⏸️  Waiting 30s before next batch...

📦 Batch 8/34: Processing 15 articles...
   ✅ Batch complete in 44.0s - Success: 15/15 (100%)
   📊 Progress: 120/500 (24.0%) - Throughput: 20.5 articles/min
   ⏱️  Time: 11.0m elapsed, ~14.3m remaining
   📈 Overall: 118 successful, 2 failed (98.3% success rate)
   ⏸️  Waiting 30s before next batch...

📦 Batch 9/34: Processing 15 articles...
   ✅ Batch complete in 43.8s - Success: 15/15 (100%)
   📊 Progress: 135/500 (27.0%) - Throughput: 20.5 articles/min
   ⏱️  Time: 12.4m elapsed, ~13.2m remaining
   📈 Overall: 133 successful, 2 failed (98.5% success rate)
   ⏸️  Waiting 30s before next batch...

📦 Batch 10/34: Processing 15 articles...
   ✅ Batch complete in 44.3s - Success: 15/15 (100%)
   📊 Progress: 150/500 (30.0%) - Throughput: 20.3 articles/min
   ⏱️  Time: 13.9m elapsed, ~12.0m remaining
   📈 Overall: 148 successful, 2 failed (98.7% success rate)
   ⏸️  Waiting 30s before next batch...

[... batches 11-33 continue with similar pattern ...]

📦 Batch 34/34: Processing 5 articles...
   ✅ Batch complete in 18.2s - Success: 5/5 (100%)
   📊 Progress: 500/500 (100.0%) - Throughput: 16.5 articles/min
   ⏱️  Time: 25.2m elapsed, ~0.0m remaining
   📈 Overall: 497 successful, 3 failed (99.4% success rate)

✅ Updated 497 articles with narrative data
```

## Example with Errors

```
📦 Batch 15/34: Processing 15 articles...
❌ Error processing article 507f1f77...: Connection timeout
❌ Error processing article 507f191e...: Invalid response from API
   ✅ Batch complete in 45.1s - Success: 13/15 (87%)
   📊 Progress: 225/500 (45.0%) - Throughput: 20.0 articles/min
   ⏱️  Time: 16.8m elapsed, ~10.2m remaining
   📈 Overall: 218 successful, 7 failed (96.9% success rate)
   ⏸️  Waiting 30s before next batch...
```

## Example with Rate Limit Warning

```
📦 Batch 8/34: Processing 15 articles...
   ✅ Batch complete in 39.5s - Success: 15/15 (100%)
   📊 Progress: 120/500 (24.0%) - Throughput: 22.8 articles/min
   ⏱️  Time: 10.2m elapsed, ~13.5m remaining
   📈 Overall: 118 successful, 2 failed (98.3% success rate)
   ⚠️  Throughput (22.8/min) approaching limit (25/min)
   ⏸️  Waiting 30s before next batch...
```

## Small Batch Test Example

```
$ poetry run python scripts/backfill_narratives.py --limit 30 --batch-size 5

🔌 Connecting to MongoDB...
🔄 Backfilling narrative data for articles from last 48h (limit: 30)...

📊 Rate limiting configuration:
   Batch size: 5 articles
   Batch delay: 30s
   Article delay: 1.0s
   Time per batch: 34.0s
   Expected throughput: 8.8 articles/min
✓ Throughput well under safe limit

📊 Found 30 articles needing narrative data
⏱️  Processing in 6 batches of 5
⏱️  Estimated time: 3.4 minutes

📦 Batch 1/6: Processing 5 articles...
   ✅ Batch complete in 33.8s - Success: 5/5 (100%)
   📊 Progress: 5/30 (16.7%) - Throughput: 8.9 articles/min
   ⏱️  Time: 0.6m elapsed, ~2.8m remaining
   📈 Overall: 5 successful, 0 failed (100.0% success rate)
   ⏸️  Waiting 30s before next batch...

📦 Batch 2/6: Processing 5 articles...
   ✅ Batch complete in 34.1s - Success: 5/5 (100%)
   📊 Progress: 10/30 (33.3%) - Throughput: 8.8 articles/min
   ⏱️  Time: 1.7m elapsed, ~2.3m remaining
   📈 Overall: 10 successful, 0 failed (100.0% success rate)
   ⏸️  Waiting 30s before next batch...

📦 Batch 3/6: Processing 5 articles...
   ✅ Batch complete in 33.9s - Success: 5/5 (100%)
   📊 Progress: 15/30 (50.0%) - Throughput: 8.8 articles/min
   ⏱️  Time: 2.8m elapsed, ~1.7m remaining
   📈 Overall: 15 successful, 0 failed (100.0% success rate)
   ⏸️  Waiting 30s before next batch...

📦 Batch 4/6: Processing 5 articles...
   ✅ Batch complete in 34.2s - Success: 5/5 (100%)
   📊 Progress: 20/30 (66.7%) - Throughput: 8.8 articles/min
   ⏱️  Time: 3.9m elapsed, ~1.1m remaining
   📈 Overall: 20 successful, 0 failed (100.0% success rate)
   ⏸️  Waiting 30s before next batch...

📦 Batch 5/6: Processing 5 articles...
   ✅ Batch complete in 33.8s - Success: 5/5 (100%)
   📊 Progress: 25/30 (83.3%) - Throughput: 8.9 articles/min
   ⏱️  Time: 5.0m elapsed, ~0.6m remaining
   📈 Overall: 25 successful, 0 failed (100.0% success rate)
   ⏸️  Waiting 30s before next batch...

📦 Batch 6/6: Processing 5 articles...
   ✅ Batch complete in 34.0s - Success: 5/5 (100%)
   📊 Progress: 30/30 (100.0%) - Throughput: 8.8 articles/min
   ⏱️  Time: 6.1m elapsed, ~0.0m remaining
   📈 Overall: 30 successful, 0 failed (100.0% success rate)

✅ Updated 30 articles with narrative data
```

## Key Observations

### Progress Tracking
- **Percentage updates**: Shows exact progress (3.0%, 6.0%, 9.0%, etc.)
- **Dynamic estimates**: Time remaining decreases as processing continues
- **Accurate predictions**: After a few batches, estimates stabilize

### Success Rate Tracking
- **Per-batch**: Shows immediate success rate for each batch
- **Overall**: Cumulative success rate across all batches
- **Trend visibility**: Easy to spot if success rate is declining

### Throughput Monitoring
- **Real-time**: Shows actual articles/min for each batch
- **Consistency**: Should stay around 20-21 articles/min
- **Warnings**: Alerts if approaching rate limits

### Time Management
- **Elapsed time**: Shows how long the process has been running
- **Remaining time**: Estimates when the process will complete
- **Planning**: Helps schedule other tasks or breaks

### Error Visibility
- **Immediate feedback**: Errors logged as they occur
- **Article identification**: Shows first 8 chars of article ID
- **Impact tracking**: Shows how errors affect overall success rate

## What Makes This Better

### Before (Old Output)
```
Found 500 articles needing narrative data
Processing in batches of 15 with 30s delays
Estimated time: 24.9 minutes

Batch 1/34: Processing 15 articles...
   ✅ Batch complete in 43.2s - Throughput: 20.8 articles/min - Success: 15, Failed: 0
   ⏸️  Waiting 30s before next batch...
```

### After (New Output)
```
📊 Found 500 articles needing narrative data
⏱️  Processing in 34 batches of 15
⏱️  Estimated time: 24.9 minutes

📦 Batch 1/34: Processing 15 articles...
   ✅ Batch complete in 43.2s - Success: 15/15 (100%)
   📊 Progress: 15/500 (3.0%) - Throughput: 20.8 articles/min
   ⏱️  Time: 0.7m elapsed, ~23.1m remaining
   📈 Overall: 15 successful, 0 failed (100.0% success rate)
   ⏸️  Waiting 30s before next batch...
```

### Improvements
1. **Visual hierarchy**: Emojis make sections easy to scan
2. **More metrics**: Progress %, time remaining, success rate
3. **Better formatting**: Multi-line output with clear labels
4. **Percentages**: Easier to understand than raw numbers
5. **Time tracking**: Both elapsed and remaining time
6. **Success rate**: Immediate visibility of data quality
