# Current Sprint: Sprint 2 (Intelligence Layer)

**Goal:** Redesign signals and narratives to produce intelligence, not noise

**Sprint Duration:** 2025-12-31 to TBD

**Velocity Target:** TBD

---

## In Progress

- [x] [FEATURE-009] Add Narrative Focus Extraction - **COMPLETE**
  - Location: `/Users/mc/Documents/claude-vault/projects/app-backdrop/development/backlog/FEATURE-009-narrative-focus-extraction.md`
  - Priority: High
  - Complexity: Medium
  - Started: 2026-01-06
  - Completed: 2026-01-06
  - Branch: `feature/narrative-focus-extraction`
  - **Summary:**
    - ✅ Updated LLM prompt in `discover_narrative_from_article()` with narrative_focus field
    - ✅ Added two examples showing focus extraction
    - ✅ Updated `validate_narrative_json()` with narrative_focus validation
    - ✅ Updated `compute_narrative_fingerprint()` to include focus
    - ✅ Revised `calculate_fingerprint_similarity()` with new weights:
      - Focus: 0.35 (new key differentiator)
      - Nucleus: 0.30 (reduced from 0.45)
      - Actors: 0.20 (reduced from 0.35)
      - Actions: 0.15 (reduced from 0.20)
    - ✅ Updated Article model with narrative_focus field
    - ✅ Updated narrative_service.py cluster aggregation
    - ✅ Updated backfill scripts (backfill_narratives.py, process_missing_narratives.py)
    - ✅ All 68 tests pass (including 3 new narrative_focus tests)

- [x] [FEATURE-008] Fix Theme vs Title in UI - **COMPLETE**
  - Location: `/Users/mc/Documents/claude-vault/projects/app-backdrop/development/backlog/FEATURE-008-fix-theme-vs-title-ui.md`
  - Priority: High
  - Complexity: Small
  - Started: 2026-01-06
  - Completed: 2026-01-06
  - **Summary:**
    - ✅ Analyzed root cause: `theme` being set to `nucleus_entity` instead of category
    - ✅ Identified UI fallback issue: when `title` = `theme`, narratives look identical
    - ✅ Implemented smart title fallback in Narratives.tsx
    - ✅ New logic: uses title if distinct from theme, else uses summary first sentence
    - ✅ Frontend build passes
    - ✅ Tested locally - backend returning good titles already
    - ✅ Committed to `feature/narrative-title-display` branch
    - ✅ Pushed to remote - PR ready
  - **Branch:** `feature/narrative-title-display`

- [x] [FEATURE-008] Signals & Narratives Redesign - **Phase 1: Relevance Filtering COMPLETE**
  - Location: `/Users/mc/Documents/claude-vault/projects/app-backdrop/development/backlog/feature-signals-narratives-redesign.md`
  - Priority: High
  - Complexity: Large
  - **Progress:**
    - Implemented article relevance classifier (Tier 1/2/3)
    - Signals now filter by relevance tier
    - Narratives now filter by relevance tier
    - Backfill complete: ~22k articles classified
    - Distribution: ~15% Tier 1, ~83% Tier 2, ~2% Tier 3
    - Committed to `feature/briefing-agent` branch
  - **Next:** Test locally, deploy to Railway, tune patterns

---

## Backlog

### Narrative Deduplication Initiative (2026-01-06)

New tickets created to fix narrative duplication problem:

- [x] [FEATURE-009] Add Narrative Focus Extraction - **COMPLETE** (2026-01-06)
  - Core fix - added focus field to distinguish parallel stories about same entity
  - See "In Progress" section for full summary

- [x] [FEATURE-010] Revise Similarity Matching to Prioritize Focus - **COMPLETE**
  - Location: `/Users/mc/Documents/claude-vault/projects/app-backdrop/development/backlog/FEATURE-010-narrative-focus-matching.md`
  - Priority: High
  - Complexity: Large
  - **Summary (2026-01-07):**
    - ✅ Added `_compute_focus_similarity()` function for token-based focus matching
    - ✅ Implemented hard gate logic: blocks similarity if no focus OR nucleus match
    - ✅ Reweighted components: Focus (0.5), Nucleus (0.3), Actors (0.1), Actions (0.1)
    - ✅ Removed semantic boost (weights now sum to 1.0)
    - ✅ Added 12 comprehensive focus similarity tests
    - ✅ Updated 16 fingerprint similarity tests with new weights and hard gate logic
    - ✅ All 83 tests pass ✅
  - **Result:** Prevents narrative over-merging - "Dogecoin price surge" now stays separate from "Dogecoin governance dispute"
  - **Branch:** `feature/narrative-title-display`

- [ ] [FEATURE-011] Add Post-Detection Consolidation Safety Pass
  - Location: `/Users/mc/Documents/claude-vault/projects/app-backdrop/development/backlog/FEATURE-011-narrative-consolidation.md`
  - Priority: Medium
  - Complexity: Medium
  - Lightweight cleanup task to catch edge cases

- [ ] [FEATURE-012] Implement Time-Based Narrative Reactivation
  - Location: `/Users/mc/Documents/claude-vault/projects/app-backdrop/development/backlog/FEATURE-012-narrative-reactivation.md`
  - Priority: Medium
  - Complexity: Medium
  - Revive dormant narratives when story re-emerges

### Other Backlog

- [ ] [CHORE-001] Tune Relevance Classifier Rules
  - Location: `/Users/mc/Documents/claude-vault/projects/app-backdrop/development/backlog/chore-tune-relevance-classifier.md`
  - Priority: Medium
  - Complexity: Small
  - Created this session - tune patterns after seeing prod data

