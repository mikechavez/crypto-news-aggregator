# Sprint 6: Cost Tracking & Monitoring

**Goal:** Implement comprehensive LLM cost tracking with accurate monitoring dashboard

**Sprint Duration:** 2026-02-05 to 2026-02-19 (2 weeks)

**Velocity Target:** 4 core features for cost tracking, integration, and dashboard

**Status:** 🟡 **IN PROGRESS** - FEATURE-028 & FEATURE-029 Complete, Starting FEATURE-030

---

## Sprint Overview

### Context
Sprint 5 completed briefing automation with twice-daily generation. All LLM operations are running but **cost tracking is not functional**. Current `tracking.py` only has in-memory counters that reset on deployment and don't calculate actual costs.

### Key Objective
Implement Phase 2 of cost optimization: actual cost tracking with MongoDB persistence, token counting, and accurate pricing calculations. Deploy monitoring dashboard to ensure monthly costs stay under $10 target.

### Success Criteria
- ✅ All LLM calls tracked with accurate token counts and costs
- ✅ MongoDB `api_costs` collection populated with real data
- ✅ Cache hit/miss rates tracked accurately
- ✅ Dashboard displays accurate daily/monthly costs
- ✅ Alert system warns if daily cost exceeds $0.50
- ✅ Cost verification tests confirm tracking accuracy

---

## Sprint Backlog

### 🎯 Core Features (Priority Order)

#### FEATURE-028: Cost Tracking Service
**Priority:** HIGH - Do First
**Complexity:** Medium (4 hours estimated, 1 hour actual)
**Status:** ✅ COMPLETED

**Why First?** Foundation for all cost tracking. Must be in place before integration.

**Completion Details:**
- CostTracker service implemented with full pricing table
- 8 tests created and passing (cost calculations, database writes, aggregations)
- PR #146 created and ready for merge
- Branch: feature/cost-tracking-service

**What:** Create comprehensive cost tracking service with:
- Anthropic pricing table (Haiku, Sonnet, Opus)
- Token-based cost calculation
- MongoDB persistence to `api_costs` collection
- Cache hit/miss tracking
- Async database writes

**Files to create:**
- `src/crypto_news_aggregator/services/cost_tracker.py`
- `tests/services/test_cost_tracker.py`

**Acceptance:**
- Cost tracker calculates correct costs for all models
- Writes to `api_costs` collection with all required fields
- Handles cache hits (cost = $0.00, cached = true)
- Test suite validates pricing calculations
- All tests passing (8+ tests)

---

#### FEATURE-029: LLM Integration - Core Services
**Priority:** HIGH - Do Second
**Complexity:** Medium (3 hours estimated, 2 hours actual)
**Status:** ✅ COMPLETED

**Why Second?** Integrates tracker with main LLM operations.

**What:** Integrate cost tracking into primary LLM services:
- `llm/optimized_anthropic.py` - wrap all API calls
- `services/briefing_agent.py` - track briefing generation
- `services/narrative_themes.py` - track narrative summaries

**Files to modify:**
- `src/crypto_news_aggregator/llm/optimized_anthropic.py`
- `src/crypto_news_aggregator/services/briefing_agent.py`
- `src/crypto_news_aggregator/services/narrative_themes.py`

**Files to create:**
- `tests/integration/test_llm_cost_tracking.py`

**Acceptance:**
- All Anthropic API calls wrapped with cost tracking
- Token counts extracted from API responses
- Operation types correctly labeled
- Integration tests verify tracking
- No performance regression

---

#### FEATURE-030: Cost Verification & Testing
**Priority:** HIGH - Do Third
**Complexity:** Small (2 hours estimated, 1 hour actual)
**Status:** ✅ COMPLETED (2026-02-05)

**Why Third?** Validates tracking accuracy before dashboard work.

**Completion Details:**
- Verification script created and functional
- E2E test suite with 6 passing tests
- All cost calculations validated accurate
- Pricing table completeness verified
- Commit: d07d078

**What:** Create verification scripts and comprehensive tests:
- Manual verification script to test tracking
- End-to-end integration tests
- Cost calculation validation
- Database query verification

