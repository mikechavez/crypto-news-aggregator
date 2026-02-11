# Narrative Persistence Investigation

**Date:** 2025-10-14  
**Issue:** Narratives aren't persisting beyond 1-2 days

## Executive Summary

**Root Cause Identified:** Narratives are being **recreated daily** instead of updated, causing them to appear short-lived. The system creates new narratives every 48 hours based on the lookback window, rather than maintaining long-term narrative continuity.

---

## Key Findings

### 1. **Narrative Detection Logic (`detect_narratives`)**

**Location:** `src/crypto_news_aggregator/services/narrative_service.py:166-294`

**Current Behavior:**
- Runs every **10 minutes** (configured in `worker.py:309`)
- Uses a **48-hour lookback window** (default `hours=48`)
- Processes only articles from the last 48 hours
- Creates narratives from scratch each time based on this window

**Critical Issue:**
```python
# Line 192-193
cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
cursor = articles_collection.find({
    "published_at": {"$gte": cutoff_time},  # Only last 48 hours!
    "narrative_summary": {"$exists": True}
})
```

**Problem:** Articles older than 48 hours are **excluded** from narrative detection, so narratives naturally "die" after 2 days when their articles age out of the window.

---

### 2. **Narrative Matching/Merging Mechanism**

**Location:** `src/crypto_news_aggregator/services/narrative_themes.py:604-722`

**How Clustering Works:**
The system uses `cluster_by_narrative_salience()` to group articles:

```python
# Weighted link strength calculation (lines 674-694):
link_strength = 0.0

# Same nucleus entity: +1.0 (strongest signal)
if nucleus == cluster_nucleus:
    link_strength += 1.0

# 2+ shared high-salience actors (≥4): +0.7
if shared_core >= 2:
    link_strength += 0.7
elif shared_core >= 1:
    link_strength += 0.4

# Shared tensions: +0.3
if shared_tensions >= 1:
    link_strength += 0.3

# Cluster if link_strength >= 0.8
```

**Clustering Happens Per-Run:** Articles are clustered within each 48-hour window, but there's **no mechanism to match new clusters with existing narratives** from previous runs.

---

### 3. **The `upsert_narrative` Function**

**Location:** `src/crypto_news_aggregator/db/operations/narratives.py:64-195`

**How It Works:**
```python
# Line 108: Match by theme field
existing = await collection.find_one({"theme": theme})

if existing:
    # Update existing narrative
    update_data = {
        "title": title,
        "summary": summary,
        "entities": entities,
        "article_ids": article_ids,  # REPLACES old article_ids
        "article_count": article_count,
        "last_updated": now,
        # ... other fields
    }
```

**Critical Flaw:**
- Matches narratives by `theme` field (e.g., "SEC", "Bitcoin")
- **Replaces** `article_ids` instead of appending
- Only includes articles from the current 48-hour window
- Old articles are lost when the narrative is updated

**Example Scenario:**
1. **Day 1:** Narrative created with articles A, B, C (article_ids: [A, B, C])
2. **Day 2:** Same narrative updated with articles D, E (article_ids: [D, E])
3. **Result:** Articles A, B, C are **removed** from the narrative

---

### 4. **The `narrative_hash` Field**

**Location:** `src/crypto_news_aggregator/services/narrative_themes.py:314-318, 463, 782`

**Purpose:** Content-based caching to avoid re-extracting narrative data from articles

**Usage:**
```python
# Line 314-318: Generate hash from article content
content_for_hash = f"{article.get('title', '')}{article.get('summary', '')}"
content_hash = hashlib.sha1(content_for_hash.encode()).hexdigest()

# Check if we already have current narrative data
existing_hash = article.get('narrative_hash')
```

**Scope:** Only used for **article-level caching**, not for narrative deduplication or matching. Does not help with narrative persistence.

---

### 5. **Narrative Deletion/Archiving**

**Location:** `src/crypto_news_aggregator/db/operations/narratives.py:231-251`

**Function Exists But Not Used:**
```python
async def delete_old_narratives(days: int = 7) -> int:
    """Delete narratives older than specified days."""
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    result = await collection.delete_many({
        "last_updated": {"$lt": cutoff_date}
    })
    
    return result.deleted_count
```

