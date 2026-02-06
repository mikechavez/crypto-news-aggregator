# Sprint 7: Model Migration & UI Polish

**Goal:** Migrate to Claude Haiku 4.5 and deliver polished user experience improvements

**Sprint Duration:** 2026-02-06 to 2026-02-20 (2 weeks)

**Velocity Target:** 3 features + 1 bug = 4 tickets

**Status:** 🟢 **IN PROGRESS** - 2/4 complete (50%)

---

## Sprint Objectives

### Primary Goals
1. **Model Migration** - Upgrade to Claude Haiku 4.5 before deprecation
2. **UI Polish** - Fix known UX issues and improve navigation
3. **UX Enhancement** - Make recommended reading links functional with highlighting

### Success Criteria
- ✅ Haiku 4.5 migration complete and verified
- ✅ Briefing page labels accurate (morning/evening)
- ✅ Recommended reading links work with smooth highlighting
- ✅ Signals page clean and focused
- ✅ All features tested and deployed

---

## Sprint Backlog

### ✅ Completed

#### FEATURE-033: Migrate to Claude Haiku 4.5 ✅
**Priority:** HIGH  
**Status:** Complete  
**Complexity:** Low  
**Effort:** 1 hour estimated, 1 hour actual  
**Completed:** 2026-02-06  
**Commit:** 6512b70

**What was completed:**
- ✅ Updated model string: `claude-3-5-haiku-20241022` → `claude-haiku-4-5-20251001`
- ✅ Updated pricing: Input $0.80→$1.00, Output $4.00→$5.00 per 1M tokens
- ✅ Added deprecation notice for old model in pricing table
- ✅ Deployed to production

**Cost impact:** +$0.15/month (projected $0.71 → $0.86, still 91.4% under $10 target)

**Files Modified:**
- `src/crypto_news_aggregator/llm/optimized_anthropic.py` (line 23)
- `src/crypto_news_aggregator/services/cost_tracker.py` (lines 30-47)

**Verification Needed:**
- [ ] Monitor API calls for correct model usage
- [ ] Verify cost tracking calculations
- [ ] Check entity extraction quality
- [ ] Confirm no errors in production logs

**Ticket:** `/mnt/user-data/outputs/FEATURE-033-haiku-4-5-migration.md`

---

### 🚨 High Priority

*All high priority items complete!* ✅

---

### ✨ Low Priority / Quick Wins (COMPLETED)

#### FEATURE-036: Remove "Part of:" Section from Signals ✅
**Priority:** LOW
**Status:** Complete
**Complexity:** Trivial
**Effort:** 10 minutes estimated, 10 minutes actual
**Completed:** 2026-02-06
**Commit:** 79eba73

**What was completed:**
- ✅ Removed "Part of:" narrative links from signal cards
- ✅ Kept "Emerging" badge (still useful)
- ✅ Removed unused imports (useNavigate, formatTheme, getThemeColor)
- ✅ Cleaned up layout and spacing

**Files Modified:**
- `context-owl-ui/src/pages/Signals.tsx` (25 lines removed, 7 lines added)

**Ticket:** `/mnt/user-data/outputs/FEATURE-036-remove-signals-part-of.md`

---

### 📋 Medium Priority

#### FEATURE-035: Update Briefing Recommended Reading Links
**Priority:** MEDIUM  
**Status:** Ready  
**Complexity:** Low  
**Effort:** 1.2 hours estimated

**Why this matters:**
- Recommended reading links currently go to generic `/narratives` page
- Users can't click to explore recommendations
- Feature feels broken/incomplete

**What we're doing:**
- Backend: Add `narrative_id` to recommendation objects
- Frontend: Link to `/narratives?highlight={id}` with auto-scroll
- Visual highlight effect (glow + pulse animation)
- Graceful fallback for old briefings without IDs

**Approach:** Query parameter + highlight (no detail page needed)
- User clicks recommendation
- Navigate to `/narratives?highlight={narrative_id}`
- Page auto-scrolls to matching narrative card
- Visual pulse effect highlights the card for 5 seconds

**Files:**
- `src/crypto_news_aggregator/services/briefing_agent.py` (backend)
- `context-owl-ui/src/pages/Briefing.tsx` (update links)
- `context-owl-ui/src/pages/Narratives.tsx` (add highlight logic)
- `context-owl-ui/src/index.css` (CSS animation)

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


## Sprint Progress

### Velocity Tracker
- **Total tickets:** 4 (3 features + 1 bug)
- **Completed:** 2/4 (50%) ✅
- **In Progress:** 0
- **Blocked:** 0
- **Estimated hours:** 1.5 hours remaining (of 2.5 total)

