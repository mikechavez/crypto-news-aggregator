# Salience Clustering Implementation - Complete

## Summary
Successfully integrated salience-based narrative clustering into the narrative service with shallow narrative merging.

## Changes Made

### 1. Added `merge_shallow_narratives` to `narrative_themes.py`
**Location**: `src/crypto_news_aggregator/services/narrative_themes.py`

**Function**: `async def merge_shallow_narratives(narratives: List[Dict]) -> List[Dict]`

**Purpose**: Merge single-article or weak narratives into nearest semantic cluster

**Logic**:
- Identifies shallow narratives:
  - 1 article AND < 3 unique actors
  - OR ubiquitous nucleus (Bitcoin/Ethereum) with < 3 articles
- Uses Jaccard similarity (overlap/union) to find best match
- Minimum threshold: 0.5 similarity to merge
- Falls back to standalone if no good match found

### 2. Added `backfill_narratives_for_recent_articles` to `narrative_themes.py`
**Location**: `src/crypto_news_aggregator/services/narrative_themes.py`

**Function**: `async def backfill_narratives_for_recent_articles(hours: int = 48, limit: int = 100) -> int`

**Purpose**: Backfill narrative data for articles without it

**Extracts and stores**:
- `actors` - list of entities
- `actor_salience` - salience scores (1-5)
- `nucleus_entity` - primary entity
- `actions` - key events
- `tensions` - forces at play
- `implications` - why it matters
- `narrative_summary` - 2-3 sentence summary

### 3. Added `generate_narrative_from_cluster` to `narrative_themes.py`
**Location**: `src/crypto_news_aggregator/services/narrative_themes.py`

**Function**: `async def generate_narrative_from_cluster(cluster: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]`

**Purpose**: Generate cohesive narrative from article cluster

**Aggregates**:
- All actors from cluster articles
- All tensions from cluster articles
- Primary nucleus entity (most common)
- Article IDs

**Returns**:
```python
{
    "title": "...",
    "summary": "...",
    "actors": [...],
    "tensions": [...],
    "nucleus_entity": "...",
    "article_ids": [...],
    "article_count": N
}
```

### 4. Updated `detect_narratives` in `narrative_service.py`
**Location**: `src/crypto_news_aggregator/services/narrative_service.py`

**New signature**:
```python
async def detect_narratives(
    hours: int = 48,
    min_articles: int = 3,
    use_salience_clustering: bool = True
) -> List[Dict[str, Any]]
```

**New flow (when `use_salience_clustering=True`)**:
1. Backfill narrative data for recent articles
2. Get articles with narrative data
3. Cluster by nucleus entity and weighted overlap
4. Generate narrative for each cluster
5. Merge shallow narratives
6. Save to database

**Old flow preserved** (when `use_salience_clustering=False`):
- Theme-based clustering still available as fallback
- Uses predefined theme categories

## Integration Points

### Database Schema
Articles now store:
```python
{
    "actors": ["Entity1", "Entity2"],
    "actor_salience": {"Entity1": 5, "Entity2": 4},
    "nucleus_entity": "Entity1",
    "actions": ["action1", "action2"],
    "tensions": ["tension1", "tension2"],
    "implications": "...",
    "narrative_summary": "...",
    "narrative_extracted_at": datetime
}
```

### Narratives Collection
Narratives use `nucleus_entity` as `theme` for database compatibility:
```python
{
    "theme": "SEC",  # nucleus_entity
    "title": "...",
    "summary": "...",
    "entities": [...],  # actors
    "article_ids": [...],
    "article_count": N,
    "mention_velocity": X.XX,
    "lifecycle": "emerging|hot|mature|declining"
}
```

## Clustering Algorithm

### Weighted Link Strength
- Same nucleus entity: **+1.0** (strongest signal)
- 2+ shared high-salience actors (≥4): **+0.7**
- 1 shared high-salience actor: **+0.4**
- 1+ shared tensions: **+0.3**

**Threshold**: Articles cluster if `link_strength >= 0.8`

### Shallow Narrative Merging
- Uses Jaccard similarity on actors
- Threshold: **0.5 minimum** to merge
- Ubiquitous entities: Bitcoin, Ethereum, crypto, blockchain, cryptocurrency

## Usage

### Default (Salience-based)
```python
from crypto_news_aggregator.services.narrative_service import detect_narratives

narratives = await detect_narratives(hours=48, min_articles=3)
```

### Fallback (Theme-based)
```python
narratives = await detect_narratives(
    hours=48, 
    min_articles=3,
    use_salience_clustering=False
)
```

## Testing Recommendations

1. **Unit tests** for `merge_shallow_narratives`:
   - Test shallow narrative detection
   - Test Jaccard similarity calculation
   - Test merge logic
   - Test fallback to standalone

2. **Integration tests** for `detect_narratives`:
   - Test full salience-based flow
   - Test with various article counts
   - Test shallow narrative merging
   - Verify database persistence

3. **Comparison tests**:
   - Run both salience and theme-based on same data
   - Compare narrative quality
   - Compare cluster sizes

## Next Steps

1. Add tests for new functions
2. Monitor narrative quality in production
3. Tune thresholds based on real data:
   - Link strength threshold (currently 0.8)
   - Shallow narrative criteria (currently 1 article + <3 actors)
   - Merge similarity threshold (currently 0.5)
4. Consider adding narrative deduplication across time windows
