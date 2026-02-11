# RSS Fetcher Fix - Critical Bug Resolution

## 🔴 Problem Identified

**Symptom**: No new articles being fetched in Railway production for ~20 hours

**Root Cause**: Missing `OPENAI_API_KEY` attribute in Settings class

### Error Details
```
RSS ingestion cycle failed: Could not initialize any of the specified LLM providers: ['openai']. 
Last error: 'Settings' object has no attribute 'OPENAI_API_KEY'
```

### Impact
- RSS fetcher was crashing every 30 minutes
- No new articles being fetched since 2025-10-04 22:00:52
- LLM enrichment (sentiment, entities, themes) not running
- Stale data in production (28 articles in last 24h, 0 in last hour)

## ✅ Solution

### Code Fix
**File**: `src/crypto_news_aggregator/core/config.py`

Added missing `OPENAI_API_KEY` field to Settings class:

```python
# API Keys (these will be loaded from environment variables)
LLM_PROVIDER: str = "openai"  # Default provider, will be overridden by .env
OPENAI_API_KEY: str = ""  # OpenAI API key for LLM operations  # ← ADDED THIS LINE
NEWS_API_KEY: str = ""  # Kept for backward compatibility
```

### Why This Happened
The Settings class uses Pydantic's `BaseSettings` which requires all environment variables to be explicitly defined as class attributes. The `OPENAI_API_KEY` was being used by the LLM provider but was never added to the Settings class definition.

## 📊 Diagnosis Process

### 1. Checked Database for Fresh Articles
```bash
poetry run python -c "check newest articles"
```
**Result**: Newest article from 20 hours ago, 0 articles in last hour

### 2. Reviewed Background Worker Configuration
**File**: `src/crypto_news_aggregator/main.py` lines 93-115
**Result**: Configuration correct - RSS fetcher scheduled every 1800 seconds (30 min)

### 3. Checked Railway Logs
```bash
railway logs --tail 200 | grep -E "RSS|background|worker"
```

**Findings**:
- ✅ Alert detection running (every 2 minutes)
- ✅ Narrative updates running (every 10 minutes)
- ❌ RSS fetcher failing with LLM initialization error
- ❌ No "Starting background worker tasks" log

### 4. Found the Error
```
2025-10-05 00:05:00 - ERROR - RSS ingestion cycle failed: 
Could not initialize any of the specified LLM providers: ['openai']. 
Last error: 'Settings' object has no attribute 'OPENAI_API_KEY'
```

## 🚀 Deployment Plan

### Current Status
- ✅ Fix committed to `feature/vercel-deployment` branch
- ✅ Pushed to GitHub
- ⏳ Awaiting PR merge and Railway deployment

### Post-Merge Actions

1. **Merge PR to main**
   - This will trigger Railway auto-deployment
   - Backend will restart with the fix

2. **Verify Railway Environment Variables**
   ```bash
   # Check Railway dashboard that OPENAI_API_KEY is set
   # If not, add it via Railway dashboard or CLI
   ```

3. **Monitor Railway Logs**
   ```bash
   railway logs --tail 50
   ```
   
   **Look for**:
   - ✅ "Starting background worker tasks..."
   - ✅ "Starting RSS fetcher schedule with interval 1800 seconds"
   - ✅ "Running initial RSS fetch on startup..."
   - ✅ "RSS ingestion cycle completed"
   - ✅ "Enriched X article(s) with sentiment, themes, keywords, and entities"

4. **Verify Fresh Articles**
   After 5-10 minutes, check for new articles:
   ```bash
   poetry run python -c "
   from dotenv import load_dotenv
   load_dotenv()
   import asyncio
   from motor.motor_asyncio import AsyncIOMotorClient
   import os
   from datetime import datetime, timedelta, UTC
   
   async def check():
       client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))
       db = client[os.getenv('MONGODB_DB_NAME')]
       
       last_hour = datetime.now(UTC) - timedelta(hours=1)
       count = await db.articles.count_documents({'published_at': {'\$gte': last_hour}})
       
       print(f'Articles in last hour: {count}')
       
       if count > 0:
           newest = await db.articles.find_one(sort=[('published_at', -1)])
           print(f'Newest: {newest[\"title\"][:50]}')
           print(f'Published: {newest.get(\"published_at\")}')
       
       client.close()
   
   asyncio.run(check())
   "
   ```

5. **Test Production UI**
   - Open: https://context-owl-5zwt1nrjk-mikes-projects-92d90cb6.vercel.app
   - Refresh Signals page - should see fresh data
   - Check timestamps on articles

## 🔍 Additional Findings

### Background Workers Status
From Railway logs, these workers ARE running:
- ✅ **Alert Detection**: Every 2 minutes
- ✅ **Narrative Updates**: Every 10 minutes  
- ✅ **Signal Score Updates**: Running
- ❌ **RSS Fetcher**: Was failing, now fixed

### RSS Fetcher Configuration
- **Interval**: 1800 seconds (30 minutes)
- **Run Immediately**: True (fetches on startup)
- **Feeds**: Multiple crypto news sources (CoinTelegraph, CoinDesk, etc.)

## 📝 Lessons Learned

### 1. Always Define Environment Variables in Settings
When using Pydantic BaseSettings, ALL environment variables must be explicitly defined as class attributes, even if they have default values.

### 2. Monitor Background Workers
Set up alerts for background worker failures. The RSS fetcher was silently failing for 20 hours.

### 3. Check Startup Logs
The error was in the startup logs but wasn't immediately visible. Need better error alerting.

### 4. Test Environment Variable Access
Before deploying, verify that all required environment variables are:
- Defined in Settings class
- Set in Railway dashboard
- Accessible by the application

## 🎯 Success Metrics

After deployment, verify:
- [ ] RSS fetcher runs without errors
- [ ] New articles appear in database (check every 30 min)
- [ ] Articles have LLM enrichment (sentiment, entities, themes)
- [ ] Production UI shows fresh data
- [ ] No errors in Railway logs

## 🔗 Related Files

- `src/crypto_news_aggregator/core/config.py` - Settings class (FIXED)
- `src/crypto_news_aggregator/background/rss_fetcher.py` - RSS fetcher implementation
- `src/crypto_news_aggregator/main.py` - Background worker startup
- `src/crypto_news_aggregator/llm/factory.py` - LLM provider initialization

## 📞 Next Steps

1. **Create PR**: https://github.com/mikechavez/crypto-news-aggregator/pull/new/feature/vercel-deployment
2. **Review and merge** the PR
3. **Wait for Railway deployment** (2-3 minutes)
4. **Monitor logs** for successful RSS fetch
5. **Verify fresh data** in production UI
6. **Close this issue** once verified

---

**Priority**: 🔴 **CRITICAL** - Production data pipeline broken
**Status**: ✅ **FIXED** - Awaiting deployment
**ETA**: 5-10 minutes after PR merge
