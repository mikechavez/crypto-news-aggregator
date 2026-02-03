# 003. Signal Scoring: Compute on Read

**Date:** 2026-01-05

**Status:** Accepted

**Deciders:** User, Claude

**Related Tickets:** Signal scoring staleness investigation

---

## Context

Signal scores were stale - 1145 entities had scores, but none had been updated in 24+ hours, with the last updates from October 2025. Investigation revealed a fundamental architectural flaw:

**Root Cause (worker.py lines 50-54):**
```python
thirty_min_ago = datetime.now(timezone.utc) - timedelta(minutes=30)
cursor = entity_mentions_collection.find({
    "created_at": {"$gte": thirty_min_ago},
    "is_primary": True
})
```

Only entities mentioned in the last 30 minutes get refreshed. If an entity isn't mentioned for 2 hours, its 24h score becomes stale because old mentions don't "age out" of the calculation.

**Computation Cost:**
Each entity requires ~32 database operations across 4 timeframes (24h, 7d, 30d, legacy). A full backfill of 1000 entities would mean ~32,000 database operations.

**Key Finding:**
Briefings (the primary consumer) use **narratives**, not signal scores. The briefing agent prompt explicitly states: "Your role is to synthesize ONLY the narratives listed below into an insightful briefing." Signal scores serve as supplementary context, not primary content.

---

## Decision

Adopt the **Compute on Read** pattern for signal scoring:

1. **Remove background pre-computation** - Disable the worker task that updates signal_scores collection every 2 minutes
2. **Compute on API request** - Calculate signal scores on-demand when `/signals/trending` or `/signals` is called
3. **Cache results for 60 seconds** - Use Redis (with in-memory fallback) to cache computed results

This approach was chosen because:
- Signals are always fresh (computed from current entity_mentions data)
- Simpler architecture (no background worker complexity for signals)
- Appropriate for current usage patterns (signals page checked occasionally, not constantly)
- The primary use case (briefings) doesn't rely on pre-computed signals

---

## Alternatives Considered

### Option 2: Time-Bucketed Aggregates

**Description:** Create `entity_hourly_stats` collection with pre-computed hourly counts. On ingestion, increment current hour's bucket. API reads sum relevant buckets.

**Pros:**
- Fast reads (sum ~24-720 small docs)
- Correct aging (old hours naturally excluded)
- Historical trend analysis possible
- Scales well

**Cons:**
- More complex data model
- Need to update buckets on ingestion
- Storage overhead (~24 docs/entity/day)
- Migration required for existing data

**Why not chosen:** Over-engineered for current usage patterns. Would be appropriate if we needed sub-second response times or historical analytics, but neither is a current requirement.

### Option 3: Fix Current System

**Description:** Keep current architecture but expand refresh scope to include all entities with score > 0 OR recent mentions. Cache `_get_high_signal_article_ids()` to reduce redundant calls.

**Pros:**
- Minimal code changes
- No data model changes
- Quick to implement

**Cons:**
- Still computing full scores for 1000+ entities in background
- Still somewhat expensive
- Band-aid, not ideal architecture

**Why not chosen:** Doesn't address the fundamental issue that pre-computation isn't necessary for the current use case.

---

## Consequences

### Positive

- Signal scores are always fresh (no stale data ever)
- Simpler architecture (removed background worker complexity)
- No data duplication (no signal_scores collection drift)
- Lower background compute load on the database
- Easier to reason about (data source is entity_mentions)

### Negative

- First request each minute may be slower (2-5s compute time)
- Compute happens during user request (brief latency spike)
- Cannot easily query "historical" signal trends
- Compute cost shifted from background to request time

### Neutral

- Need to monitor cache hit rates
- May need to adjust cache TTL based on usage patterns
- signal_scores collection still exists but will become stale (cleanup TBD)

---

## Implementation Notes

- Key files affected:
  - `src/crypto_news_aggregator/services/signal_service.py` - Added `compute_trending_signals()` and `get_top_entities_by_mentions()`
  - `src/crypto_news_aggregator/api/v1/endpoints/signals.py` - Modified both endpoints to use compute-on-read
  - `src/crypto_news_aggregator/worker.py` - Disabled signal score update task
- Migration required: No
- Breaking changes: No (API response structure preserved)
- Documentation updated: Yes (this ADR)

---

## Validation

How will we know if this decision was successful?

- Response time < 5s for first uncached request
- Response time < 100ms for cached requests
- No more stale signal scores reported
- Cache hit rate > 80% under normal usage
- No increase in database connection issues

---

## References

- Analysis document: `docs/decisions/signal-scoring-architecture-analysis.md`
- Narrative system: `docs/decisions/narrative-detection-system.md`
- Worker code: `src/crypto_news_aggregator/worker.py`
- Signal service: `src/crypto_news_aggregator/services/signal_service.py`

---

## Follow-up

- [ ] Monitor first-request latency in production
- [ ] Consider cleanup of stale signal_scores collection
- [ ] Evaluate if time-bucketed aggregates needed for future analytics features
- [ ] Review this decision after 30 days of production usage