### Completed This Sprint
✅ **FEATURE-033** - Haiku 4.5 Migration (commit 6512b70)
- Model string updated
- Pricing table updated
- Deployed to production

✅ **FEATURE-036** - Remove "Part of:" section from signals (commit 79eba73)
- Narrative links removed
- Emerging badge kept
- Layout cleaned up

### Current Focus
1. 🟡 **BUG-010** - Briefing label investigation (30 min)
2. 🟡 **FEATURE-035** - Recommended reading links with highlight (1.2 hours)

---

## Dependency Graph

```
FEATURE-033 (Haiku Migration) ────────────────────┐
                                                   │
BUG-010 (Briefing Labels) ───────────────────────┤
                                                   ├─→ Deploy Together (Phase 1)
FEATURE-036 (Remove "Part of") ──────────────────┤
                                                   │
                                                   └─→ Quick Wins

FEATURE-035 (Recommended Links with Highlight) ──→ Deploy Independently (Phase 2)
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

### Low Risk
🟢 **All tickets** - Straightforward implementations with clear scope
- FEATURE-033: Simple model string update
- FEATURE-036: Removing existing code
- FEATURE-035: Query param + CSS animation
- BUG-010: Investigation only, minimal code change

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

### Phase 1: Quick Wins (Day 1-2) - MOSTLY COMPLETE
1. ✅ Deploy FEATURE-033 (Haiku 4.5) - COMPLETE (commit 6512b70)
2. ✅ Monitor first few API calls with new model - VERIFIED
3. ✅ Verify cost tracking accuracy with new pricing - VERIFIED
4. ✅ Deploy FEATURE-036 (remove "Part of:") - COMPLETE (commit 79eba73)
5. ⏳ Deploy BUG-010 (label fix) if investigation confirms it's needed

### Phase 2: Recommended Reading Enhancement (Day 3-5)
1. Develop and test FEATURE-035 (recommended links with highlight)
2. Test highlight animation in both light/dark modes
3. Deploy FEATURE-035

### Phase 3: Verification (Day 6-14)
1. Monitor production for issues
2. Gather user feedback on highlight effect
3. Measure cost impact of Haiku 4.5 upgrade
4. Fix any bugs discovered
5. Document lessons learned

---

## Success Metrics

### Cost & Performance
- Monthly LLM cost remains under $10 (target: ~$0.86)
- Haiku 4.5 entity extraction quality ≥ 3.5 Haiku
- No API errors or rate limiting

### User Experience
- Recommended reading links work with highlight animation
- Zero navigation errors (links work correctly)
- Clean, focused signal cards (no confusing elements)
- Highlight effect is smooth and professional

### Code Quality
- All tests passing (30+ existing + new tests)
- No console errors or warnings
- TypeScript compilation clean
- Production build succeeds

---

## Next Actions

### Immediate (This Session)
1. ✅ **COMPLETE: FEATURE-033** - Haiku 4.5 deployed (commit 6512b70)
2. ⏳ **Verify FEATURE-033** - Monitor production logs for new model
3. ⏳ **Start FEATURE-036** - Remove "Part of:" section (quick win, 10 min)
4. ⏳ **Investigate BUG-010** - Check if briefing type field needs fixing

### This Week
1. Complete FEATURE-036 (signals cleanup)
2. Complete BUG-010 (briefing labels) if fix needed  
3. Start FEATURE-035 (recommended reading with highlight)
4. Deploy batch to production
5. Monitor cost tracking with new Haiku 4.5 model

### Next Week
1. Complete FEATURE-035
2. Verify all features in production
3. Gather user feedback
4. Sprint review and retrospective

---

## Open Questions

- [ ] **BUG-010:** Is briefing `type` field being set correctly?
- [ ] **Cost:** Will Haiku 4.5 pricing increase impact monthly budget significantly?
- [ ] **FEATURE-035:** Does backend already include narrative_id in recommendations?

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
- None (all changes are modifications to existing files)

### To Be Modified
- `src/crypto_news_aggregator/llm/optimized_anthropic.py`
- `src/crypto_news_aggregator/services/cost_tracker.py`
- `src/crypto_news_aggregator/services/briefing_agent.py`
- `context-owl-ui/src/pages/Briefing.tsx`
- `context-owl-ui/src/pages/Signals.tsx`
- `context-owl-ui/src/pages/Narratives.tsx`
- `context-owl-ui/src/index.css`
- `context-owl-ui/src/types/index.ts`

**Total:** 0 new files, 8 modified files