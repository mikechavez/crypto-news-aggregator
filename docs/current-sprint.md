# Sprint 6: Cost Tracking & Monitoring

**Goal:** Implement comprehensive LLM cost tracking with accurate monitoring dashboard

**Sprint Duration:** 2026-02-05 to 2026-02-19 (2 weeks)

**Velocity Target:** 5 features + critical bugs

**Status:** 🟡 **99% COMPLETE** - BUG-013 fix ready, awaiting merge

---

## 🟡 ACTIVE BUGS (Being Resolved)

### BUG-012: Missing check_price_movements Import
**Priority:** P0 - CRITICAL
**Status:** ✅ FIXED (2026-02-06 01:50 UTC)
**Fix Time:** ~2 hours investigation + 10 minutes implementation

**What was fixed:**
- ✅ Removed import from `tasks/__init__.py` (line 19)
- ✅ Removed from `__all__` exports
- ✅ Removed from beat schedule
- ✅ Web service now starts successfully
- ✅ Celery worker now starts and registers tasks

**Commits:** c1bd804

---

### BUG-013: Tasks Not Registered (Discovered During BUG-012 Fix)
**Priority:** P0 - CRITICAL (blocks task processing)
**Status:** ⏳ FIX READY - Awaiting merge to main
**Related to:** BUG-012 (incomplete cleanup)

**Issue:**
Celery worker reports: `Received unregistered task of type 'crypto_news_aggregator.tasks.fetch_news.fetch_news'`

**Root Cause:**
`app.autodiscover_tasks()` includes `crypto_news_aggregator.tasks.price_monitor` module, but all Celery tasks were removed from it during BUG-012 fix.

**Fix:**
Remove price_monitor from autodiscover list in `tasks/__init__.py`

**Commits:** 618e4c7 (ready to merge)

---

## ✅ CRITICAL BUGS RESOLVED

### BUG-007 - FIXED ✅
**Root Cause:** Procfile missing Celery Beat and Worker process definitions
**Fix:** Added worker and beat processes to Procfile (commit cddbeb8)
**Status:** Verified working

### BUG-008 - FIXED ✅
**Root Cause:** Celery worker/beat can't connect to Redis broker in production
**Fix:** Updated config to accept CELERY_BROKER_URL environment override (commit aab0f16)
**Infrastructure:** Redis service added to Railway
**Status:** Verified working

### BUG-009 - FIXED ✅
**Root Cause:** Manual event loop management left dangling Motor references
**Issue:** "Event loop is closed" error on repeated briefing generation
**Fix:** Replaced with `asyncio.run()` which properly manages lifecycle
**Status:** Verified working

### BUG-010 - FIXED ✅
**Root Cause:** Multiple deployment configuration issues
**Issues Found and Fixed:**
1. **Python Path:** Added `cd src &&` to worker and beat start commands ✅
2. **SECRET_KEY:** Added SECRET_KEY environment variable to both services ✅
3. **Redis URLs:** Replaced `${REDIS_URL}` with actual connection strings ✅
**Status:** Infrastructure configured correctly

### BUG-011 - FIXED & VERIFIED ✅
**Root Cause:** Missing `get_article_service()` function in `article_service.py`
**Fix:** Added function to return singleton instance (commit edb385d)
**Status:** ✅ Verified working (function imports successfully now that BUG-012 is fixed)

---

## ✅ Completed Features

### FEATURE-028: Cost Tracking Service
**Status:** ✅ COMPLETED
**Effort:** 4h estimated, 1h actual
**Delivered:**
- CostTracker service with full pricing table
- 8 tests passing
- Accurate cost calculations verified

### FEATURE-029: LLM Integration
**Status:** ✅ COMPLETED  
**Effort:** 3h estimated, 2h actual
**Delivered:**
- All LLM calls wrapped with tracking
- Token extraction from API responses
- 9 integration tests passing

### FEATURE-030: Verification & Testing
**Status:** ✅ COMPLETED
**Effort:** 2h estimated, 1h actual
**Delivered:**
- Verification script functional
- 6 E2E tests passing
- Cost calculations validated

### FEATURE-031: Backend API Verification
**Status:** ✅ COMPLETED
**Effort:** 1h estimated, 0.5h actual
**Delivered:**
- All 7 admin endpoints tested with real MongoDB data
- Response formats verified correct for frontend
- Real cost data validated: $0.09 MTD, $0.71 projected (TARGET MET!)
- Cache performance tracked: 24.33% hit rate
- Processing statistics verified: 1,145 articles, 1,308 LLM ops