**Status:** This function is **defined but never called** in the worker. Narratives are not being actively deleted.

**Verification:**
```bash
# Checked worker.py - no calls to delete_old_narratives()
grep -r "delete_old_narratives" src/crypto_news_aggregator/worker.py
# Result: No matches
```

---

## Why Narratives Appear Short-Lived

### The 48-Hour Window Problem

1. **Narrative Detection** runs every 10 minutes
2. Each run looks at articles from the **last 48 hours only**
3. Articles older than 48 hours are **excluded** from clustering
4. When `upsert_narrative` updates an existing narrative, it **replaces** the article list with only recent articles
5. After 48 hours, all original articles age out, making the narrative appear "new"

### Timeline Tracking Exists But Doesn't Help

The system has `timeline_data` and `days_active` fields (lines 111-159 in `narratives.py`), but these only track **how long the theme has been active**, not the actual article history.

```python
# Lines 177-192: New narrative structure
narrative_data = {
    "theme": theme,
    "first_seen": first_seen_date,  # Preserved across updates
    "last_updated": now,
    "article_ids": article_ids,  # Only current window articles
    "days_active": days_active,  # Calculated from first_seen
    "timeline_data": [timeline_snapshot],  # Daily snapshots
}
```

**The `first_seen` field is preserved**, but the article list is not cumulative.

---

## Proposed Solutions

### Option 1: Cumulative Article Tracking (Recommended)

**Modify `upsert_narrative` to append articles instead of replacing:**

```python
# In db/operations/narratives.py, line 144-159
if existing:
    # Get existing article IDs
    existing_article_ids = set(existing.get("article_ids", []))
    
    # Merge with new article IDs (keep all historical articles)
    all_article_ids = list(existing_article_ids | set(article_ids))
    
    # Optionally limit to most recent N articles (e.g., 100)
    # to prevent unbounded growth
    all_article_ids = all_article_ids[-100:]
    
    update_data = {
        # ... other fields
        "article_ids": all_article_ids,  # Cumulative list
        "article_count": len(all_article_ids),  # Total count
    }
```

**Pros:**
- Simple fix
- Preserves narrative history
- Shows true narrative longevity

**Cons:**
- Article list could grow large (mitigate with max limit)
- Old articles may not be relevant to current narrative state

---

### Option 2: Extend Lookback Window

**Change the detection window from 48 hours to 7+ days:**

```python
# In worker.py or narrative_service.py
narratives = await detect_narratives(hours=168)  # 7 days instead of 48
```

**Pros:**
- Captures longer narrative arcs
- Simple configuration change

**Cons:**
- Doesn't solve the root issue (still replaces articles)
- Increases computational load
- May cluster unrelated articles together

---

### Option 3: Narrative Continuity Matching

**Implement cross-run narrative matching:**

1. Before creating new narratives, fetch existing narratives from DB
2. Match new clusters to existing narratives using similarity scoring
3. Update matched narratives, create new ones for unmatched clusters

```python
# Pseudo-code for narrative_service.py
async def detect_narratives(hours=48):
    # Get existing narratives
    existing_narratives = await get_all_narratives()
    
    # Detect new clusters
    clusters = await cluster_by_narrative_salience(articles)
    
    # Match clusters to existing narratives
    for cluster in clusters:
        best_match = find_best_narrative_match(cluster, existing_narratives)
        
        if best_match:
            # Update existing narrative with new articles
            await update_narrative_with_cluster(best_match, cluster)
        else:
            # Create new narrative
            await create_narrative_from_cluster(cluster)
```

**Pros:**
- Maintains true narrative continuity
- Allows narratives to evolve over time
- Most accurate representation of narrative lifecycle

**Cons:**
- More complex implementation
- Requires careful similarity scoring
- May need tuning to avoid false matches

---

### Option 4: Hybrid Approach (Best Solution)

**Combine Options 1 and 3:**

1. Implement cumulative article tracking (Option 1)
2. Add narrative continuity matching (Option 3)
3. Keep 48-hour detection window but match to historical narratives
4. Optionally prune very old articles (e.g., keep last 30 days)

**Implementation Steps:**

