# Sprint 7: Model Migration & UI Polish

**Goal:** Migrate to Claude Haiku 4.5 and deliver polished user experience improvements

**Sprint Duration:** 2026-02-06 to 2026-02-20 (2 weeks)

**Velocity Target:** 4 features + 1 bug = 5 tickets

**Status:** 🟡 **IN PROGRESS** - 0/5 complete (0%)

---

## Sprint Objectives

### Primary Goals
1. **Model Migration** - Upgrade to Claude Haiku 4.5 before deprecation
2. **UI Polish** - Fix known UX issues and improve navigation
3. **Feature Enhancement** - Add narrative detail pages for better UX

### Success Criteria
- ✅ Haiku 4.5 migration complete and verified
- ✅ Briefing page labels accurate (morning/evening)
- ✅ Narrative detail pages functional and linked
- ✅ Signals page clean and focused
- ✅ All features tested and deployed

---

## Sprint Backlog

### 🚨 High Priority

#### FEATURE-033: Migrate to Claude Haiku 4.5
**Priority:** HIGH  
**Status:** Ready  
**Complexity:** Low  
**Effort:** 1 hour estimated

**Why this matters:**
- Claude 3.5 Haiku deprecated Jan 5, 2026
- Shutdown date: July 5, 2026
- Haiku 4.5 is 4-5x faster with better performance
- Achieves 90% of Sonnet 4.5 quality

**What we're doing:**
- Update model string: `claude-3-5-haiku-20241022` → `claude-haiku-4-5-20251001`
- Update pricing: Input $0.80→$1.00, Output $4.00→$5.00 per 1M tokens
- Test entity extraction quality
- Verify cost tracking accuracy

**Cost impact:** +$0.15/month (still well under $10 target)

**Files:**
- `src/crypto_news_aggregator/llm/optimized_anthropic.py` (1 line)
- `src/crypto_news_aggregator/services/cost_tracker.py` (pricing table)

**Ticket:** `/mnt/user-data/outputs/FEATURE-033-haiku-4-5-migration.md`

---

### 📋 Medium Priority

#### FEATURE-034: Build Narrative Detail Page
**Priority:** MEDIUM  
**Status:** Ready  
**Complexity:** Medium  
**Effort:** 4 hours estimated

**Why this matters:**
- Blocks FEATURE-035 (recommended reading links)
- Users can't deep-dive into narratives
- No shareable narrative URLs
- Future features need detail pages

**What we're building:**
- New route: `/narratives/:id`
- Dedicated page with narrative focus
- Full article list (better UX than accordion)
- Metadata section (first seen, last updated, etc.)
- Related signals (if available)

**Components:**
- `NarrativeDetail.tsx` (main page)
- `LifecycleBadge.tsx` (extracted shared component)
- `ArticleCard.tsx` (extracted shared component)

**Backend dependency:** Verify or create `GET /api/narratives/:id` endpoint

**Ticket:** `/mnt/user-data/outputs/FEATURE-034-narrative-detail-page.md`

---

#### FEATURE-035: Update Briefing Recommended Reading Links
**Priority:** MEDIUM  
**Status:** Blocked (depends on FEATURE-034)  
**Complexity:** Low  
**Effort:** 1 hour estimated

**Why this matters:**
- Recommended reading links currently go to generic `/narratives` page
- Users can't click to explore recommendations
- Feature feels broken/incomplete

**What we're doing:**
- Backend: Add `narrative_id` to recommendation objects
- Frontend: Link to `/narratives/{id}` instead of `/narratives`
- Graceful fallback for old briefings without IDs

**Dependencies:** FEATURE-034 must be complete first

**Files:**
- `src/crypto_news_aggregator/services/briefing_agent.py` (backend)
- `context-owl-ui/src/pages/Briefing.tsx` (1 line change)

**Ticket:** `/mnt/user-data/outputs/FEATURE-035-briefing-recommended-links.md`

---

#### BUG-010: Briefing Morning/Evening Label Accuracy
**Priority:** MEDIUM  
**Status:** Ready  
**Severity:** Low  
**Effort:** 30 min estimated

