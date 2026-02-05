bug-008-celery-redis-configuration-missing

---
id: BUG-008
type: bug
status: open
priority: critical
severity: critical
created: 2026-02-05
updated: 2026-02-05
---

# BUG-008: Celery Briefing Generation Not Running (Redis Configuration Missing)

## Problem
Briefings are not being generated automatically at scheduled times (8 AM and 8 PM EST) despite the Celery worker and beat processes being defined in the Procfile and code being correct.

## Expected Behavior
Briefings should be automatically generated daily:
- Morning briefing at 8:00 AM EST
- Evening briefing at 8:00 PM EST
- Process should run in the background via Celery Beat scheduler and worker

## Actual Behavior
No briefings are generated at scheduled times. The Procfile defines worker and beat processes, but they fail to connect to the message broker.

## Steps to Reproduce
1. Deploy application to Railway with Procfile (worker and beat processes)
2. Wait for scheduled briefing time (8 AM or 8 PM EST)
3. Check MongoDB for new briefing documents
4. Observe: No new briefing created
5. Check Railway logs for Celery worker/beat process errors
6. Observe: Connection errors to `localhost:6379` (Redis)

## Environment
- Environment: production (Railway)
- User impact: high (core feature completely broken)
- Affects: All users relying on automated briefing generation

## Screenshots/Logs
Railway logs would show connection errors like:
```
Error: Cannot connect to redis://localhost:6379/0
ConnectionError: Error 111 connecting to localhost:6379
```

---

## Resolution

**Status:** In Progress
**Root Cause Identified:** YES - Redis connection not configured for production

### Root Cause
The Celery worker and beat processes require a message broker (Redis) to communicate and schedule tasks.

**The Issue:**
1. `.env` file doesn't define `CELERY_BROKER_URL`, `REDIS_HOST`, or `REDIS_PORT`
2. Configuration defaults to `redis://localhost:6379/0` for local development
3. Railway doesn't provide Redis by default - this address doesn't exist in production
4. Celery worker and beat fail to connect to the broker on startup
5. Tasks cannot be scheduled or executed

**Code Location:** `src/crypto_news_aggregator/core/config.py` (lines 77-88)

### Changes Made
1. **Updated Config (config.py)**:
   - Changed `CELERY_BROKER_URL` from f-string with hardcoded defaults to empty string allowing environment override
   - Changed `CELERY_RESULT_BACKEND` from f-string with hardcoded defaults to empty string allowing environment override
   - Updated model validator to build Celery URLs only if environment variables not provided (lines 178-182)
   - This allows production deployments to override with proper Redis URLs

2. **Configuration Flexibility**:
   - Local development: Falls back to `redis://localhost:6379/0` if env vars not set
   - Production (Railway): Can now accept `CELERY_BROKER_URL` from environment
   - Supports external Redis services (Upstash, etc.)

### Testing
1. **Local Testing**: Verify briefing tasks still work with default localhost:6379
   - `pytest tests/services/test_briefing_agent.py`

2. **Production Deployment**:
   - Add Redis to Railway (via plugin or external service)
   - Set `CELERY_BROKER_URL` environment variable
   - Verify worker and beat processes start: `railway ps`
   - Monitor logs for successful broker connection
   - Wait for next scheduled briefing time and verify generation

### Files Changed
- `src/crypto_news_aggregator/core/config.py` - Added environment variable override support for Celery URLs

### Next Steps
1. Deploy configuration changes
2. Add Redis to Railway deployment:
   - **Option A**: Use Railway Redis plugin (recommended)
   - **Option B**: Use Upstash Redis (https://upstash.com/)
3. Verify briefing generation resumes at next scheduled time