**Files created:**
- `scripts/verify_cost_tracking.py` - Interactive verification script
- `tests/integration/test_cost_tracking_e2e.py` - 6 passing E2E tests

**Acceptance:** ✅ All criteria met
- ✅ Verification script generates test LLM call and confirms tracking
- ✅ Script displays: operation, tokens, cost, cache status
- ✅ E2E test validates full tracking pipeline
- ✅ All cost calculations verified accurate (Haiku, Sonnet)
- ✅ Database queries return expected data
- ✅ 6/6 E2E tests passing

---

#### FEATURE-031: Dashboard Enhancement
**Priority:** MEDIUM - Do Fourth
**Complexity:** Medium (3 hours)
**Status:** Backlog

**Why Fourth?** Polish dashboard after tracking is proven accurate.

**What:** Enhance Cost Monitor UI with focused metrics:
- Primary: Month-to-date vs $10 budget (big progress bar)
- Secondary: Daily trend chart (7 days)
- Breakdown: Cost by operation type
- Breakdown: Cost by model
- Alert: Warning if daily cost > $0.50
- Cache effectiveness metrics

**Files to modify:**
- `context-owl-ui/src/pages/CostMonitor.tsx`

**Files to create:**
- `context-owl-ui/src/components/CostAlert.tsx`
- `context-owl-ui/src/components/BudgetProgress.tsx`

**Acceptance:**
- Dashboard loads real data from `/admin/api-costs/*` endpoints
- Budget progress bar shows month-to-date vs $10 target
- Alert displays if projected monthly > $10 or daily > $0.50
- Daily trend chart shows last 7 days
- Cost breakdowns display operation and model data
- Cache hit rate percentage displayed
- UI updates every 30 seconds

---

## Current Status

### ✅ Sprint 5 Completed (2026-02-04)
- Briefing automation live (8 AM/8 PM EST)
- Multi-pass refinement working
- Quality prompts enhanced
- All tests passing

### ✅ Cost Tracking Status (Updated 2026-02-05)
- **tracking.py**: Still in-memory (will be replaced by CostTracker) ⚠️
- **CostTracker service**: Implemented with full pricing table ✅
- **Cost calculation**: Verified accurate for all models ✅
- **MongoDB integration**: Ready to write data ✅
- **LLM integration**: Next step (FEATURE-029) ⏳
- **Dashboard**: Awaiting real data (FEATURE-031) ⏳

---

## Implementation Order

### Day 1-3: Foundation (FEATURE-028)
1. Create `cost_tracker.py` service
2. Define pricing tables for all models
3. Implement cost calculation logic
4. Write comprehensive test suite
5. Verify calculations with manual tests
6. Commit and deploy

### Day 4-6: Integration (FEATURE-029)
1. Integrate with `optimized_anthropic.py`
2. Integrate with `briefing_agent.py`
3. Integrate with `narrative_themes.py`
4. Test all integration points
5. Verify MongoDB writes
6. Commit and deploy

### Day 7-8: Verification (FEATURE-030)
1. Create verification script
2. Run manual test LLM calls
3. Confirm database population
4. Write E2E integration tests
5. Validate cost accuracy
6. Document findings

### Day 9-14: Dashboard (FEATURE-031)
1. Update CostMonitor.tsx with new components
2. Add budget progress bar
3. Add alert system
4. Add daily trend chart
5. Test with real data
6. Deploy to Vercel

---

## Technical Context

### LLM Call Locations

**Primary Integration Points:**
1. `llm/optimized_anthropic.py` - Main LLM client (entity extraction, all operations)
2. `services/briefing_agent.py` - Briefing generation (2x daily)
3. `services/narrative_themes.py` - Narrative summaries (imported by narrative_service.py)

**Operation Types:**
- `entity_extraction` - Most frequent, uses Haiku
- `briefing_generation` - 2x daily, uses Sonnet 4.5
- `narrative_summary` - Periodic, uses Haiku or Sonnet
- `fingerprint_generation` - Occasional, uses Haiku

