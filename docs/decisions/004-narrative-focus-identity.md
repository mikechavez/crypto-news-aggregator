# 004. Add Narrative Focus Field for Story Identity

**Date:** 2026-01-06

**Status:** Accepted

**Deciders:** Development team

**Related Tickets:** FEATURE-008, FEATURE-009, FEATURE-010, FEATURE-011, FEATURE-012

---

## Context

The narrative detection system is producing duplicate narratives for the same entity (e.g., multiple "Dogecoin" narratives appearing simultaneously). The root cause is that `nucleus_entity` is being used as the primary identity signal, but **entities are not narratives - they are ingredients of narratives**.

Current problems:
1. **Over-splitting**: Same entity produces multiple simultaneous narratives (e.g., "Dogecoin" → 5 separate narratives)
2. **Over-merging**: Different stories about same entity collapse together (e.g., "SEC enforcement action" + "SEC policy proposal" → single narrative)
3. **Time fragmentation**: Narratives >48h old split unnecessarily because they lack actor/action overlap, even when covering the same story

The current fingerprint matching logic relies on:
- `nucleus_entity` (strongest signal)
- `top_actors` (medium signal)
- `key_actions` (medium signal)
- Time decay thresholds

This design assumes: **same entity ≈ same narrative**

But in reality:
- "Dogecoin" can support 5 parallel stories on the same day:
  - Price surge driven by retail
  - Governance proposal dispute
  - Twitter meme campaign
  - Protocol upgrade announcement
  - Regulatory scrutiny

The system has no way to distinguish these as separate stories.

**Constraints:**
- Must work with existing LLM extraction pipeline
- Cannot break existing narrative lifecycle tracking
- Must not introduce expensive embedding computation at this stage
- Solution must be deterministic and debuggable

**Success Criteria:**
- Eliminate duplicate nucleus_entity narratives when they tell the same story
- Allow parallel narratives for same entity when they tell different stories
- Make narrative identity stable over time (reactivation vs new narrative)

---

## Decision

**Add `narrative_focus` as a core field to narrative fingerprints and use it as the primary story discriminator.**

The `narrative_focus` field captures "what is happening" in the story as a short phrase (2-5 words).

**New fingerprint structure:**
```python
{
  "nucleus_entity": str,          # Primary entity (e.g., "Dogecoin")
  "narrative_focus": str,          # What's happening (e.g., "price surge")
  "top_actors": List[str],         # Supporting entities
  "key_actions": List[str],        # Key verbs/actions
  "timestamp": datetime
}
```

**Revised matching philosophy:**

Hard gate: `nucleus_entity` must match OR `narrative_focus` must match strongly

Primary signal: `narrative_focus` match (weighted 0.5)

Secondary: `nucleus_entity` match (weighted 0.3)

Tertiary: actor/action overlap (weighted 0.2)

**This creates stable narrative identity:**
- Same nucleus + same focus → same narrative (merge)
- Same nucleus + different focus → parallel narratives (keep separate)
- Focus reappears after dormancy → reactivate (not new narrative)

**Implementation approach:**
1. Extract `narrative_focus` during LLM entity extraction (no new API call)
2. Update fingerprint generation to include focus
3. Revise similarity matching to prioritize focus over entity
4. Add lightweight consolidation pass as safety net

---

## Alternatives Considered

### Option 1: Just Tune Thresholds

**Description:** Adjust similarity thresholds and boost same-nucleus matching more aggressively

**Pros:**
- Minimal code changes
- Quick to implement
- No schema changes

**Cons:**
- Treats symptoms, not root cause
- Will create weird merges (different stories collapse together)
- Fragile to edge cases
- Makes future behavior unpredictable

**Why not chosen:** This masks the real issue that the system doesn't know what a narrative *is*. It will create new problems (over-merging) while trying to solve duplication.

### Option 2: Post-Detection Deduplication Only

**Description:** Let duplicates form, then merge them in a cleanup pass

**Pros:**
- Non-invasive to existing detection logic
- Can be tuned independently
- Safety net for edge cases

