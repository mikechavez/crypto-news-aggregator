# Quick Fix Reference - Entity Extraction 403

## ✅ What Was Fixed
- **Problem:** 403 Forbidden from Anthropic API for entity extraction
- **Solution:** Enhanced error logging + automatic model fallback
- **Status:** ✅ Working locally with Haiku 3.5

## 🔧 Changes Made

### 1. Code Files
- `src/crypto_news_aggregator/llm/anthropic.py` - Added fallback logic
- `src/crypto_news_aggregator/core/config.py` - Fixed model name + added fallback config

### 2. New Files
- `test_entity_extraction_debug.py` - Test script
- `docs/ENTITY_EXTRACTION_403_FIX.md` - Full documentation
- `RAILWAY_DEPLOYMENT_CHECKLIST.md` - Deployment guide
- `ENTITY_EXTRACTION_FIX_SUMMARY.md` - This summary

## 🚀 Deploy to Railway

```bash
# 1. Commit changes
git add -A
git commit -m "fix: Add fallback logic and enhanced error logging for entity extraction 403 errors"
git push origin main

# 2. Verify Railway env vars (Railway dashboard)
ANTHROPIC_API_KEY=<your_key>
ANTHROPIC_ENTITY_MODEL=claude-3-5-haiku-20241022
ANTHROPIC_ENTITY_FALLBACK_MODEL=claude-3-5-sonnet-20241022

# 3. Monitor logs
railway logs

# 4. Test
curl -X POST https://your-app.railway.app/api/v1/tasks/trigger-enrichment \
  -H "X-API-Key: your_api_key"
```

## 📊 What to Look For in Logs

**Success (Haiku):**
```
INFO - Attempting entity extraction with Haiku 3.5 (claude-3-5-haiku-20241022)
INFO - Successfully extracted entities using Haiku 3.5
```

**Success (Fallback to Sonnet):**
```
ERROR - Anthropic API request failed for Haiku 3.5: Status 403
WARNING - 403 Forbidden for Haiku 3.5, trying fallback model...
INFO - Successfully extracted entities using Sonnet 3.5 (Fallback)
```

**Failure (All models):**
```
ERROR - All entity extraction models failed. Last error: {...}
```

## 🔍 If Still Getting 403 on Railway

1. **Check API Key:** Railway might use different key than local
   ```bash
   railway variables | grep ANTHROPIC
   ```

2. **Use Same Key:** Copy the working local key to Railway

3. **Let Fallback Work:** Sonnet will work even if Haiku doesn't (3.75x cost)

## 💰 Cost

- **Haiku 3.5:** $0.002-0.005 per 10 articles
- **Sonnet 3.5:** $0.008-0.020 per 10 articles (fallback)

## 🧪 Test Locally

```bash
poetry run python test_entity_extraction_debug.py
```

## 📚 Full Docs

- **Technical:** `docs/ENTITY_EXTRACTION_403_FIX.md`
- **Deployment:** `RAILWAY_DEPLOYMENT_CHECKLIST.md`
- **Summary:** `ENTITY_EXTRACTION_FIX_SUMMARY.md`
