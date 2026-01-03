# 002. Rule-Based Article Relevance Classification

**Date:** 2026-01-02

**Status:** Accepted

**Deciders:** MC

**Related Tickets:** FEATURE-008

---

## Context

Signals and narratives were surfacing too much noise - gaming news, price predictions, speculation articles that aren't market-moving. We needed a way to filter articles by relevance before they feed into signal scoring and narrative clustering.

Key constraints:
- Minimize additional LLM cost (user requirement: "keep additional llm cost to a minimum")
- No source authority weighting (user requirement: "the whole point of the app is to not have to rely on a bias toward any specific source")
- Must work on ~24k existing articles and all new ingestion

---

## Decision

Use rule-based regex pattern matching to classify articles into three relevance tiers:

- **Tier 1 (High):** Regulatory news, security incidents, ETF flows, institutional moves
- **Tier 2 (Medium):** Standard crypto news (default)
- **Tier 3 (Low):** Gaming, speculation, price predictions - excluded from signals/narratives

Classification happens at RSS ingestion time and is stored on the article document. Signals and narratives filter to only include Tier 1 and Tier 2 articles.

---

## Alternatives Considered

### Option 1: LLM-Based Classification

**Description:** Use Claude Haiku to classify each article's relevance

**Pros:**
- More nuanced understanding of content
- Can handle edge cases better
- Adaptable without code changes

**Cons:**
- Cost per article (~$0.001-0.005 each)
- Latency added to ingestion
- 24k backfill would cost $24-120

**Why not chosen:** User explicitly wanted minimal LLM cost. Rule-based is $0.

### Option 2: Source Authority Weighting

**Description:** Weight articles based on publication source credibility

**Pros:**
- Simple to implement
- Leverages known source quality

**Cons:**
- Creates bias toward specific sources
- Defeats purpose of aggregation

**Why not chosen:** User explicitly rejected this approach - "the whole point of the app is to not have to rely on a bias toward any specific source"

### Option 3: Query-Time Filtering

**Description:** Filter by patterns at query time instead of storing tier

**Pros:**
- No migration/backfill needed
- Rules can change without data update

**Cons:**
- Repeated computation on every query
- Can't pre-filter at aggregation level
- Slower queries

**Why not chosen:** Filtering once at ingestion is more efficient

---

## Consequences

### Positive

- Zero additional LLM cost
- Fast classification (~1ms per article)
- Easy to tune patterns based on production data
- Backward compatible (unclassified articles included)

### Negative

- Less nuanced than LLM classification
- Patterns need manual tuning (CHORE-001 created)
- May miss edge cases that LLM would catch

### Neutral

- Need to monitor tier distribution in production
- May need periodic pattern updates as crypto landscape evolves

---

## Implementation Notes

- Key file(s) affected: `src/crypto_news_aggregator/services/relevance_classifier.py`
- Migration required: Yes (backfill script created)
- Breaking changes: No (unclassified articles still included)
- Documentation updated: Yes (current-sprint.md)

---

## Validation

- Tier distribution should be roughly: 5-15% Tier 1, 80-90% Tier 2, 5-10% Tier 3
- Dry run showed: 10% Tier 1, 88% Tier 2, 2% Tier 3 (acceptable)
- Signals page should show fewer gaming/speculation entities
- Narratives should focus on market-moving themes

---

## Follow-up

- [ ] Complete backfill of ~24k articles
- [ ] Monitor tier distribution in production
- [ ] Tune patterns based on real data (CHORE-001)
- [ ] Review this decision after 2 weeks of production data
