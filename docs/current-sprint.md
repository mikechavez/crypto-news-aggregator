# Sprint 6: Cost Tracking & Monitoring

**Goal:** Implement comprehensive LLM cost tracking with accurate monitoring dashboard

**Sprint Duration:** 2026-02-05 to 2026-02-19 (2 weeks)

**Velocity Target:** 5 features + 1 critical bug

**Status:** 🔴 **BLOCKED** - BUG-007 Critical (Briefing generation broken), 3/5 features complete

---

## CRITICAL: BUG-007 - Briefing Generation Failure
**Priority:** CRITICAL | **Status:** ✅ FIXED
**Issue:** No briefings generated today (2026-02-05) despite Sprint 5 automation
**Root Cause:** Procfile missing Celery Beat and Worker process definitions
**Fix:** Added worker and beat processes to Procfile (commit cddbeb8)
**Action:** Deploy to Railway and verify briefing generation resumes

---

## Sprint Backlog

### 🚨 Critical Bug (Do First)

#### BUG-007: Briefing Generation Not Running
**Priority:** CRITICAL
**Status:** Ready
**Estimated:** 1-2 hours

**Problem:** No briefings created today. Expected 8 AM/8 PM EST automated generation.

**Investigation needed:**
- Railway deployment status
- Celery Beat scheduler running?
- Celery Worker receiving tasks?
- Database connectivity
- Last successful briefing timestamp

**Ticket:** `/home/claude/BUG-007-briefing-generation-failure.md`

---

### ✅ Completed Features

#### FEATURE-028: Cost Tracking Service
**Status:** ✅ COMPLETED
**Effort:** 4h estimated, 1h actual

**Delivered:**
- CostTracker service with full pricing table
- 8 tests passing
- Accurate cost calculations verified

---

#### FEATURE-029: LLM Integration
**Status:** ✅ COMPLETED  
**Effort:** 3h estimated, 2h actual

**Delivered:**
- All LLM calls wrapped with tracking
- Token extraction from API responses
- 9 integration tests passing

---

#### FEATURE-030: Verification & Testing
**Status:** ✅ COMPLETED
**Effort:** 2h estimated, 1h actual

**Delivered:**
- Verification script functional
- 6 E2E tests passing
- Cost calculations validated

---

### 📋 Remaining Features

#### FEATURE-031: Backend API Verification
**Priority:** HIGH
**Status:** Backlog
**Estimated:** 1 hour
**Dependencies:** FEATURE-028, 029, 030

**What:** Test admin API endpoints with real cost data
- Verify `/admin/api-costs/summary` returns correct format
- Test `/admin/api-costs/daily?days=7`
- Confirm data ready for frontend

**Ticket:** `/home/claude/FEATURE-031-backend-api-verification.md`

---

#### FEATURE-032: Dashboard UI Components
**Priority:** LOW
**Status:** Backlog
**Estimated:** 0.5 hours (30 minutes)
**Dependencies:** FEATURE-031

**What:** Add CostAlert component to existing dashboard - **DO NOT rewrite**
- Create single CostAlert.tsx component
- Add alert banner at top of existing CostMonitor page
- Show alert if daily > $0.50 or projected monthly > $10
- Keep all existing dashboard functionality

**Why:** Existing dashboard is comprehensive - only missing threshold alerts

**Ticket:** `/home/claude/FEATURE-032-dashboard-ui-components.md`

---

## Sprint Progress

### Velocity
- **Total tickets:** 5 features + 1 bug
- **Completed:** 3/5 features (60%)
- **Blocked by:** BUG-007 (critical)
- **Time spent:** 4 hours / 10.5 estimated total

### Current Focus
1. **Fix BUG-007** (briefing generation) - CRITICAL
2. Complete FEATURE-031 (backend verification)
3. Complete FEATURE-032 (dashboard UI)

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

## Next Actions

### Immediate (This Session)
1. 🔴 **Fix BUG-007** - Briefing generation broken
2. Test FEATURE-031 - Backend API verification
3. Start FEATURE-032 - Dashboard UI if time

### This Week
1. Resolve briefing issue
2. Complete backend verification
3. Complete dashboard UI
4. Deploy and monitor

---

## Success Criteria

By end of sprint:
- ✅ Briefing automation working
- ✅ All LLM calls tracked accurately
- ✅ Dashboard displays real cost data
- ✅ Alerts trigger at thresholds ($0.50/day, $10/month)
- ✅ Monthly cost under $10

---

---

## Investigation Summary (BUG-007)

**Timeline:**
1. Explored briefing generation system - Celery tasks, Beat schedule, config all correct
2. Checked Procfile - found critical issue: **only web process defined**
3. Root cause: Railway wasn't running Celery Beat (scheduler) or Worker (executor)
4. Solution: Added worker and beat processes to Procfile
5. Deployed fix via commit cddbeb8

**Key Files Examined:**
- `src/crypto_news_aggregator/tasks/briefing_tasks.py` - Tasks correctly implemented
- `src/crypto_news_aggregator/tasks/beat_schedule.py` - Schedule correctly configured (8 AM & 8 PM EST)
- `src/crypto_news_aggregator/tasks/celery_config.py` - Timezone correctly set to America/New_York
- `Procfile` - **Was missing worker and beat processes**

**Lesson Learned:**
For distributed systems with task scheduling, ensure all required processes are defined in the deployment configuration (Procfile, docker-compose, etc). The code was correct; the deployment was incomplete.

---

**Sprint Health:** 🟡 BUG-007 Fixed, awaiting Railway deployment confirmation