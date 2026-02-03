# Session Start Guide - Sprint 6
**Last Updated**: 2026-02-05
**Sprint**: Sprint 6 - Cost Tracking & Monitoring

---

## 🎯 Current Sprint Goal

Implement comprehensive LLM cost tracking with accurate monitoring dashboard to ensure monthly costs stay under $10 target.

**Progress:** 3/4 tickets completed (FEATURE-028 ✅, FEATURE-029 ✅, FEATURE-030 ✅)

---

## ✅ What's Already Working

**Sprint 5 Completed (2026-02-04):**
- Briefing automation live (8 AM/8 PM EST)
- Multi-pass refinement working (avg 1-2 iterations)
- Quality prompts enhanced (no vague references)
- All tests passing (21/21)
- Ready for Railway deployment

**Current Infrastructure:**
- Briefing agent service complete and automated
- Admin API endpoints exist (`/admin/api-costs/*`, `/admin/cache/*`)
- Cost Monitor UI exists (no real data)
- MongoDB `api_costs` collection created (empty)
- MongoDB `llm_cache` collection created (for Phase 3)

**Current Problem:**
- ❌ Cost tracking not implemented (only in-memory Counter)
- ❌ No cost calculations (just call counts)
- ❌ No MongoDB writes (zero persistence)
- ❌ Dashboard shows no data
- ❌ Zero visibility into actual spending

---

## 🎫 Sprint 6 Tickets (Implementation Order)

### 1️⃣ FEATURE-028: Cost Tracking Service
**Priority:** HIGH - Do First
**Status:** ✅ COMPLETED
**File:** `/Users/mc/dev-projects/crypto-news-aggregator/docs/tickets/feature-028-cost-tracking-service`
**Estimated:** 4 hours (Completed in 1 hour)

**What was implemented:**
- ✅ Created `src/crypto_news_aggregator/services/cost_tracker.py`
- ✅ Anthropic pricing table (Haiku, Sonnet, Opus)
- ✅ Token-based cost calculation (6-decimal precision)
- ✅ MongoDB persistence to `api_costs` collection
- ✅ Cache hit/miss tracking (cached=True = $0.00)
- ✅ Test suite: `tests/services/test_cost_tracker.py` (8 tests, all passing)

**Key Classes:**
```python
class CostTracker:
    PRICING = {...}  # Anthropic pricing per 1M tokens
    
    async def track_call(
        operation: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cached: bool = False
    ) -> float
```

**Why first:** Foundation for all cost tracking. Must be in place before integration.

---

### 2️⃣ FEATURE-029: LLM Integration - Core Services
**Priority:** HIGH - Do Second
**Status:** ✅ COMPLETED (2026-02-05)
**File:** `/Users/mc/dev-projects/crypto-news-aggregator/docs/tickets/feature-029-llm-integration`
**Estimated:** 3 hours | **Actual:** 2 hours
**Dependencies:** FEATURE-028 ✅

**What was implemented:**
- ✅ Modified `src/crypto_news_aggregator/llm/optimized_anthropic.py`
  - Wrapped all API calls with new CostTracker from FEATURE-028
  - Extract token counts from `response.usage`
  - Use `asyncio.create_task()` for non-blocking tracking

- ✅ Modified `src/crypto_news_aggregator/services/briefing_agent.py`
  - Added `_get_cost_tracker()` method
  - Track all LLM calls with operation="briefing_generation"

- ✅ Created test suite: `tests/integration/test_llm_cost_tracking.py`
  - 9 tests, all passing
  - Covers all integration scenarios
  - Tests operation labeling, caching, cost calculation

**Integration Pattern:**
```python
# After LLM call
tracker = await self._get_cost_tracker()
asyncio.create_task(
    tracker.track_call(
        operation="entity_extraction",
        model=model,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        cached=False
    )
)
```

**Why second:** Integrates tracker with main LLM operations.

---

