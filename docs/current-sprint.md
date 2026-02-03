# Current Sprint: Sprint 5 (Briefing System Launch)

**Goal:** Launch automated briefing generation with high-quality analysis twice daily

**Sprint Duration:** 2026-02-01 to 2026-02-15 (2 weeks)

**Velocity Target:** 3 core features for briefing automation and quality

**Status:** 🟢 **READY TO START** - All dependencies clear, implementation-ready tickets

---

## Sprint Overview

### Context
Sprint 4 completed UX enhancements with article pagination, skeleton loaders, error handling, and progress indicators. All features are production-ready and merged. Sprint 5 pivots to briefing system launch.

### Key Objective
Get automated briefings generating twice daily (8 AM/8 PM EST) with consistent high-quality analysis. The briefing agent service exists and works, but needs:
1. Multi-pass refinement for quality assurance
2. Celery Beat automation for scheduled generation
3. Prompt enhancements for better output

### Success Criteria
- ✅ Briefings auto-generate at 8 AM EST and 8 PM EST
- ✅ Quality consistently meets publication standards
- ✅ No hallucinations or vague entity references
- ✅ Each narrative explains "why it matters"
- ✅ System handles failures gracefully with retries

---

## Sprint Backlog

### 🎯 Core Features (Priority Order)

#### FEATURE-027: Prompt Quality Enhancement
**Priority:** HIGH - Do First
**Complexity:** Small (2 hours)
**Status:** Backlog

**Why First?** Improves prompt quality before we start automated generation. Get the foundation right.

**What:** Enhance system and critique prompts with:
- Specific entity reference rules (no vague "the platform")
- "Why it matters" enforcement
- Good/bad example demonstrations
- Stronger anti-hallucination checks

**Files to modify:**
- `src/crypto_news_aggregator/services/briefing_agent.py` (lines 338-391, 463-500)
- Create: `tests/test_briefing_prompts.py`

**Acceptance:**
- System prompt includes entity reference rules
- Critique checks for vague references
- Test briefing has no vague pronouns
- All narratives explain significance

---

#### FEATURE-025: Multi-Pass Refinement
**Priority:** HIGH - Do Second  
**Complexity:** Medium (3 hours)
**Status:** Backlog

**Why Second?** Builds on prompt improvements. Ensures quality loop before automation.

**What:** Implement iterative refinement (2-3 passes max):
- Generate → Critique → Refine → Repeat
- Stop when quality passes OR max iterations
- Track iteration count in metadata
- Reduce confidence score if max iterations hit

**Files to modify:**
- `src/crypto_news_aggregator/services/briefing_agent.py` (lines 294-336, 650-684)
- Create: `tests/test_briefing_multi_pass.py`

**Acceptance:**
- Refinement continues up to max_iterations (default: 2)
- Stops early if quality check passes
- Iteration count saved in briefing metadata
- Confidence score capped at 0.6 if max iterations hit
- Tests validate multi-pass behavior

---

#### FEATURE-026: Celery Beat Automation
**Priority:** HIGH - Do Third
**Complexity:** Medium (4 hours)
**Status:** Backlog

**Why Third?** Deploy automation after quality systems in place. Final piece for launch.

**What:** Set up scheduled briefing generation:
- Morning briefing: 8:00 AM EST (13:00 UTC)
- Evening briefing: 8:00 PM EST (01:00 UTC)
- Celery Beat tasks with retry logic
- Railway deployment configuration

**Files to create:**
- `src/crypto_news_aggregator/tasks/briefing_tasks.py`
- `tests/test_briefing_tasks.py`

**Files to modify:**
- `src/crypto_news_aggregator/tasks/beat_schedule.py`
- `src/crypto_news_aggregator/tasks/celery_config.py`
- Railway deployment config (Procfile or railway.toml)

**Acceptance:**
- Morning task registered and runs at 13:00 UTC
- Evening task registered and runs at 01:00 UTC
- Tasks retry 3x with exponential backoff
- Failures logged to application logs
- Railway shows 3 services: web, worker, beat
- First automated briefings generated successfully

---

## Current Status

### ✅ Completed
- **[FEATURE-027]** Prompt Quality Enhancement - ✅ COMPLETED (2026-02-01)
  - System prompt enhanced with entity references and why-it-matters rules
  - Critique prompt checks for vague entity references
  - Test suite created (3 tests passing)
  - Commit: `228fb48`

- **[FEATURE-025]** Multi-Pass Refinement - ✅ COMPLETED (2026-02-04)
  - Iterative refinement loop with max_iterations (default: 2)
  - Early stopping when quality check passes
  - Iteration tracking in metadata
  - Confidence score penalties if max iterations hit
  - Test suite created (3 tests, all passing)
  - Commits: `84d0a3f`, `abad1e7`

