# Entity Extraction 403 Forbidden Fix

## Problem
The entity extraction feature was failing with a 403 Forbidden error from the Anthropic API when trying to use the Claude Haiku 3.5 model (`claude-3-5-haiku-20241022`).

**Error Message:** "Request not allowed" with status 403

## Root Cause
The 403 error typically indicates one of the following:
1. The API key doesn't have access to the Claude Haiku 3.5 model
2. The model is not available in the API tier/plan
3. The model requires beta access that hasn't been granted

## Solution Implemented

### 1. Enhanced Error Logging
Added comprehensive error logging to capture the full API error response:
- Logs the exact status code and response text
- Parses and logs error type and message from Anthropic API
- Tracks which model was being attempted

### 2. Model Fallback Logic
Implemented automatic fallback to alternative models if Haiku 3.5 is unavailable:

**Fallback Order:**
1. `claude-3-5-haiku-20241022` (Haiku 3.5) - Primary model
2. `claude-3-5-sonnet-20241022` (Sonnet 3.5) - Fallback model
3. `claude-3-5-sonnet-20240620` (Sonnet 3.5 June) - Secondary fallback

### 3. Configuration Updates
Added new environment variable for fallback model:

```env
# Primary entity extraction model
ANTHROPIC_ENTITY_MODEL=claude-3-5-haiku-20241022

# Fallback model if primary is unavailable
ANTHROPIC_ENTITY_FALLBACK_MODEL=claude-3-5-sonnet-20241022
```

### 4. Fixed Model Name
Corrected the model name from `claude-haiku-3-5-20241022` to `claude-3-5-haiku-20241022` (proper format).

## Files Modified

1. **`src/crypto_news_aggregator/llm/anthropic.py`**
   - Added logging import and logger
   - Enhanced `extract_entities_batch()` with fallback logic
   - Added detailed error logging for 403 and other HTTP errors
   - Implemented model retry loop with fallback

2. **`src/crypto_news_aggregator/core/config.py`**
   - Fixed model name: `ANTHROPIC_ENTITY_MODEL = "claude-3-5-haiku-20241022"`
   - Added: `ANTHROPIC_ENTITY_FALLBACK_MODEL = "claude-3-5-sonnet-20241022"`

3. **`test_entity_extraction_debug.py`** (New)
   - Test script to verify entity extraction
   - Checks API key configuration
   - Tests model availability and fallback logic

## Testing

### Local Testing
Run the debug test script:
```bash
python test_entity_extraction_debug.py
```

This will:
- Verify API key is configured
- Test entity extraction with sample articles
- Show which model was successfully used
- Display extracted entities and usage statistics

### Expected Output
```
✓ ANTHROPIC_API_KEY is set: sk-ant-...xyz
✓ Entity Model: claude-3-5-haiku-20241022
✓ Fallback Model: claude-3-5-sonnet-20241022
✓ Successfully extracted entities from 2 articles

Usage Statistics:
  Model: claude-3-5-sonnet-20241022
  Input tokens: 450
  Output tokens: 120
  Total cost: $0.001800
```

## Railway Deployment

### Environment Variables to Set
Ensure these are configured in Railway:

```env
ANTHROPIC_API_KEY=your_api_key_here
ANTHROPIC_ENTITY_MODEL=claude-3-5-haiku-20241022
ANTHROPIC_ENTITY_FALLBACK_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_ENTITY_INPUT_COST_PER_1K_TOKENS=0.0008
ANTHROPIC_ENTITY_OUTPUT_COST_PER_1K_TOKENS=0.004
ENTITY_EXTRACTION_BATCH_SIZE=10
```

### Verifying the Fix on Railway

1. **Check Logs After Deployment:**
   ```bash
   railway logs
   ```

2. **Look for These Log Messages:**
   - `Attempting entity extraction with Haiku 3.5 (claude-3-5-haiku-20241022)`
   - If 403: `403 Forbidden for Haiku 3.5, trying fallback model...`
   - `Successfully extracted entities using Sonnet 3.5 (Fallback)`

3. **Trigger Entity Extraction:**
   ```bash
   curl -X POST https://your-app.railway.app/api/v1/tasks/trigger-enrichment \
     -H "X-API-Key: your_api_key"
   ```

## API Key Verification

If the fallback is consistently being used, verify your Anthropic API key has access to Haiku 3.5:

1. Check your Anthropic account tier
2. Verify model access in the Anthropic Console
3. Consider requesting beta access if needed
4. Alternatively, update `ANTHROPIC_ENTITY_MODEL` to use Sonnet directly

## Cost Implications

**Haiku 3.5 Pricing:**
- Input: $0.0008 per 1K tokens
- Output: $0.004 per 1K tokens

**Sonnet 3.5 Pricing (Fallback):**
- Input: ~$0.003 per 1K tokens (3.75x more expensive)
- Output: ~$0.015 per 1K tokens (3.75x more expensive)

If using Sonnet as fallback, costs will be approximately 3-4x higher than Haiku.

## Monitoring

The enhanced logging will show:
- Which model is being used for each batch
- Any 403 errors with full error details
- Successful fallback attempts
- Token usage and costs per batch

## Troubleshooting

### If All Models Fail
Check logs for:
```
All entity extraction models failed. Last error: {...}
```

Possible causes:
1. Invalid API key
2. API key doesn't have access to any Claude 3.5 models
3. Network connectivity issues
4. Rate limiting

### If Costs Are Higher Than Expected
If consistently using Sonnet fallback:
1. Update `ANTHROPIC_ENTITY_MODEL` to `claude-3-5-sonnet-20241022` directly
2. Update cost settings to reflect Sonnet pricing
3. Consider reducing `ENTITY_EXTRACTION_BATCH_SIZE` to lower per-request costs

## References
- [Anthropic Models Documentation](https://docs.anthropic.com/en/docs/about-claude/models)
- [Claude 3.5 Haiku Announcement](https://www.anthropic.com/news/3-5-models-and-computer-use)
- [Anthropic API Pricing](https://www.anthropic.com/pricing)
