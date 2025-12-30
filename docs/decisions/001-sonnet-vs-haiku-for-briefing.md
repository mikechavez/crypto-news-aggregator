# 001. Use Claude Sonnet 4.5 for Briefing Generation

**Date:** 2025-12-29

**Status:** Accepted

**Deciders:** MC, Claude Code

**Related Tickets:** FEATURE-002, FEATURE-003

---

## Context

The briefing agent was initially using Claude Haiku (cheaper, faster model) to generate daily intelligence briefings. However, testing revealed that Haiku consistently hallucinated content despite explicit anti-hallucination prompts and rules.

Problems observed with Haiku:
- Added non-existent facts (e.g., "FalconX CEO", "SEC restructuring")
- Mentioned entities/people not in source data (e.g., "Binance CEO CZ")
- Couldn't reliably follow complex instruction sets
- Generic filler language despite explicit prohibitions

Success criteria:
- Zero hallucinated content in briefings
- Professional analyst tone
- All provided narratives covered
- Customer-facing quality

---

## Decision

**Upgrade briefing generation to Claude Sonnet 4.5** for all briefing operations.

This applies to:
- Morning briefing generation
- Evening briefing generation
- Narrative summarization within briefings
- Any critique/refinement steps

Haiku remains in use for:
- Entity extraction (batch processing)
- High-volume, low-complexity tasks

---

## Alternatives Considered

### Option 1: Continue with Haiku + Better Prompting

**Description:** Iterate on prompt engineering to eliminate hallucinations while using Haiku

**Pros:**
- Significantly cheaper ($0.80/$4 per 1M tokens vs $3/$15)
- Faster response times
- Lower operational costs (~$20-30/month)

**Cons:**
- Multiple prompt iterations already failed
- Haiku fundamentally struggles with complex instructions
- Risk of hallucinations in customer-facing content
- Time cost of continued iteration

**Why not chosen:** After extensive testing, Haiku couldn't reliably follow anti-hallucination rules. The quality risk for customer-facing briefings is unacceptable.

### Option 2: Hybrid Approach (Haiku + Sonnet Validation)

**Description:** Use Haiku to generate, Sonnet to validate/correct

**Pros:**
- Lower cost than pure Sonnet
- Adds validation layer
- Could catch hallucinations

**Cons:**
- Complex pipeline to maintain
- 2x API calls per briefing
- Sonnet validation still costs similar tokens
- Adds latency
- Doesn't solve root problem (Haiku generating bad content)

**Why not chosen:** Added complexity for minimal cost savings. If we're using Sonnet anyway, might as well use it for generation.

---

## Consequences

### Positive

- **Zero hallucinations** - Sonnet reliably follows anti-hallucination instructions
- **Professional quality** - Output suitable for customer-facing product
- **Maintainability** - Simpler pipeline (one model, not validation chain)
- **Trust** - Can confidently deploy automated briefings
- **Scalability** - Quality doesn't degrade with volume

### Negative

- **Cost increase** - ~12x more expensive per token
  - Haiku: ~$0.015 per briefing
  - Sonnet: ~$0.18 per briefing
  - Daily cost: $0.36 (2 briefings/day)
  - Monthly: ~$11/month (up from ~$1/month)
- **Slower generation** - Sonnet takes ~5-10s vs Haiku's 2-3s
- **Budget impact** - Need to monitor LLM costs more carefully

### Neutral

- Sets precedent for "quality over cost" for customer-facing features
- May need to optimize other areas to offset cost
- Cost tracking becomes more important

---

## Implementation Notes

- **Key files affected:**
  - `src/crypto_news_aggregator/services/briefing_agent.py`
  - `src/crypto_news_aggregator/services/narrative_themes.py`
- **Migration required:** No (config change only)
- **Breaking changes:** No (API remains same)
- **Documentation updated:** Yes (in ticket FEATURE-002)

**Code changes:**
```python
# Before
model = "claude-3-5-haiku-20241022"

# After
model = "claude-sonnet-4-5-20250929"
```

---

## Validation

**Success metrics:**
- ✅ Zero hallucinated facts in 10+ test briefings
- ✅ All anti-hallucination rules followed consistently
- ✅ Professional analyst tone achieved
- ✅ Generic filler language eliminated
- ✅ Cost: $11/month (acceptable for Phase 2 Intelligence feature)

**Monitoring:**
- Track LLM costs via `cost_tracking` collection
- Spot-check briefings for quality
- User feedback once deployed

---

## References

- [FEATURE-002: Upgrade to Sonnet 4.5](../../development/done/feature-briefing-upgrade-to-sonnet.md)
- [FEATURE-003: Briefing Prompt Engineering](../../development/in-progress/feature-briefing-prompt-engineering.md)
- [Anthropic Model Pricing](https://www.anthropic.com/pricing)

---

## Follow-up

- [x] Deploy to production (completed 2025-12-29)
- [x] Verify cost impact after 1 week
- [ ] Consider Sonnet for other customer-facing content (narratives?)
- [ ] Review this decision in 1 month (2025-01-29)