**Cons:**
- Consolidation has to do heavy structural work (merge metrics, article_ids, timelines)
- Narrative IDs change after consolidation (breaks external references)
- Doesn't fix identity problem at source
- Hard to reason about which narratives will merge

**Why not chosen:** Consolidation should be boring and obvious, not essential. If we rely on it to fix identity, we'll introduce spooky merges later (especially when adding embeddings).

### Option 3: Embeddings-Based Similarity

**Description:** Use semantic embeddings (e.g., OpenAI text-embedding-3) to compute narrative similarity

**Pros:**
- More sophisticated similarity matching
- Handles synonyms and paraphrasing
- Could improve matching quality

**Cons:**
- Expensive (API cost + compute)
- Non-deterministic (hard to debug)
- Doesn't solve the identity modeling problem
- Adds latency to detection pipeline
- Still needs focus concept to avoid over-merging

**Why not chosen:** Premature optimization. The current system doesn't need semantic similarity - it needs a clear notion of story identity. Embeddings can be added later as a refinement.

---

## Consequences

### Positive

- **Eliminates duplication at source**: Same entity + same focus naturally deduplicate
- **Enables parallel narratives**: Different stories about same entity coexist cleanly
- **Makes identity stable**: Focus-based matching survives time gaps and actor drift
- **Improves briefing quality**: Narratives are actual stories, not just entity clusters
- **Debuggable**: Focus is human-readable (no black-box embeddings)
- **Zero new API calls**: Focus extracted during existing entity extraction step

### Negative

- **Schema migration required**: Need to backfill `narrative_focus` for existing narratives (can be done lazily)
- **LLM prompt changes**: Entity extraction prompt needs focus extraction instruction
- **Matching logic complexity**: More sophisticated similarity calculation
- **Quality depends on LLM**: If focus extraction is poor, matching breaks

### Neutral

- **New field to monitor**: Need to validate focus extraction quality in production
- **Consolidation logic still needed**: Downgraded to safety net, but still useful
- **May reveal new edge cases**: Different categorization of what counts as "same story"

---

## Implementation Notes

**Key files affected:**
- `src/crypto_news_aggregator/services/entity_extraction.py` (add focus to extraction)
- `src/crypto_news_aggregator/services/narrative_service.py` (update fingerprint, matching)
- `src/crypto_news_aggregator/db/models/narrative.py` (add focus field to schema)
- `src/crypto_news_aggregator/llm/prompts/entity_extraction.py` (update prompt)

**Migration required:** Yes
- Add `narrative_focus` field to narratives collection
- Backfill can be lazy (compute on next detection run)

**Breaking changes:** No
- Existing API contracts unchanged
- UI shows title (not focus), so no user-facing changes

**Documentation updated:**
- Update narrative detection flow diagram
- Document focus extraction guidelines

---

## Validation

How will we know if this decision was successful?

**Quantitative:**
- Duplicate nucleus_entity narratives reduced by >80% (measure: narratives per entity)
- Narrative merge rate decreases (fewer consolidations needed)
- Narrative reactivation rate increases (same focus comes back vs new narrative)

**Qualitative:**
- Manual review: 20 random narratives should tell distinct stories
- Briefing quality: No repeated stories about same entity
- User feedback: Narrative list feels coherent, not fragmented

**Metrics to track:**
- `narratives.count()` grouped by `nucleus_entity` (should approach 1-3, not 5+)
- Consolidation pass merge count (should trend toward 0)
- Focus extraction failure rate (monitor for "unknown" or empty focus)

---

## References

- [FEATURE-008: Fix duplicate narrative detection](../../external-tickets/FEATURE-008-fix-duplicate-narratives.md)
- Narrative service: `src/crypto_news_aggregator/services/narrative_service.py`
- Original narrative detection ADR: `docs/decisions/narrative-detection-system.md`

---

## Follow-up

- [ ] Review this decision after 2 weeks of production data
- [ ] Consider adding focus taxonomy (if common focuses emerge)
- [ ] Evaluate semantic embeddings as focus similarity refinement (3-6 months)
- [ ] Monitor LLM costs for focus extraction (should be negligible)
