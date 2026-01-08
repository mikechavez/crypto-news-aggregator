# Current Sprint: Sprint 2 (Intelligence Layer)

**Goal:** Redesign signals and narratives to produce intelligence, not noise

**Sprint Duration:** 2025-12-31 to TBD

**Velocity Target:** TBD

---

## Current Status

### ✅ FEATURE-013 Backfill Complete
- **[FEATURE-013] Execute Backfill** - ✅ **COMPLETE**
  - Status: Successfully executed 2026-01-07 23:11-23:24
  - Result: 435/436 narratives backfilled with narrative_focus field
  - Failures: 1 (timeout on ObjectId('68f1ba31fdcae8c027f50d19'))
  - Cost: $0.09 (much cheaper than estimated $1-2)
  - Duration: ~13 minutes
  - Ready for FEATURE-011 implementation

---

## Completed This Session

### ✅ FEATURE-011-IMPLEMENTATION Complete

**[FEATURE-011-IMPLEMENTATION] Consolidation Safety Pass - Implementation**
- Priority: P1 (blocks narrative quality improvements)
- Complexity: Medium (2-3 hours)
- Status: ✅ **COMPLETE** (2026-01-08)
- Ticket: `docs/tickets/feature-011-add-post-detection-consolidation`
- Implementation summary:
  - Added `consolidate_duplicate_narratives()` to NarrativeService
  - Added `_merge_narratives()` with comprehensive data merging logic
  - Created Celery task: `narrative_consolidation.py`
  - Scheduled to run every hour via Celery Beat
  - All imports verified and code compiles successfully
- Files created:
  - ✅ `src/crypto_news_aggregator/tasks/narrative_consolidation.py` (45 lines)
- Files modified:
  - ✅ `src/crypto_news_aggregator/services/narrative_service.py` (added 200 lines)
  - ✅ `src/crypto_news_aggregator/tasks/beat_schedule.py` (added schedule entry)
  - ✅ `src/crypto_news_aggregator/tasks/__init__.py` (added import)
- Next: FEATURE-011-TESTS (comprehensive test suite)

## Ready for Implementation

### Priority 1 - Critical Path (After FEATURE-011)

**[FEATURE-011-TESTS] Consolidation Safety Pass - Testing**
- Priority: P1 (completes FEATURE-011)
- Complexity: Medium (2-3 hours)
- Status: ✅ Ready for Claude Code (after implementation)
- Ticket: `FEATURE-011-TESTS.md` (in outputs folder)
- Blocked by: FEATURE-011-IMPLEMENTATION must be complete
- Files to create:
  - CREATE: `tests/services/test_narrative_service_consolidation.py` (10+ unit tests)
  - CREATE: `tests/tasks/test_narrative_consolidation.py` (3+ integration tests)
- Deliverable: Comprehensive test suite, ready for production deployment

### Priority 2 - Optimizations

**[CHORE-001] Tune Relevance Classifier Rules**
- Priority: P2
- Complexity: Small (1-2 hours)
- Status: ✅ Ready for immediate implementation
- Location: `backlog/chore-tune-relevance-classifier.md`
- Files: `src/crypto_news_aggregator/services/relevance_classifier.py`
- No blockers - can implement anytime

**[FEATURE-012] Time-Based Narrative Reactivation**
- Priority: P2
- Complexity: Medium (2-3 hours)
- Status: Backlog (implement after FEATURE-011-TESTS)
- Location: `backlog/FEATURE-012-narrative-reactivation.md`
- Dependencies: FEATURE-011-IMPLEMENTATION + FEATURE-011-TESTS complete

---

## Completed

### 2026-01-07 (Today)