### 3️⃣ FEATURE-030: Cost Verification & Testing
**Priority:** HIGH - Do Third
**Status:** ✅ COMPLETED (2026-02-05)
**File:** `/Users/mc/dev-projects/crypto-news-aggregator/docs/tickets/feature-030-verification-testing`
**Estimated:** 2 hours | **Actual:** 1 hour
**Dependencies:** FEATURE-028 ✅, FEATURE-029 ✅

**What was implemented:**
- ✅ Created `scripts/verify_cost_tracking.py`
  - Makes test LLM call
  - Displays tracked data
  - Verifies cost calculations
  - Shows monthly summary and operation breakdown

- ✅ Created `tests/integration/test_cost_tracking_e2e.py`
  - 6 E2E tests - all passing
  - Cost tracker initialization
  - Cost calculation accuracy validation
  - Cache hit zero cost tracking
  - Pricing table completeness
  - Fractional token calculations
  - Multi-model pricing comparison

**Test Results:**
```bash
✅ test_cost_tracker_initialization - PASSED
✅ test_cost_calculation_accuracy - PASSED
✅ test_cache_hit_zero_cost - PASSED
✅ test_pricing_table_completeness - PASSED
✅ test_cost_calculation_fractional_tokens - PASSED
✅ test_multiple_model_pricing - PASSED
```

**Why third:** Validates tracking accuracy before dashboard work. ✅ Complete!

---

### 4️⃣ FEATURE-031: Dashboard Enhancement
**Priority:** MEDIUM - Do Fourth
**Status:** Backlog
**File:** `/Users/mc/dev-projects/crypto-news-aggregator/docs/tickets/FEATURE-031-dashboard-enhancement.md`
**Estimated:** 3 hours
**Dependencies:** FEATURE-028, FEATURE-029, FEATURE-030

**What to implement:**
- Create `context-owl-ui/src/components/BudgetProgress.tsx`
  - Big progress bar: month-to-date vs $10 target
  - Status indicator (🟢 On Track / 🟡 Warning / 🔴 Over Budget)
  - Days elapsed/remaining

- Create `context-owl-ui/src/components/CostAlert.tsx`
  - Alert banner if daily cost > $0.50
  - Alert banner if projected monthly > $10
  - Recommended actions

- Create `context-owl-ui/src/components/DailyTrendChart.tsx`
  - 7-day cost trend line chart
  - Recharts integration

- Update `context-owl-ui/src/pages/CostMonitor.tsx`
  - Integrate all new components
  - Fetch from `/admin/api-costs/*` endpoints
  - Auto-refresh every 30 seconds

**Why fourth:** Polish dashboard after tracking is proven accurate.

---

## 📋 Implementation Checklist

**For each ticket:**
1. Read ticket file completely at `/Users/mc/dev-projects/crypto-news-aggregator/docs/tickets/FEATURE-XXX-*.md`
2. Ticket contains full implementation code
3. Implement changes exactly as specified
4. Run tests to verify functionality
5. Commit with format: `feat(cost): [ticket description]`
6. Test manually if applicable
7. Mark ticket complete in tracking

**Testing after each ticket:**
- FEATURE-028: `pytest tests/services/test_cost_tracker.py -v`
- FEATURE-029: `pytest tests/integration/test_llm_cost_tracking.py -v`
- FEATURE-030: `poetry run python scripts/verify_cost_tracking.py`
- FEATURE-031: Open Cost Monitor UI and verify data displays

---

## 🔍 LLM Call Locations (Verified)

**Primary Integration Points:**
1. `llm/optimized_anthropic.py` - Main LLM client
   - Used by entity extraction
   - Used by narrative themes (imported)
   - Most frequent calls

2. `services/briefing_agent.py` - Briefing generation
   - 2x daily (morning/evening)
   - Uses Sonnet 4.5
   - High token count per call