1. **Modify `upsert_narrative`** to append articles (Option 1)
2. **Add narrative matching logic** before clustering:
   ```python
   # In narrative_service.py
   existing_narratives = await get_narratives_by_nucleus_entity(nucleus_entity)
   if existing_narratives:
       # Update existing narrative
       await append_articles_to_narrative(existing_narratives[0], new_articles)
   ```
3. **Add article pruning** to prevent unbounded growth:
   ```python
   # Keep only articles from last 30 days
   recent_article_ids = filter_articles_by_age(all_article_ids, days=30)
   ```

---

## Verification Steps

### Check Current Narrative Ages

```bash
# Connect to MongoDB and check narrative ages
poetry run python -c "
import asyncio
from crypto_news_aggregator.db.mongodb import mongo_manager, initialize_mongodb
from datetime import datetime, timezone

async def check_narratives():
    await initialize_mongodb()
    db = await mongo_manager.get_async_database()
    narratives = db.narratives
    
    async for n in narratives.find().sort('first_seen', 1):
        first_seen = n.get('first_seen')
        last_updated = n.get('last_updated')
        days_active = n.get('days_active', 0)
        article_count = n.get('article_count', 0)
        
        print(f\"Theme: {n.get('theme')}\")
        print(f\"  First seen: {first_seen}\")
        print(f\"  Last updated: {last_updated}\")
        print(f\"  Days active: {days_active}\")
        print(f\"  Article count: {article_count}\")
        print()

asyncio.run(check_narratives())
"
```

### Monitor Narrative Updates

```bash
# Watch narrative updates in real-time
poetry run python -c "
import asyncio
from crypto_news_aggregator.db.mongodb import mongo_manager, initialize_mongodb

async def watch_narratives():
    await initialize_mongodb()
    db = await mongo_manager.get_async_database()
    narratives = db.narratives
    
    # Get current narratives
    current = {}
    async for n in narratives.find():
        theme = n.get('theme')
        current[theme] = {
            'article_ids': set(n.get('article_ids', [])),
            'article_count': n.get('article_count', 0)
        }
    
    print('Current narratives:', list(current.keys()))
    print('Waiting 10 minutes for next update...')
    
    await asyncio.sleep(600)  # Wait 10 minutes
    
    # Check for changes
    async for n in narratives.find():
        theme = n.get('theme')
        new_article_ids = set(n.get('article_ids', []))
        
        if theme in current:
            old_ids = current[theme]['article_ids']
            added = new_article_ids - old_ids
            removed = old_ids - new_article_ids
            
            if added or removed:
                print(f\"\\nTheme: {theme}\")
                print(f\"  Articles added: {len(added)}\")
                print(f\"  Articles removed: {len(removed)}\")
                print(f\"  Total articles: {len(new_article_ids)}\")

asyncio.run(watch_narratives())
"
```

---

## Recommended Action Plan

### Phase 1: Quick Fix (Immediate)
1. Implement **Option 1** (cumulative article tracking)
2. Test with existing narratives
3. Monitor for 48 hours to verify persistence

### Phase 2: Enhanced Matching (1-2 days)
1. Implement **Option 3** (narrative continuity matching)
2. Add similarity scoring for nucleus entity + actors
3. Test matching accuracy

### Phase 3: Optimization (3-5 days)
1. Add article pruning (keep last 30 days)
2. Optimize clustering performance
3. Add metrics/logging for narrative lifecycle

### Phase 4: Validation (Ongoing)
1. Monitor narrative ages in production
2. Track `days_active` metric
3. Verify narratives persist beyond 7+ days

---

## Code Locations Reference

| Component | File | Lines |
|-----------|------|-------|
| Narrative Detection | `services/narrative_service.py` | 166-294 |
| Clustering Logic | `services/narrative_themes.py` | 604-722 |
| Upsert Function | `db/operations/narratives.py` | 64-195 |
| Worker Schedule | `worker.py` | 167-235 |
| API Endpoint | `api/v1/endpoints/narratives.py` | 127-236 |
| Delete Function | `db/operations/narratives.py` | 231-251 |

---

## Related Documentation

- `NARRATIVE_CACHING_IMPLEMENTATION.md` - Article-level caching (not narrative persistence)
- `NARRATIVE_TIMELINE_TRACKING.md` - Timeline data structure
- `SALIENCE_CLUSTERING_IMPLEMENTATION.md` - Clustering algorithm details