#### Evening (Late) - Backfill Execution
- **[FEATURE-013] Execute Backfill Script** - ✅ COMPLETE
  - Executed 2026-01-07 23:11-23:24 (~13 minutes)
  - Result: 435/436 narratives successfully backfilled
  - Single failure: Timeout on one narrative (ObjectId('68f1ba31fdcae8c027f50d19'))
  - Tokens used: 54093 input, 11104 output
  - Cost: $0.09 (excellent - well under estimate)
  - **FEATURE-011 now unblocked and ready for implementation**

#### Evening - Ticket Preparation & Enhancement
- **[FEATURE-011] Consolidation Tickets Created** - ✅ READY FOR CLAUDE CODE
  - Split into two comprehensive tickets for implementation and testing
  - **FEATURE-011-IMPLEMENTATION**: Core consolidation logic (2-3 hours)
    - Complete method implementations provided
    - Database query patterns with examples
    - Step-by-step implementation guide
    - Basic smoke test checklist
  - **FEATURE-011-TESTS**: Comprehensive test suite (2-3 hours)
    - 10+ unit tests fully implemented
    - 3+ integration tests fully implemented
    - Edge case coverage
    - Test fixtures and helpers
  - Both tickets ready in outputs folder
  - Follows FEATURE-013 comprehensive template model
  - Time: ~1 hour of enhancement work

#### Afternoon - Database Investigation & Fix
- **[FEATURE-014] Investigate Missing Narratives** - ✅ COMPLETE
  - Root cause: Scripts connecting to `backdrop` database instead of `crypto_news`
  - Created diagnostic tool: `scripts/diagnose_database.py`
  - Fixed FEATURE-013 script database name and query filter
  - Validated: 436 narratives ready for backfill
  - Time: ~1 hour
  - Files created: `scripts/diagnose_database.py`
  - Files modified: `scripts/backfill_narrative_focus.py`

- **[FEATURE-013] Backfill Script Creation** - ✅ READY TO EXECUTE
  - Created comprehensive backfill script with:
    - Batch processing (50 narratives per batch)
    - Cost tracking and progress logging
    - Dry-run mode for validation
    - Error handling and failure tracking
  - Database issue fixed (was `backdrop`, now `crypto_news`)
  - Query filter updated (backfills ALL narratives, not just Dec 1+)
  - Dry-run validated: Found 436 narratives to process
  - Ready for execution: Waiting for Mike to run manually
  - Time: ~2 hours total (creation + fixes)

#### Morning - Focus-First Matching
- **[FEATURE-010] Revise Similarity Matching** - ✅ DEPLOYED
  - Rewrote `calculate_fingerprint_similarity()` with new weights:
    - Focus: 0.5 (primary discriminator, was 0.35)
    - Nucleus: 0.3 (secondary, was 0.30)
    - Actors: 0.1 (was 0.20)
    - Actions: 0.1 (was 0.15)
  - Added hard gate logic: Requires focus OR nucleus match
  - Added `_compute_focus_similarity()` for token-based matching
  - All 83 tests passing (12 new focus tests, 71 existing updated)
  - Result: Prevents unrelated narrative merges
  - Time: ~3 hours
  - Deployed: Merged to main, live in Railway production

### 2026-01-06

- **[FEATURE-009] Add Narrative Focus Extraction** - ✅ DEPLOYED
  - Added narrative_focus field to LLM extraction pipeline
  - Updated fingerprint calculation to include focus
  - Added validation and tests
  - All 68 tests passing
  - Time: ~4 hours
  - Branch: `feature/narrative-focus-extraction`

- **[FEATURE-008] Fix Theme vs Title UI** - ✅ DEPLOYED
  - Implemented smart title fallback in Narratives.tsx
  - Fixed UI issue where narratives showed identical titles
  - Time: ~1 hour
  - Branch: `feature/narrative-title-display`

### 2026-01-05

- **Signal Scoring: Compute on Read** - ✅ DEPLOYED
  - Implemented ADR-003: Compute signals on demand instead of background task
  - Disabled worker signal task
  - Added 60s cache to API endpoints
  - Time: ~2 hours

### 2026-01-04

