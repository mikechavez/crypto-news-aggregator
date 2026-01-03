# Current Sprint: Sprint 2 (Intelligence Layer)

**Goal:** Redesign signals and narratives to produce intelligence, not noise

**Sprint Duration:** 2025-12-31 to TBD

**Velocity Target:** TBD

---

## In Progress

- [x] [FEATURE-008] Signals & Narratives Redesign - **Phase 1: Relevance Filtering COMPLETE**
  - Location: `/Users/mc/Documents/claude-vault/projects/app-backdrop/development/backlog/feature-signals-narratives-redesign.md`
  - Priority: High
  - Complexity: Large
  - **Progress:**
    - Implemented article relevance classifier (Tier 1/2/3)
    - Signals now filter by relevance tier
    - Narratives now filter by relevance tier
    - Backfill script ready for existing articles
  - **Next:** Run backfill, deploy, tune patterns based on prod data

---

## Backlog

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

1. **Run backfill** to classify existing ~24k articles:
   ```bash
   poetry run python scripts/backfill_relevance_tiers.py
   ```
   - Dry run tested successfully (2026-01-02)
   - Distribution: ~10% Tier 1, ~88% Tier 2, ~2% Tier 3
   - Full run interrupted - needs to complete

2. **Commit changes** on `feature/briefing-agent` branch

3. **Test locally** - verify signals/narratives are filtering correctly

4. **Deploy to Railway** and monitor

5. **Review tier distribution** in prod and tune patterns (CHORE-001)

---

## External References

- **Full sprint plan:** `/Users/mc/Documents/claude-vault/projects/app-backdrop/development/SPRINTS.md`
- **All tickets:** `/Users/mc/Documents/claude-vault/projects/app-backdrop/development/`
- **Product vision:** `/Users/mc/Documents/claude-vault/projects/app-backdrop/planning/vision.md`
- **Roadmap:** `/Users/mc/Documents/claude-vault/projects/app-backdrop/planning/roadmap.md`