**Why this matters:**
- Briefing page should accurately show "Morning" or "Evening"
- Label should be based on actual generation time
- Current implementation unclear

**What we're investigating:**
- Does backend set `type` field correctly?
- Is it based on scheduled time (8 AM/8 PM) or actual time?
- Does it persist correctly in MongoDB?

**Proposed fix:**
Backend should set `type` based on scheduled hour:
- `scheduled_hour == 8` → `type = "morning"`
- `scheduled_hour == 20` → `type = "evening"`

**Files:**
- `src/crypto_news_aggregator/services/briefing_agent.py` (investigation/fix)

**Ticket:** `/mnt/user-data/outputs/BUG-010-briefing-morning-evening-label.md`

---

### ✨ Low Priority / Quick Wins

#### FEATURE-036: Remove "Part of:" Section from Signals
**Priority:** LOW  
**Status:** Ready  
**Complexity:** Trivial  
**Effort:** 10 minutes estimated

**Why this matters:**
- Current "Part of:" links don't work (go to generic page)
- Creates user confusion
- Better to remove than show broken functionality

**What we're doing:**
- Remove narrative links from signal cards
- Keep "Emerging" badge (still useful)
- Clean up spacing/layout

**What stays:** Recent articles, velocity badges, entity info  
**What goes:** Narrative theme badge buttons

**Files:**
- `context-owl-ui/src/pages/Signals.tsx` (~20 lines removed, ~8 added)

**Future:** Re-add with working links after FEATURE-034 completes

**Ticket:** `/mnt/user-data/outputs/FEATURE-036-remove-signals-part-of.md`

---

## Sprint Progress

### Velocity Tracker
- **Total tickets:** 5 (4 features + 1 bug)
- **Completed:** 0/5 (0%)
- **In Progress:** 0
- **Blocked:** 1 (FEATURE-035 blocked by FEATURE-034)
- **Estimated hours:** 6.5 hours total

### Current Focus
1. 🔴 **FEATURE-033** - Haiku migration (do first, highest priority)
2. 🟡 **FEATURE-034** - Narrative detail pages (unblocks FEATURE-035)
3. 🟢 **FEATURE-036** - Remove "Part of:" section (quick win)

---

## Dependency Graph

```
FEATURE-033 (Haiku Migration) ────────────────────┐
                                                   │
BUG-010 (Briefing Labels) ───────────────────────┤
                                                   ├─→ Deploy Together
FEATURE-036 (Remove "Part of") ──────────────────┤
                                                   │
                                                   └─→ Quick Wins Phase

FEATURE-034 (Narrative Detail) ──┐
                                  ├─→ FEATURE-035 (Recommended Links)
                                  │
                                  └─→ Future: Re-add "Part of" to Signals
```

---

## Technical Context

### Model Migration Details
**Current:** Claude 3.5 Haiku (deprecated)  
**New:** Claude Haiku 4.5

| Model | Input Cost | Output Cost |
|-------|------------|-------------|
| 3.5 Haiku | $0.80/1M | $4.00/1M |
| 4.5 Haiku | $1.00/1M | $5.00/1M |

**Performance:** 4.5 is 4-5x faster, better quality

---

### UI Architecture Changes

**New Routes:**
- `/narratives/:id` - Narrative detail page (new)

**Shared Components to Extract:**
- `LifecycleBadge` - Used by Narratives list + detail
- `ArticleCard` - Reusable article display

**Files to Modify:**
- Briefing.tsx - Link recommendations to detail pages
- Signals.tsx - Remove broken narrative links
- Narratives.tsx - Refactor to use shared components

---

## Risk Assessment

### Medium Risk  
🟡 **FEATURE-034** - Backend endpoint might not exist  
**Mitigation:** Verify endpoint first, create if needed (add 30 min)

### Low Risk
🟢 **FEATURE-033** - Model migration is straightforward  
🟢 **Others** - All are simple UI changes with clear scope

---

## Testing Strategy

### Unit Tests
- Cost tracker with new Haiku 4.5 pricing
- Entity extraction with new model
- Narrative detail component rendering

