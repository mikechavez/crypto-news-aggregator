# Narrative Actions Backfill Guide

## Problem
Existing narratives have empty `key_actions` arrays in their fingerprints, preventing any matches from reaching the 0.6 similarity threshold needed for narrative matching.

## Solution
The `scripts/backfill_narrative_actions.py` script extracts key actions from narrative summaries using Claude Haiku and updates the fingerprints.

## How It Works

### 1. **Identifies Narratives**
Finds all narratives where:
- `fingerprint.key_actions` doesn't exist
- `fingerprint.key_actions` is an empty array
- `fingerprint.key_actions` is null

### 2. **Extracts Actions**
For each narrative:
- Sends the summary to Claude Haiku
- Asks for 2-3 key action phrases (e.g., "filed lawsuit", "announced partnership")
- Parses the JSON response

### 3. **Updates Fingerprints**
- Updates the `fingerprint.key_actions` field with extracted actions
- Updates the `fingerprint.timestamp` to current time
- Creates a basic fingerprint if one doesn't exist

### 4. **Rate Limiting**
- Waits 1 second between API calls to avoid hitting rate limits
- Logs progress every 10 narratives

## Usage

### Prerequisites
- MongoDB connection configured
- `ANTHROPIC_API_KEY` set in environment

### Run the Script
```bash
# From project root
python scripts/backfill_narrative_actions.py
```

### Expected Output
```
2024-01-15 10:00:00 - INFO - Starting narrative actions backfill...
2024-01-15 10:00:01 - INFO - Found 45 narratives with empty key_actions
2024-01-15 10:00:02 - INFO - [1/45] Processing narrative 507f1f77bcf86cd799439011 (theme: regulatory_enforcement)
2024-01-15 10:00:03 - INFO - [1/45] ✓ Updated narrative 507f1f77bcf86cd799439011 with actions: ['filed lawsuit', 'regulatory action', 'enforcement notice']
...
2024-01-15 10:08:00 - INFO - Progress: 10/45 processed, 9 updated, 0 skipped, 1 errors
...
================================================================================
Backfill complete!
Total narratives: 45
Successfully updated: 42
Skipped (no summary): 1
Errors: 2
================================================================================
```

## Action Extraction

### Prompt Design
The script uses a carefully crafted prompt that:
- Requests 2-3 short action phrases (2-4 words each)
- Provides examples of good actions
- Requests JSON array format only
- Uses Claude Haiku for cost-effectiveness

### Example Actions
Good action phrases:
- "filed lawsuit"
- "announced partnership"
- "launched mainnet"
- "regulatory enforcement"
- "price rally"
- "network upgrade"
- "token listing"
- "security breach"

### Validation
- Ensures response is a JSON array
- Limits to maximum 3 actions
- Strips whitespace
- Filters out empty strings

## Impact on Matching

### Before Backfill
```python
fingerprint = {
    'nucleus_entity': 'SEC',
    'top_actors': ['SEC', 'Binance', 'Coinbase'],
    'key_actions': []  # Empty!
}

# Similarity calculation:
# - Actor overlap: 0.5 * 0.67 = 0.335
# - Nucleus match: 0.3 * 1.0 = 0.300
# - Action overlap: 0.2 * 0.0 = 0.000  ← Problem!
# Total: 0.635 (but actions are 0, so effectively lower)
```

### After Backfill
```python
fingerprint = {
    'nucleus_entity': 'SEC',
    'top_actors': ['SEC', 'Binance', 'Coinbase'],
    'key_actions': ['filed lawsuit', 'regulatory enforcement']  # Populated!
}

# Similarity calculation:
# - Actor overlap: 0.5 * 0.67 = 0.335
# - Nucleus match: 0.3 * 1.0 = 0.300
# - Action overlap: 0.2 * 0.5 = 0.100  ← Now contributes!
# Total: 0.735 (above 0.6 threshold!)
```

## Error Handling

### API Errors
- Logs HTTP status codes and error messages
- Continues processing remaining narratives
- Counts as error in final summary

### Missing Summaries
- Skips narratives without summaries
- Logs warning
- Counts as skipped in final summary

### JSON Parse Errors
- Logs parse errors
- Continues processing
- Counts as error in final summary

## Cost Estimation

### Claude Haiku Pricing
- Input: ~$0.25 per 1M tokens
- Output: ~$1.25 per 1M tokens

### Estimated Cost per Narrative
- Input: ~200 tokens (summary + prompt)
- Output: ~50 tokens (JSON array)
- Cost: ~$0.0001 per narrative

### Example Costs
- 50 narratives: ~$0.005 ($0.01)
- 500 narratives: ~$0.05
- 5000 narratives: ~$0.50

## Monitoring

### Progress Logs
- Every 10 narratives: progress update
- Every narrative: individual status
- Final summary: complete statistics

### Verification
After running, verify updates:
```python
# In MongoDB shell or Python
db = await mongo_manager.get_async_database()
narratives = db.narratives

# Check updated narratives
updated = await narratives.count_documents({
    "fingerprint.key_actions": {"$exists": True, "$ne": []}
})
print(f"Narratives with key_actions: {updated}")

# Sample a few
sample = await narratives.find_one({
    "fingerprint.key_actions": {"$exists": True, "$ne": []}
})
print(f"Sample fingerprint: {sample.get('fingerprint')}")
```

## Troubleshooting

### No API Key
```
ERROR - ANTHROPIC_API_KEY not configured in environment
```
**Solution**: Set `ANTHROPIC_API_KEY` in `.env` file

### Rate Limiting
```
ERROR - Anthropic API request failed: 429 - Too Many Requests
```
**Solution**: Script already includes 1-second delays. If still hitting limits, increase delay in code.

### MongoDB Connection
```
ERROR - Failed to connect to MongoDB
```
**Solution**: Verify `MONGODB_URI` in `.env` and MongoDB is running

### Empty Actions
```
WARNING - No actions extracted for narrative 507f1f77bcf86cd799439011
```
**Solution**: Check narrative summary quality. May need manual review.

## Next Steps

After backfilling:
1. **Verify Updates**: Check that narratives now have key_actions
2. **Test Matching**: Run narrative matching to see improved similarity scores
3. **Monitor Results**: Check if more narratives are being matched correctly
4. **Adjust Threshold**: If needed, fine-tune the 0.6 similarity threshold

## Related Files
- Script: `scripts/backfill_narrative_actions.py`
- Fingerprint calculation: `src/crypto_news_aggregator/services/narrative_themes.py`
- Similarity matching: `src/crypto_news_aggregator/services/narrative_service.py`
- Debug results: `MATCHING_FAILURE_DEBUG_RESULTS.md`
