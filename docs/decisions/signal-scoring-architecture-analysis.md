# Signal Scoring Architecture Analysis

## Context

Signal scores are stale - last updates from October 2025, none in the last 24 hours. Investigation revealed fundamental architectural issues with how scores are computed and maintained.

## Current Architecture

### How Signal Scores Work

The worker (`src/crypto_news_aggregator/worker.py`) runs every 2 minutes and:

1. Queries `entity_mentions` for entities mentioned in the **last 30 minutes only**
2. For each entity found, calculates signal scores across 4 timeframes (1h, 4h, 12h, 24h)
3. Stores results in `signal_scores` collection

### The Problem

```python
# worker.py line 50-54
thirty_min_ago = datetime.now(timezone.utc) - timedelta(minutes=30)
cursor = entity_mentions_collection.find({
    "created_at": {"$gte": thirty_min_ago},
    "is_primary": True
})
```

**Only entities mentioned in the last 30 minutes get refreshed.** If Bitcoin isn't mentioned for 2 hours, its 24h score becomes stale because old mentions don't "age out" of the calculation.

### Computation Cost Per Entity

Each call to `calculate_signal_score(entity, timeframe)` does:

| Operation | DB Queries |
|-----------|------------|
| `_get_high_signal_article_ids()` | 1 (scans all articles) |
| `calculate_mentions_and_velocity()` | +1 article scan, +2 count queries |
| `calculate_source_diversity()` | +1 article scan, +1 aggregation |
| `calculate_recency_factor()` | +1 article scan, +2 count queries |
| `calculate_sentiment_metrics()` | +1 article scan, +iterate all mentions |

**Total per timeframe:** ~8 queries + 4 full article table scans

**Per entity in worker:** 4 timeframes × 8 queries = ~32 DB operations

**Backfill of 1000 entities:** ~32,000 database operations

---

## How The System Connects

```
Articles (RSS)
    ↓
Entity Mentions (extracted entities from articles)
    ↓
┌─────────────────────────────────────────────────────┐
│                                                     │
↓                                                     ↓
Signal Scores                               Narratives
(trending entities)                    (story clusters)
"Bitcoin is hot"                      "SEC approves Bitcoin ETF"
    ↓                                         ↓
    └──────────────┬──────────────────────────┘
                   ↓
              Briefings
    (morning/evening summaries for user)
```

### What Each Component Does

| Component | Purpose | Used By |
|-----------|---------|---------|
| Signal Scores | "What entities are trending?" - velocity, mentions, sentiment | Signals UI page, Alerts |
| Narratives | "What stories are happening?" - clusters of related articles | Narratives UI page, Briefings |
| Briefings | Human-readable daily summary | End user consumption |

### Critical Finding: Briefings Use Narratives, Not Signals

From `briefing_agent.py`:

> "Your role is to synthesize ONLY the narratives listed below into an insightful briefing."

The briefing feature primarily uses **NARRATIVES**, not signals. Signals are passed as secondary context but the prompt explicitly instructs to only discuss narratives.

---

## Proposed Options

### Option 1: Compute on Read

**How it works:**
- Remove the `signal_scores` collection and background worker
- Calculate scores in real-time when API receives `/signals` request
- Cache result for 60 seconds

```
User requests /signals
  → Check cache (hit? return cached)
  → Miss: Query entity_mentions, calculate scores
  → Store in cache with 60s TTL
  → Return response
```

**User impact:**

| Pros | Cons |
|------|------|
| Always fresh - no stale data ever | First request each minute is slow (~2-5s) |
| No background jobs to manage | Compute happens during user request |
| Simpler architecture | Can't easily query "historical" signal trends |
| No data duplication | |

**Best for:** Apps where freshness matters more than latency, low-traffic endpoints

---

### Option 2: Time-Bucketed Aggregates

**How it works:**
- Create new collection `entity_hourly_stats` with pre-computed hourly counts
- When articles are ingested, increment the current hour's bucket
- API reads sum the relevant buckets (last 24 buckets for 24h score)

**Data structure:**
```json
{
  "entity": "Bitcoin",
  "hour": "2026-01-04T15:00:00Z",
  "mentions": 12,
  "sources": ["coindesk", "decrypt"],
  "sentiment_sum": 0.5
}
```

**User impact:**

| Pros | Cons |
|------|------|
| Fast reads (sum ~24-720 small docs) | More complex data model |
| Correct aging (old hours naturally excluded) | Need to update buckets on ingestion |
| Can query historical trends | Storage overhead (~24 docs/entity/day) |
| Scales well | Migration needed for existing data |

**Best for:** High-traffic apps, analytics dashboards, historical trend analysis

---

### Option 3: Fix Current System

**How it works:**
- Keep current architecture but fix inefficiencies
- Cache `_get_high_signal_article_ids()` (called 4x redundantly per calculation)
- Expand which entities get refreshed: all with score > 0 OR recent mentions
- Reduce refresh frequency (every 10 min instead of 2 min)

**User impact:**

| Pros | Cons |
|------|------|
| Minimal code changes | Still computing full scores for 1000+ entities |
| No data model changes | Still somewhat expensive |
| Keeps existing API contract | Band-aid, not ideal architecture |
| Quick to implement (~30 min) | May need backfill script for initial catch-up |

**Best for:** Quick fix when you need to ship something else

---

## Summary Comparison

| Option | Freshness | Page Load | Future-Proof | Dev Effort |
|--------|-----------|-----------|--------------|------------|
| Compute on Read | Perfect | 2-5s (first), instant (cached) | Yes | Medium |
| Time Buckets | ~1 hour lag | Fast always | Yes | Higher |
| Fix Current | Can drift stale | Fast | No | Low |

---

## Recommendation

Given that:
1. **Briefings don't need pre-computed signals** - they use narratives
2. **Signals page can compute on demand** - users check it occasionally
3. **Alerts can compute when checking conditions**

**Option 1 (Compute on Read)** appears to be the most pragmatic choice:
- Solves the staleness problem permanently
- Simplifies architecture (removes background worker complexity)
- Appropriate for current usage patterns

---

## Questions to Resolve

1. How often do users check the Signals page?
2. Is 2-5 second first-load latency acceptable?
3. Do we need historical signal trends in the future?
4. Should we consider removing signal_scores collection entirely?
