# Railway Deployment Checklist - Entity Extraction Fix

## ✅ Local Testing Results
- **Status:** All tests passed
- **Model Used:** `claude-3-5-haiku-20241022` (Haiku 3.5)
- **API Key:** Valid and has access to Haiku 3.5
- **Entity Extraction:** Working correctly

## 🚀 Railway Deployment Steps

### 1. Verify Environment Variables
Check that these are set in Railway:

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-api03-...
ANTHROPIC_ENTITY_MODEL=claude-3-5-haiku-20241022
ANTHROPIC_ENTITY_FALLBACK_MODEL=claude-3-5-sonnet-20241022

# Optional (for cost tracking)
ANTHROPIC_ENTITY_INPUT_COST_PER_1K_TOKENS=0.0008
ANTHROPIC_ENTITY_OUTPUT_COST_PER_1K_TOKENS=0.004
ENTITY_EXTRACTION_BATCH_SIZE=10
```

### 2. Deploy Changes
```bash
git add -A
git commit -m "fix: Add fallback logic and enhanced error logging for entity extraction 403 errors"
git push origin main
```

### 3. Monitor Railway Logs
After deployment, watch for these log messages:

**Success Pattern:**
```
INFO - Attempting entity extraction with Haiku 3.5 (claude-3-5-haiku-20241022)
INFO - Successfully extracted entities using Haiku 3.5
INFO - Batch metrics: articles_processed=10, entities_extracted=28
```

**Fallback Pattern (if 403 occurs):**
```
ERROR - Anthropic API request failed for Haiku 3.5: Status 403, Response: {...}
WARNING - 403 Forbidden for Haiku 3.5, trying fallback model...
INFO - Attempting entity extraction with Sonnet 3.5 (Fallback)
INFO - Successfully extracted entities using Sonnet 3.5 (Fallback)
```

### 4. Trigger Entity Extraction
Test the deployed service:

```bash
# Get your Railway URL
RAILWAY_URL="https://your-app.railway.app"

# Trigger enrichment
curl -X POST $RAILWAY_URL/api/v1/tasks/trigger-enrichment \
  -H "X-API-Key: your_api_key"
```

## 🔍 Troubleshooting

### If 403 Still Occurs on Railway

**Possible Causes:**
1. **Different API Key:** Railway might be using a different API key than local
2. **API Key Permissions:** The Railway API key might not have Haiku 3.5 access
3. **Environment Variable Not Set:** Check Railway dashboard for `ANTHROPIC_API_KEY`

**Verification Steps:**

1. **Check Railway Environment Variables:**
   ```bash
   railway variables
   ```

2. **Check Railway Logs for API Key:**
   Look for the masked key in logs:
   ```
   ✓ ANTHROPIC_API_KEY is set: sk-ant-...xyz
   ```

3. **Compare API Keys:**
   - Local: Check your `.env` file
   - Railway: Check Railway dashboard
   - Ensure they're the same key

4. **Test API Key Directly:**
   ```bash
   # Test with Railway's API key
   curl https://api.anthropic.com/v1/messages \
     -H "x-api-key: $RAILWAY_API_KEY" \
     -H "anthropic-version: 2023-06-01" \
     -H "content-type: application/json" \
     -d '{
       "model": "claude-3-5-haiku-20241022",
       "max_tokens": 100,
       "messages": [{"role": "user", "content": "Hello"}]
     }'
   ```

### If Fallback is Always Used

If logs show fallback is consistently used:
1. Update `ANTHROPIC_ENTITY_MODEL` to use Sonnet directly
2. Update cost settings to reflect Sonnet pricing:
   ```
   ANTHROPIC_ENTITY_INPUT_COST_PER_1K_TOKENS=0.003
   ANTHROPIC_ENTITY_OUTPUT_COST_PER_1K_TOKENS=0.015
   ```

## 📊 Cost Monitoring

**Haiku 3.5 (Preferred):**
- Input: $0.0008/1K tokens
- Output: $0.004/1K tokens
- Example batch (10 articles): ~$0.002-0.005

**Sonnet 3.5 (Fallback):**
- Input: $0.003/1K tokens (3.75x more)
- Output: $0.015/1K tokens (3.75x more)
- Example batch (10 articles): ~$0.008-0.020

## 📝 Changes Made

### Code Changes
1. **`src/crypto_news_aggregator/llm/anthropic.py`**
   - Added logging and enhanced error handling
   - Implemented model fallback logic
   - Added detailed 403 error logging

2. **`src/crypto_news_aggregator/core/config.py`**
   - Fixed model name: `claude-3-5-haiku-20241022`
   - Added fallback model config

### New Files
1. **`test_entity_extraction_debug.py`** - Debug test script
2. **`docs/ENTITY_EXTRACTION_403_FIX.md`** - Detailed fix documentation
3. **`RAILWAY_DEPLOYMENT_CHECKLIST.md`** - This file

## ✅ Pre-Deployment Checklist

- [x] Local tests pass
- [x] Enhanced error logging added
- [x] Fallback logic implemented
- [x] Configuration updated
- [ ] Railway environment variables verified
- [ ] Changes committed to git
- [ ] Deployed to Railway
- [ ] Railway logs monitored
- [ ] Entity extraction tested on Railway

## 🎯 Success Criteria

Deployment is successful when:
1. Entity extraction completes without errors
2. Logs show successful model usage (Haiku or Sonnet)
3. Entities are extracted and stored in database
4. No 403 errors in Railway logs (or fallback works correctly)