3. `services/narrative_themes.py` - Narrative summaries
   - Imported by `narrative_service.py`
   - Uses `get_llm_provider("anthropic")`
   - Periodic calls

**Operation Types:**
- `entity_extraction` - Most frequent, uses Haiku
- `briefing_generation` - 2x daily, uses Sonnet 4.5
- `narrative_summary` - Periodic, uses Haiku or Sonnet
- `fingerprint_generation` - Occasional, uses Haiku

---

## 📊 Cost Projections

**Anthropic Pricing (Feb 2026):**
| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|----------------------|------------------------|
| Claude 3.5 Haiku | $0.80 | $4.00 |
| Claude 3.5 Sonnet | $3.00 | $15.00 |
| Claude Opus 4.5 | $15.00 | $75.00 |

**Expected Monthly Cost (no caching):**
- Entity extraction: ~$0.60/month
- Briefings: ~$0.90/month
- Narratives: ~$0.13/month
- **Total: ~$1.63/month** ✅

**With 90% cache hit rate:**
- **Total: ~$0.16/month** 🎉

**Alert Thresholds:**
- Daily cost > $0.50 → Warning
- Projected monthly > $10 → Danger

---

## 🚀 Deployment Notes

**Local Testing:**
```bash
# Test cost tracker
pytest tests/services/test_cost_tracker.py -v

# Test LLM integration
pytest tests/integration/test_llm_cost_tracking.py -v

# Verify tracking
poetry run python scripts/verify_cost_tracking.py

# Check database
mongosh "your_connection_string"
use crypto_news
db.api_costs.find().sort({timestamp: -1}).limit(5)
```

**Railway Deployment:**
- No changes needed (same services as Sprint 5)
- Verify environment variables: `ANTHROPIC_API_KEY`, `MONGODB_URI`
- Monitor logs for cost tracking messages
- Check dashboard after deployment

---

## 📁 Key File Locations

**Cost Tracking (New):**
- Cost tracker service: `src/crypto_news_aggregator/services/cost_tracker.py` (to create)
- Verification script: `scripts/verify_cost_tracking.py` (to create)

**LLM Integration (Modify):**
- LLM client: `src/crypto_news_aggregator/llm/optimized_anthropic.py`
- Briefing agent: `src/crypto_news_aggregator/services/briefing_agent.py`
- Narrative themes: `src/crypto_news_aggregator/services/narrative_themes.py`

**Backend (Existing):**
- Admin API: `src/crypto_news_aggregator/api/admin.py`
- MongoDB connection: `src/crypto_news_aggregator/db/mongodb.py`

**Frontend (Modify):**
- Cost Monitor page: `context-owl-ui/src/pages/CostMonitor.tsx`
- Components: `context-owl-ui/src/components/` (new components)
- Admin API client: `context-owl-ui/src/api/admin.ts`

**Tests (New):**
- `tests/services/test_cost_tracker.py`
- `tests/integration/test_llm_cost_tracking.py`
- `tests/integration/test_cost_tracking_e2e.py`

**Tickets:**
- All tickets: `/Users/mc/dev-projects/crypto-news-aggregator/docs/tickets/`
- FEATURE-028: `FEATURE-028-cost-tracking-service.md`
- FEATURE-029: `FEATURE-029-llm-integration.md`
- FEATURE-030: `FEATURE-030-verification-testing.md`
- FEATURE-031: `FEATURE-031-dashboard-enhancement.md`

---

## ⚠️ Important Notes

**Current Tracking Status:**
- `llm/tracking.py` - Only in-memory Counter (not persistent)
- No cost calculations (just counts)
- No MongoDB writes
- Dashboard has no data

**MongoDB Collections:**
- `api_costs` - Created in Phase 1, currently empty
- `llm_cache` - Created in Phase 1, for future caching