### Ready to Implement
- **[FEATURE-026]** Celery Beat Automation - Ready to implement

### Bug Fixes & Verification (Session 2)
✅ **BUG-006 RESOLVED (2026-02-02):**
- Market event detector implemented to identify liquidation cascades
- Briefing now includes high-impact market shocks in top 8 narratives
- FEATURE-025 is now unblocked and ready to implement
- Commit: 8b735a0

✅ **Entity Handling Bug Fixed (2026-02-02):**
- Issue: Market event detector crashed on entity extraction (unhashable type)
- Cause: Articles have entities as dicts with `name` field, not plain strings
- Fix: Added type checking in _detect_liquidation_cascade, _detect_market_crash, _detect_exploit_event
- Impact: Market detector now works with real database data
- All market shock tests passing: 11/12 (1 skipped - requires MongoDB)

### Manual Verification Complete (2026-02-03)
✅ Live briefing generated and tested
- Briefing quality: 0.92 confidence score (excellent)
- 15 narratives analyzed, 8 selected for inclusion
- 5 distinct patterns detected
- No high-impact market shocks in current 24h window (system operating correctly)
- Market event detector verified working as designed

---

## Implementation Order

**Day 1-2: Foundation (FEATURE-027)**
1. Start with FEATURE-027 (prompt enhancement)
2. Test prompt changes with manual generation
3. Verify entity references and "why it matters"
4. Commit and deploy

**Day 3-4: Quality Loop (FEATURE-025)**
1. Implement multi-pass refinement
2. Write and run tests
3. Test with real briefing generation
4. Monitor iteration counts and confidence scores
5. Commit and deploy

**Day 5-7: Automation (FEATURE-026)**
1. Create Celery Beat tasks
2. Update beat schedule configuration
3. Test locally with manual triggers
4. Deploy to Railway with multi-service setup
5. Monitor first scheduled runs
6. Verify both 8 AM and 8 PM generations

**Day 8-14: Monitor & Tune**
1. Watch automated briefing quality
2. Review user feedback
3. Tune prompts if needed
4. Adjust narrative selection if needed
5. Document any issues for future sprints

---

## Technical Context

### Existing Infrastructure

**Briefing Agent Service:** ✅ Complete
- File: `src/crypto_news_aggregator/services/briefing_agent.py`
- Functions: `generate_morning_briefing()`, `generate_evening_briefing()`
- Features: Memory manager, pattern detector, LLM integration, self-refine
- Cost: ~$0.03-0.05 per briefing with Sonnet 4.5

**API Endpoints:** ✅ Complete
- GET `/api/v1/briefing/latest` - Get most recent briefing
- POST `/api/v1/briefing/generate` - Manual generation (for testing)
- GET `/api/v1/briefing/next` - Next scheduled time
- Feedback system integrated

**Frontend:** ✅ Complete
- Page: `context-owl-ui/src/pages/Briefing.tsx`
- Displays morning/evening briefings
- Placeholder while agent being set up
- Recommendation links to narratives

### What We're Building

**Quality System:**
- Multi-pass refinement ensures publication quality
- Enhanced prompts prevent common issues
- Confidence scoring flags low-quality attempts

**Automation:**
- Celery Beat schedules twice-daily generation
- Retry logic handles transient failures
- Monitoring via application logs

**Cost Projection:**
- 2 briefings/day × $0.04 avg = $0.08/day
- ~$2.40/month (well within budget)
- Multi-pass may increase to $0.06/briefing = $3.60/month

---

## Architecture Decisions

### Sprint 5 Architecture: Quality-First Automation

**Multi-Pass Refinement Strategy:**
- Max 2 iterations by default (balance quality vs cost)
- Early stopping when quality check passes
- Confidence score penalty if max iterations hit
- Iteration count tracked in metadata for analysis

**Prompt Enhancement Strategy:**
- Entity-specific rules prevent vague references
- "Why it matters" mandatory for each development
- Good/bad examples guide LLM output
- Critique prompt includes entity vagueness check

**Automation Strategy:**
- Celery Beat for reliability (vs cron)
- UTC scheduling (13:00 and 01:00) auto-adjusts for DST
- Exponential backoff retries (3 attempts)
- Task expiration after 1 hour (prevents stale execution)

**Deployment Strategy:**
- Railway multi-service: web + worker + beat
- Separate processes for isolation
- Beat worker runs schedules
- Worker executes tasks
- Web serves API

---

## Metrics & Progress