- **Deployment & Testing** - ✅ COMPLETE
  - PR #124 merged (relevance filtering)
  - Fixed loguru dependency issue (PR #125)
  - Railway deployment successful
  - Verified background tasks running

### 2026-01-02

- **[FEATURE-008 Phase 1] Relevance Filtering** - ✅ DEPLOYED
  - Implemented article relevance classifier (Tier 1/2/3)
  - Backfilled ~22k articles
  - Distribution: ~15% Tier 1, ~83% Tier 2, ~2% Tier 3
  - Files modified: Multiple services, article model, RSS fetcher
  - Time: ~6 hours
  - Branch: `feature/briefing-agent`

---

## Architecture Decisions

### Active ADRs
- **ADR-004**: Narrative Focus Identity
  - Status: ~95% implemented
  - FEATURE-009: Focus extraction ✅
  - FEATURE-010: Focus-first matching ✅
  - FEATURE-013: Backfill ready ✅ (waiting for execution)
  - FEATURE-011-IMPLEMENTATION: Ready ✅
  - FEATURE-011-TESTS: Ready ✅

- **ADR-003**: Signal Compute-on-Read
  - Status: ✅ Implemented and deployed
  - Background signal task disabled
  - API endpoints compute fresh with cache

---

## Metrics & Progress

### Sprint 2 Velocity
- **Completed tickets:** 6 (FEATURE-008 Phase 1, FEATURE-009, FEATURE-010, FEATURE-013 script, FEATURE-014, Signal compute-on-read)
- **In progress:** 1 (FEATURE-013 execution - manual)
- **Ready:** 4 (FEATURE-011-IMPLEMENTATION, FEATURE-011-TESTS, CHORE-001, FEATURE-012)
- **Estimated remaining effort:** ~8-10 hours (implementation + testing + tuning)

### Narrative Quality Improvements
**Before (Sprint 1):**
- Multiple duplicate narratives per entity (5-8 duplicates common)
- Unclear identity (nucleus_entity was primary signal)
- No distinction between parallel stories

**After ADR-004 Implementation:**
- Focus-first matching prevents duplicates ✅
- Clear narrative identity via focus field ✅
- Parallel stories stay distinct (e.g., "Dogecoin price surge" vs "Dogecoin governance") ✅
- Awaiting: Backfill + consolidation pass for full effect

---

## Blocked Items

None currently - FEATURE-013 is ready to execute (manual step)

---

## Next Actions

### Immediate (Next Session)
1. ✅ **FEATURE-013 backfill** - COMPLETE (435/436 narratives done)
2. **Claude Code (Session 1):** Implement FEATURE-011-IMPLEMENTATION
3. **Claude Code (Session 2):** Implement FEATURE-011-TESTS

### This Week
1. Complete FEATURE-011 (implementation + testing)
2. Optional: Implement CHORE-001 (tune relevance classifier)
3. Test narrative quality improvements in production
4. Plan FEATURE-012 implementation

### Next Week
1. Implement FEATURE-012 (narrative reactivation)
2. Resume FEATURE-003 (briefing prompt engineering)
3. Monitor narrative deduplication metrics

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

---

## Sprint Health

**Status:** 🟢 Healthy

**Completed this sprint:**
- ✅ Relevance filtering system
- ✅ Narrative focus extraction (ADR-004)
- ✅ Focus-first matching logic
- ✅ Database diagnostic tooling
- ✅ Backfill script preparation

**Remaining work:**
- ⏳ Execute backfill (manual step)
- 📋 FEATURE-011-IMPLEMENTATION (consolidation logic)
- 📋 FEATURE-011-TESTS (comprehensive test suite)
- 📋 Classifier tuning (optional)

**Risks:**
- None identified - good progress on critical path

**Notes:**
- Good momentum on narrative quality improvements
- ADR-004 implementation nearly complete (just needs backfill execution + consolidation)
- Ready to move to optimization phase after FEATURE-011