### Integration Tests
- Recommended reading navigation flow
- Narrative detail page data loading

### Manual QA
- Test all new routes and links
- Verify dark mode on all new pages
- Check responsive design (mobile, tablet, desktop)

---

## Deployment Plan

### Phase 1: Model Migration & Quick Wins (Day 1-2)
1. Deploy FEATURE-033 (Haiku 4.5)
2. Monitor first few API calls
3. Verify cost tracking accuracy
4. Deploy FEATURE-036 (remove "Part of") - quick win
5. Deploy BUG-010 (label fix) if investigation confirms it's needed

### Phase 2: UI Enhancements (Day 3-7)
1. Develop and test FEATURE-034 (narrative detail)
2. Deploy FEATURE-034
3. Develop and deploy FEATURE-035 (recommended links)

### Phase 3: Verification (Day 8-14)
1. Monitor production for issues
2. Gather user feedback
3. Fix any bugs discovered
4. Document lessons learned

---

## Success Metrics

### Cost & Performance
- Monthly LLM cost remains under $10 (target: ~$0.86)
- Haiku 4.5 entity extraction quality ≥ 3.5 Haiku
- No API errors or rate limiting

### User Experience
- Recommended reading links work (0% 404 errors)
- Narrative detail pages load fast (<500ms)
- Zero broken links or navigation errors
- Clean, focused signal cards (no confusing elements)

### Code Quality
- All tests passing (30+ existing + new tests)
- No console errors or warnings
- TypeScript compilation clean
- Production build succeeds

---

## Next Actions

### Immediate (This Session)
1. ⏳ **Start FEATURE-033** - Migrate to Haiku 4.5
2. ⏳ **Start FEATURE-036** - Remove "Part of:" section (quick win)
3. ⏳ **Investigate BUG-010** - Check if briefing type field needs fixing

### This Week
1. Complete FEATURE-033 and FEATURE-036
2. Start FEATURE-034 (narrative detail pages)
3. Deploy first batch to production
4. Monitor cost tracking with new model

### Next Week
1. Complete FEATURE-034 and FEATURE-035
2. Verify all features in production
3. Sprint review and retrospective

---

## Open Questions

- [ ] **FEATURE-034:** Does backend endpoint `/api/narratives/:id` exist?
- [ ] **BUG-010:** Is briefing `type` field being set correctly?
- [ ] **Cost:** Will Haiku 4.5 pricing increase impact monthly budget significantly?

---

## Lessons from Sprint 6

**What worked well:**
- ✅ Clear ticket templates with implementation details
- ✅ Comprehensive testing before deployment
- ✅ Breaking critical bugs into separate tickets
- ✅ Actual effort was 55% less than estimated (good padding)

**What to improve:**
- 🔄 Add deployment verification checklist
- 🔄 Monitor production more proactively
- 🔄 Create integration tests for Celery tasks
- 🔄 Document Railway environment variables

**Apply to Sprint 7:**
- Use detailed tickets (working well)
- Add production monitoring to each deployment
- Create verification script for briefing generation
- Test in production immediately after deploy

---

**Sprint Health:** 🟡 **READY TO START**

**Last Updated:** 2026-02-06  
**Next Review:** 2026-02-13 (mid-sprint check-in)

---

## Files Delivered This Sprint

### To Be Created
- `context-owl-ui/src/pages/NarrativeDetail.tsx`
- `context-owl-ui/src/components/LifecycleBadge.tsx`
- `context-owl-ui/src/components/ArticleCard.tsx`

### To Be Modified
- `src/crypto_news_aggregator/llm/optimized_anthropic.py`
- `src/crypto_news_aggregator/services/cost_tracker.py`
- `src/crypto_news_aggregator/services/briefing_agent.py`
- `context-owl-ui/src/pages/Briefing.tsx`
- `context-owl-ui/src/pages/Signals.tsx`
- `context-owl-ui/src/pages/Narratives.tsx`
- `context-owl-ui/src/App.tsx`
- `context-owl-ui/src/api/narratives.ts`

**Total:** 3 new files, 8 modified files