**Admin API Endpoints (Already Exist):**
- GET `/admin/api-costs/summary` - Monthly summary
- GET `/admin/api-costs/daily?days=7` - Daily breakdown
- GET `/admin/api-costs/by-model?days=30` - Model breakdown
- GET `/admin/cache/stats` - Cache performance

**Token Extraction:**
```python
# All Anthropic API responses include:
response.usage.input_tokens
response.usage.output_tokens
```

**Non-Blocking Tracking:**
```python
import asyncio

# Fire and forget - don't block LLM calls
asyncio.create_task(
    tracker.track_call(...)
)
```

---

## 📊 Success Metrics

**By End of Sprint:**
- ✅ All LLM calls tracked with accurate token counts
- ✅ MongoDB `api_costs` collection populated
- ✅ Dashboard displays accurate real-time data
- ✅ Daily cost visible and under $0.50
- ✅ Monthly projection visible and under $10
- ✅ Cache hit rate visible (baseline for Phase 3)
- ✅ All tests passing (20+ tests)

**Verification Criteria:**
- Cost calculations accurate (verified manually)
- Database writes successful
- Dashboard updates every 30 seconds
- Alert triggers correctly (test by simulation)

---

## 🎯 Sprint Context

**Previous Sprint (Sprint 5):**
- Completed 3 features in 4 days (ahead of schedule)
- Briefing automation live
- All tests passing (21/21)
- Status: ✅ COMPLETE

**Current Sprint (Sprint 6):**
- Duration: 2 weeks (Feb 5-19)
- Estimated effort: 12 hours total
- Status: 🟢 Ready to Start

**Next Sprint (Sprint 7):**
- Cost optimization with caching (Phase 3)
- Cache warming strategies
- Cost analytics dashboard

---

## 🔄 Quick Start Commands

```bash
# Start Sprint 6
cd /Users/mc/dev-projects/crypto-news-aggregator

# Read first ticket
cat docs/tickets/FEATURE-028-cost-tracking-service.md

# Create cost tracker
# (follow ticket implementation)

# Run tests
pytest tests/services/test_cost_tracker.py -v

# Verify tracking
poetry run python scripts/verify_cost_tracking.py

# Check dashboard
open http://localhost:3000/cost-monitor
```

---

## 📚 Reference Documents

**Sprint Planning:**
- Current sprint plan: `SPRINT-6-COST-TRACKING.md`
- Previous sprint: `SPRINT-5-COMPLETION.md`
- Sprint archive: `/Users/mc/Documents/claude-vault/projects/app-backdrop/development/SPRINTS.md`

**Tickets:**
- Backlog: `/Users/mc/dev-projects/crypto-news-aggregator/docs/tickets/`
- Template: `docs/tickets/ticket-template-feature.md`

**Cost Optimization:**
- Phase 1 complete: `COST_OPTIMIZATION_PHASE1_COMPLETE.md`
- Setup guide: `COST_OPTIMIZATION_SETUP.md`
- Quick reference: `COST_OPTIMIZATION_QUICKSTART.md`

**Architecture:**
- Backend patterns: `backend-service-patterns.md`
- Technical overview: `technical_overview.md`

---

## 🎓 Key Learnings from Sprint 5

**What Worked Well:**
1. Incremental approach (prompts → quality → automation)
2. Test-first mindset (21 tests created)
3. Manual verification before automation
4. Clear acceptance criteria per ticket

**Apply to Sprint 6:**
1. Build foundation first (cost tracker service)
2. Write tests alongside implementation
3. Verify accuracy with real API calls
4. Test dashboard with real data before considering done

**Cost Tracking Specifics:**
1. Use `asyncio.create_task()` for non-blocking tracking
2. Don't raise exceptions on tracking failures (log only)
3. Extract tokens from `response.usage` object
4. Track cache hits with cost = $0.00

---

**Ready to start FEATURE-028!** 🚀

Read the ticket at: `/Users/mc/dev-projects/crypto-news-aggregator/docs/tickets/FEATURE-028-cost-tracking-service.md`