### FEATURE-032: Dashboard UI Components
**Status:** ✅ COMPLETED
**Effort:** 0.5h estimated, 0.25h actual
**Delivered:**
- CostAlert component created (`src/components/CostAlert.tsx`)
- Alert triggers: daily cost > $0.50 OR projected monthly > $10
- Integrated at top of CostMonitor page
- Dark mode support with Tailwind utilities
- Production build: ✅ Successful (462.70 KB JS, 52.82 KB CSS)

---

## Sprint Progress

### Velocity
- **Total tickets:** 5 features + 6 bugs
- **Completed:** 5/5 features (100%) + 5/6 bugs (83%)
- **Remaining:** BUG-012 (5 minute fix)
- **Time spent:** 4.75 hours features + ~7 hours debugging

### Next Session Tasks
1. 🔧 **FIX BUG-012** - Remove unused import from `api/v1/tasks.py`
2. 📋 Verify Railway deployment succeeds
3. 📋 Check worker/beat service logs (verify BUG-011 fix)
4. 📋 Run manual test: `poetry run python scripts/test_briefing_trigger.py`
5. 📋 Confirm all 12 tasks registered
6. ✅ Mark sprint complete

---

## Technical Context

### LLM Call Locations
1. `llm/optimized_anthropic.py` - Main client
2. `services/briefing_agent.py` - Briefings (2x daily)
3. `services/narrative_themes.py` - Narrative summaries

### Anthropic Pricing (Feb 2026)
| Model | Input | Output |
|-------|-------|--------|
| Haiku | $0.80/1M | $4.00/1M |
| Sonnet | $3.00/1M | $15.00/1M |
| Opus | $15.00/1M | $75.00/1M |

### Expected Monthly Cost
- Entity extraction: $0.60
- Briefings: $0.90
- Narratives: $0.13
- **Total: ~$1.63/month** ✅ (under $10 target)

---

## Success Criteria

By end of sprint:
- ✅ Briefing automation working
- ✅ All LLM calls tracked accurately
- ✅ Dashboard displays real cost data
- ✅ Alerts trigger at thresholds ($0.50/day, $10/month)
- ✅ Monthly cost under $10

---

## Bug Resolution Timeline

**BUG-007:** Identified and fixed (Procfile) - 2 hours ✅
**BUG-008:** Identified and fixed (Redis config) - 1 hour ✅
**BUG-009:** Identified and fixed (event loop) - 1 hour ✅
**BUG-010:** Identified and fixed (infrastructure) - 2 hours ✅
**BUG-011:** Identified and fixed (missing function) - 1 hour ✅
**BUG-012:** Identified (import error) - 1 hour investigation, fix pending

**Total debugging time:** ~8 hours
**Lesson:** Always check full error traces - recent changes may not be the cause

---

## Deployment Status

**Features:** ✅ All tested and verified (5/5 complete)
**Infrastructure:** ✅ Configured correctly
**Code:** 🟡 BUG-012 fix needed before deployment

### What's Ready
- ✅ Cost tracking service with accurate LLM cost tracking
- ✅ LLM integration with token extraction and tracking
- ✅ Verification and testing system
- ✅ Backend API endpoints fully verified (7/7 working)
- ✅ Dashboard UI with cost alert banner
- ✅ Celery + Redis infrastructure configured
- ✅ Briefing scheduler configured for 8 AM and 8 PM EST
- ✅ Event loop management fixed with asyncio.run()
- ✅ All environment variables set correctly
- ✅ Python path configured correctly
- ✅ BUG-011 fix applied (get_article_service function added)

### What Needs Fixing
- ⏳ BUG-013: Remove price_monitor from autodiscover (FIX READY - waiting for merge)

### Recent Completion
- ✅ BUG-012: Removed check_price_movements import
- ✅ Web service now starts
- ✅ Celery worker now starts

---

**Sprint Health:** 🟡 **99% Complete - BUG-013 fix ready, awaiting merge**

**Current Status:**
- ✅ All features implemented and tested
- ✅ All infrastructure configured
- ✅ 5 critical bugs fixed
- ✅ 1 new bug discovered and fixed (618e4c7)
- ⏳ 1 fix ready for deployment (merge to main)

**Next Step:** Merge BUG-013 fix → Railway deploys → Tasks process → Sprint DONE ✅