### Anthropic Pricing (as of Feb 2026)

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|----------------------|------------------------|
| Claude 3.5 Haiku | $0.80 | $4.00 |
| Claude 3.5 Sonnet | $3.00 | $15.00 |
| Claude Opus 4.5 | $15.00 | $75.00 |

### Cost Projection

**Current Usage (estimated):**
- Entity extraction: ~1,500 articles/month × ~500 tokens = 750K tokens
- Briefings: 60 briefings/month × ~5K tokens = 300K tokens
- Narratives: ~200 summaries/month × ~800 tokens = 160K tokens

**Expected Monthly Cost:**
- Entity extraction (Haiku): 750K tokens × $0.80/1M = $0.60
- Briefings (Sonnet): 300K tokens × $3.00/1M = $0.90
- Narratives (Haiku): 160K tokens × $0.80/1M = $0.13
- **Total: ~$1.63/month** (well under $10 target)

With 90% cache hit rate:
- **Total: ~$0.16/month** (exceptional savings)

---

## Architecture Decisions

### Cost Tracker Design

**Service Pattern:**
```python
class CostTracker:
    """Tracks LLM API costs to MongoDB"""
    
    PRICING = {...}  # Pricing table
    
    async def track_call(
        operation: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cached: bool = False
    ) -> float:
        # Calculate cost
        # Write to MongoDB
        # Return cost
```

**Integration Pattern:**
```python
# Wrap LLM calls
try:
    response = await anthropic.messages.create(...)
    
    # Extract tokens from response
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    
    # Track cost
    await cost_tracker.track_call(
        operation="entity_extraction",
        model="claude-3-5-haiku-20241022",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached=False
    )
    
    return response
except Exception as e:
    logger.error(f"LLM call failed: {e}")
    raise
```

### Database Schema

**api_costs collection:**
```javascript
{
  timestamp: Date,          // UTC timestamp
  operation: String,        // "entity_extraction", "briefing_generation"
  model: String,            // "claude-3-5-haiku-20241022"
  input_tokens: Number,     // Token count
  output_tokens: Number,    // Token count
  cost: Number,            // Cost in USD (calculated)
  cached: Boolean,          // Cache hit = true
  cache_key: String         // Cache key if applicable
}
```

**Indexes:**
- `timestamp` (desc) - Fast recent queries
- `operation` - Filter by operation
- `model` - Filter by model
- `timestamp + operation` (compound) - Efficient aggregation

---

## Metrics & Progress

### Sprint 6 Velocity
- **Total tickets:** 4 (FEATURE-028, 029, 030, 031)
- **Estimated effort:** 12 hours total
- **Completed:** 3 (FEATURE-028 ✅, FEATURE-029 ✅, FEATURE-030 ✅)
- **In progress:** 0
- **Remaining:** 1 (FEATURE-031)
- **Progress:** 75% complete
- **Actual effort to date:** 4 hours (8 hours estimated)

### Sprint Health Indicators
- **Cost tracking foundation:** Implemented ✅ (FEATURE-028 complete)
- **LLM integration:** Ready to start (FEATURE-029)
- **Dashboard:** Waiting for real data (FEATURE-030, 031)
- **Target:** Complete integration by Feb 11

---

## Testing Strategy

### Unit Tests
- `tests/services/test_cost_tracker.py` - Cost calculation logic
- Verify pricing for all models
- Test cache hit scenarios (cost = $0.00)
- Test error handling

### Integration Tests
- `tests/integration/test_llm_cost_tracking.py` - LLM wrapper integration
- Verify token extraction from API responses
- Confirm MongoDB writes
- Validate operation labels

### End-to-End Tests
- `tests/integration/test_cost_tracking_e2e.py` - Full pipeline
- Generate test LLM call
- Verify database entry
- Validate cost calculation
- Check dashboard can query data

### Manual Verification
- `scripts/verify_cost_tracking.py` - Interactive testing
- Make test API call
- Display tracked data
- Verify accuracy

---

## Risks & Mitigation