### Sprint 5 Velocity
- **Total tickets:** 3 (FEATURE-025, 026, 027)
- **Estimated effort:** 9 hours total
- **Completed:** 2 (FEATURE-027: 2 hours, FEATURE-025: 2 hours)
- **In progress:** 0
- **Remaining:** 1 (FEATURE-026)
- **Velocity:** 4 hours completed, 1 session (avg 2 hours/session)

### Sprint Health Indicators
- **Briefing generation:** Manual only (via `/generate` endpoint)
- **Quality system:** Single-pass refine (to be enhanced)
- **Automation:** Not deployed (to be implemented)
- **Target:** Automated twice-daily by end of sprint

---

## Testing Strategy

### Unit Tests
- `tests/test_briefing_multi_pass.py` - Multi-pass refinement logic
- `tests/test_briefing_tasks.py` - Celery task execution
- `tests/test_briefing_prompts.py` - Prompt quality checks

### Integration Tests
- Manual briefing generation via API
- Celery task manual trigger
- Full briefing generation workflow

### Production Monitoring
- Railway logs for task execution
- MongoDB `daily_briefings` collection
- Confidence scores and iteration counts
- First automated runs verification

---

## Risks & Mitigation

### Risk 1: Railway Multi-Service Deployment
**Impact:** High - Blocks automation
**Likelihood:** Medium - Railway config may differ
**Mitigation:**
- Check Railway documentation early
- Test multi-service locally first
- Have fallback to single-process with supervisor

### Risk 2: Timezone Confusion (EST vs UTC)
**Impact:** Medium - Wrong generation times
**Likelihood:** Low - Using UTC internally
**Mitigation:**
- All schedules in UTC
- Document EST → UTC conversions clearly
- Test with manual triggers at correct times

### Risk 3: LLM Quality Variability
**Impact:** Medium - Inconsistent briefings
**Likelihood:** Medium - LLMs can vary
**Mitigation:**
- Multi-pass refinement catches issues
- Confidence scoring flags problems
- Human review first week of automation

### Risk 4: Cost Overrun
**Impact:** Low - Budget can handle it
**Likelihood:** Low - Well-estimated
**Mitigation:**
- Monitor costs daily first week
- LLM tracking already in place
- Can tune max_iterations if needed

---

## Blocked Items

None - All tickets ready to implement

---

## Next Actions

### This Session (2026-02-01)
1. ✅ Sprint planning complete
2. 📝 Ready to start FEATURE-027 (Prompt Enhancement)
3. Implement prompt changes per ticket
4. Test with manual generation
5. Commit and deploy to Railway
6. Move to FEATURE-025

### Week 1 (Feb 1-7)
1. Complete FEATURE-027 (Prompt Enhancement)
2. Complete FEATURE-025 (Multi-Pass Refinement)
3. Complete FEATURE-026 (Celery Beat Automation)
4. Deploy to Railway with multi-service
5. Monitor first automated runs

### Week 2 (Feb 8-14)
1. Monitor briefing quality daily
2. Review and adjust prompts if needed
3. Tune narrative selection if needed
4. Gather user feedback
5. Document learnings for future sprints

---

## External References

**Project Structure:**
- Sprint plans: `/Users/mc/Documents/claude-vault/projects/app-backdrop/development/SPRINTS.md`
- Backlog: `/Users/mc/Documents/claude-vault/projects/app-backdrop/development/backlog/`
- In Progress: `/Users/mc/Documents/claude-vault/projects/app-backdrop/development/in-progress/`
- Completed: `/Users/mc/Documents/claude-vault/projects/app-backdrop/development/done/`

**Key Documents:**
- Vision: `/Users/mc/Documents/claude-vault/projects/app-backdrop/planning/vision.md`
- Roadmap: `/Users/mc/Documents/claude-vault/projects/app-backdrop/planning/roadmap.md`
- Architecture: `/Users/mc/dev-projects/crypto-news-aggregator/docs/decisions/`

**Code References:**
- Briefing agent: `src/crypto_news_aggregator/services/briefing_agent.py`
- Briefing API: `src/crypto_news_aggregator/api/v1/endpoints/briefing.py`
- Memory manager: `src/crypto_news_aggregator/services/memory_manager.py`
- Pattern detector: `src/crypto_news_aggregator/services/pattern_detector.py`
- DB operations: `src/crypto_news_aggregator/db/operations/briefing.py`

---

## Sprint Health

**Status:** 🟢 Ready to Start

**Strengths:**
- All tickets have complete implementation code
- Infrastructure already in place (agent, API, frontend)
- Clear success criteria and testing strategy
- Low risk with good mitigation plans

**Watch Items:**
- Railway multi-service deployment configuration
- First automated briefing quality
- LLM costs (should be ~$2-4/month)

**Confidence:** High - Foundation is solid, just adding quality + automation