- [ ] [FEATURE-003] Briefing prompt engineering
  - Location: `/Users/mc/Documents/claude-vault/projects/app-backdrop/development/in-progress/feature-briefing-prompt-engineering.md`
  - Priority: High
  - Complexity: Medium
  - Blocked by: FEATURE-008 (partially unblocked now)

- [ ] [FEATURE-007] Celery Beat on Railway
  - Location: `/Users/mc/Documents/claude-vault/projects/app-backdrop/development/backlog/feature-celery-beat-railway.md`
  - Priority: Medium
  - Complexity: Medium

- [ ] [BUG-003] Narrative deep-links
  - Location: `/Users/mc/Documents/claude-vault/projects/app-backdrop/development/backlog/bug-narrative-deep-links.md`
  - Priority: Low
  - Complexity: Small

---

## Completed This Sprint

### 2026-01-06: Narrative Focus Architecture Planning

Designed comprehensive solution for narrative duplication problem:

**Root Cause Identified:**
- Current system uses `nucleus_entity` as primary narrative identity
- Problem: Entities are not narratives - they are ingredients of narratives
- Same entity can have multiple parallel stories (e.g., "Dogecoin price surge" vs "Dogecoin governance dispute")

**Solution Designed:**
- Add `narrative_focus` field capturing "what is happening" (2-5 word phrase)
- Revise similarity matching to prioritize focus over entity
- Examples: "price surge", "regulatory enforcement", "protocol upgrade"

**Deliverables:**
- **ADR 004:** `docs/decisions/004-narrative-focus-identity.md` - Architectural decision record
- **FEATURE-008:** Fix theme vs title in UI (quick win)
- **FEATURE-009:** Add narrative_focus extraction to LLM pipeline
- **FEATURE-010:** Revise similarity matching logic
- **FEATURE-011:** Add consolidation safety pass
- **FEATURE-012:** Implement narrative reactivation logic

**Next:** Start implementation with FEATURE-008 (UI fix)

### 2026-01-02: Relevance Filtering Implementation

Implemented article-level relevance classification to filter noise from signals and narratives:

**Files Created:**
- `src/crypto_news_aggregator/services/relevance_classifier.py` - Rule-based classifier
- `scripts/backfill_relevance_tiers.py` - Backfill script for existing articles
- `scripts/test_classifier.py` - Test script

**Files Modified:**
- `src/crypto_news_aggregator/models/article.py` - Added `relevance_tier`, `relevance_reason`
- `src/crypto_news_aggregator/background/rss_fetcher.py` - Classify on ingestion
- `src/crypto_news_aggregator/services/signal_service.py` - Filter by tier
- `src/crypto_news_aggregator/services/narrative_service.py` - Filter by tier
- `src/crypto_news_aggregator/services/narrative_themes.py` - Filter by tier

**Classification Tiers:**
- Tier 1 (High): SEC, hacks, ETF flows, institutional moves
- Tier 2 (Medium): Standard crypto news
- Tier 3 (Low): Gaming, speculation, price predictions - EXCLUDED

---

## Blocked

- [FEATURE-003] Briefing prompt engineering
  - Was blocked by: FEATURE-008 (upstream data quality)
  - Status: Partially unblocked - relevance filtering in place

---

## Notes

- Sprint 1 closed with 3/4 tickets complete
- Major discovery: signals/narratives need redesign before briefings can improve
- See Sprint 1 retro: `/Users/mc/Documents/claude-vault/projects/app-backdrop/development/sprints/sprint-1-retro.md`

---

## Next Session Checklist

1. ~~**Run backfill** - COMPLETE (2026-01-02)~~
   - Classified ~22k articles
   - Distribution: ~15% Tier 1, ~83% Tier 2, ~2% Tier 3

2. ~~**Commit changes** - COMPLETE (2026-01-02)~~

3. ~~**Test locally** - COMPLETE (2026-01-04)~~
   - Verified relevance tier filtering works correctly
   - Bitcoin test: 29 mentions in last 24h (7 Tier 1, 22 Tier 2, 0 Tier 3)
   - Confirmed Tier 3 articles properly excluded from signals
   - Signal scores need recalculation (background task will handle)

4. ~~**Deploy to Railway** - COMPLETE (2026-01-04)~~
   - PR #124 merged to main (relevance filtering)
   - Hit loguru dependency issue - fixed via PR #125
   - Railway deployment successful - API responding
   - Background tasks running (RSS, narratives, alerts)

5. **Signal scoring: Compute on Read** - COMPLETE (2026-01-05)
   - Discovered: signal scores were 3 months old due to architectural flaw
   - Solution: Implemented compute-on-read pattern (ADR-003)
   - Changes:
     - Worker signal task disabled (compute on demand instead)
     - API endpoints compute signals fresh with 60s cache
     - Alert service updated to use compute_trending_signals
     - Removed unused imports
   - Backfill scripts no longer needed (data computed fresh)

6. **Review tier distribution** in prod and tune patterns (CHORE-001)
   - Monitor signal scores after backfill completes
   - Check production tier distribution
   - Tune patterns if needed

---

## External References

- **Full sprint plan:** `/Users/mc/Documents/claude-vault/projects/app-backdrop/development/SPRINTS.md`
- **All tickets:** `/Users/mc/Documents/claude-vault/projects/app-backdrop/development/`
- **Product vision:** `/Users/mc/Documents/claude-vault/projects/app-backdrop/planning/vision.md`
- **Roadmap:** `/Users/mc/Documents/claude-vault/projects/app-backdrop/planning/roadmap.md`