### Risk 1: Token Count Extraction
**Impact:** High - No token data = no accurate costs
**Likelihood:** Low - Anthropic API returns usage data
**Mitigation:**
- Use `response.usage.input_tokens` and `output_tokens`
- Add error handling for missing usage data
- Log warnings if token counts unavailable

### Risk 2: Database Write Performance
**Impact:** Medium - Could slow down LLM calls
**Likelihood:** Low - Async writes are fast
**Mitigation:**
- Use async MongoDB writes (non-blocking)
- Consider fire-and-forget pattern
- Monitor write latency in production

### Risk 3: Pricing Changes
**Impact:** Medium - Calculations become inaccurate
**Likelihood:** Medium - Anthropic updates pricing periodically
**Mitigation:**
- Document pricing update date in code
- Add admin endpoint to view current pricing
- Make pricing table easy to update

### Risk 4: Cache Tracking Complexity
**Impact:** Low - Cache implementation already exists
**Likelihood:** Low - Well-defined cache system
**Mitigation:**
- Use existing `llm/cache.py` infrastructure
- Track cache hits explicitly
- Verify cache hit rate with database queries

---

## Blocked Items

None - All tickets ready to implement

---

## Next Actions

### This Session (2026-02-05)
1. ✅ Sprint planning complete
2. ✅ FEATURE-028 implemented and tested (8/8 tests passing)
3. ✅ FEATURE-029 LLM integration complete (9/9 tests passing)
4. ✅ FEATURE-030 verification & testing complete (6/6 E2E tests passing)
5. ✅ Cost tracking verified accurate across all models
6. 📝 Ready to start FEATURE-031 (Dashboard Enhancement)

### Week 1 (Feb 5-11)
1. Complete FEATURE-028 (Cost Tracker Service)
2. Complete FEATURE-029 (LLM Integration)
3. Complete FEATURE-030 (Verification & Testing)
4. Verify real cost data flowing to MongoDB

### Week 2 (Feb 12-19)
1. Complete FEATURE-031 (Dashboard Enhancement)
2. Deploy dashboard to Vercel
3. Monitor costs for 3-5 days
4. Verify budget targets
5. Document findings

---

## Success Metrics

**By End of Sprint:**
- ✅ Cost tracking implemented and verified
- ✅ MongoDB `api_costs` collection populated
- ✅ Dashboard displays accurate real-time data
- ✅ Daily cost visible and under $0.50
- ✅ Monthly projection visible and under $10
- ✅ Cache hit rate >85%
- ✅ All tests passing (20+ tests)

**Long-term Goals:**
- Monthly cost consistently under $10
- Cache hit rate maintained at 90%+
- Zero untracked LLM operations
- Real-time cost visibility

---

## External References

**Sprint Plans:**
- Current sprint: This file
- Previous sprint: `SPRINT-5-BRIEFING-SYSTEM.md`
- Sprint archive: `/Users/mc/Documents/claude-vault/projects/app-backdrop/development/SPRINTS.md`

**Tickets:**
- Backlog: `/Users/mc/Documents/claude-vault/projects/app-backdrop/development/backlog/`
- In Progress: `/Users/mc/Documents/claude-vault/projects/app-backdrop/development/in-progress/`
- Completed: `/Users/mc/Documents/claude-vault/projects/app-backdrop/development/done/`

**Key Code Files:**
- Cost tracker: `src/crypto_news_aggregator/services/cost_tracker.py` (to create)
- LLM client: `src/crypto_news_aggregator/llm/optimized_anthropic.py`
- Briefing agent: `src/crypto_news_aggregator/services/briefing_agent.py`
- Admin API: `src/crypto_news_aggregator/api/admin.py`
- Dashboard: `context-owl-ui/src/pages/CostMonitor.tsx`

---

## Sprint Health

**Status:** 🟢 Ready to Start

**Strengths:**
- Clear understanding of problem (no tracking exists)
- Admin endpoints already built
- Dashboard UI already exists
- Database schema already defined

**Watch Items:**
- Token extraction from API responses
- Database write performance
- Cache tracking accuracy
- Dashboard real-time updates

**Confidence:** High - Straightforward implementation with clear requirements