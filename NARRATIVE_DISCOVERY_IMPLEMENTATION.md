# Narrative Discovery System Implementation

## Summary

Successfully replaced the rigid 12-theme classification system with a two-layer narrative discovery approach that captures nuanced narratives naturally.

## Problem Solved

**Before:** Articles were forced into 12 predefined themes, causing:
- Generic narratives like "Regulatory: Recent developments in crypto regulation"
- Entities showing as "Emerging" when they didn't fit neat categories
- Missed nuanced stories that crossed theme boundaries

**After:** Natural narrative discovery produces:
- Specific narratives like "SEC vs Major Exchanges: Regulators intensify enforcement against Binance and Coinbase"
- Rich context with actors, actions, and tensions
- Better clustering based on what's actually happening

## Architecture

### Layer 1: Discovery (Natural Narrative Extraction)
**Function:** `discover_narrative_from_article()`

Extracts from each article:
- **Actors**: People, organizations, protocols, assets, regulators
- **Actions**: Key events or actions that occurred
- **Tensions**: Forces at play (regulation vs innovation, centralization vs decentralization, etc.)
- **Implications**: Why it matters, what's shifting in the ecosystem
- **Narrative Summary**: Natural 2-3 sentence description

**Example Output:**
```json
{
  "actors": ["SEC", "Binance", "Coinbase"],
  "actions": ["SEC filed charges against exchanges"],
  "tensions": ["Regulation vs. Innovation", "Centralization vs. Decentralization"],
  "implications": "Enforcement actions mark escalation in regulatory pressure",
  "narrative_summary": "Regulators are tightening control over centralized cryptocurrency exchanges..."
}
```

### Layer 2: Mapping (Optional Theme Classification)
**Function:** `map_narrative_to_themes()`

Maps natural narratives to existing themes for:
- Backward compatibility
- Analytics and filtering
- Theme-based dashboards

Can suggest new themes when existing categories don't fit.

## Key Changes

### 1. Updated `narrative_themes.py`
- **New:** `discover_narrative_from_article()` - Layer 1 discovery
- **New:** `map_narrative_to_themes()` - Layer 2 mapping
- **New:** `get_articles_by_narrative_similarity()` - Cluster by actors/tensions
- **New:** `generate_narrative_from_cluster()` - Rich narrative summaries
- **Updated:** `backfill_narratives_for_recent_articles()` - Stores both layers
- **Maintained:** Legacy functions for backward compatibility

### 2. Updated `narrative_service.py`
- **New default:** Narrative-based clustering (groups by shared actors + tensions)
- **Legacy option:** Theme-based clustering (groups by themes)
- **Enhanced:** Narrative documents now include actors and tensions fields
- **Improved:** Generates specific narrative titles instead of generic ones

### 3. Updated Article Model
Added fields to `ArticleBase`:
```python
# Layer 1 fields
actors: Optional[List[str]]
actions: Optional[List[str]]
tensions: Optional[List[str]]
implications: Optional[str]
narrative_summary: Optional[str]

# Layer 2 fields
mapped_themes: Optional[List[str]]
suggested_new_theme: Optional[str]
narrative_extracted_at: Optional[datetime]
```

## Narrative Clustering Algorithm

Articles are grouped if they share:
- **2+ actors** (e.g., both mention "SEC" and "Binance")
- **OR 1+ tension** (e.g., both involve "Regulation vs Innovation")

This creates richer clusters than theme-only grouping:
- Theme-only: All "regulatory" articles grouped together
- Narrative-based: "SEC vs Exchanges" separate from "EU MiCA Regulation"

## Testing

Created `test_narrative_discovery.py` with 3 test cases:
1. ✅ Regulatory narrative → Correctly identified actors, tensions, mapped to "regulatory"
2. ✅ L2 scaling narrative → Identified competition, mapped to "layer2_scaling"
3. ✅ Emerging AI narrative → Discovered new category, suggested new theme

All tests passed successfully.

## Backward Compatibility

- ✅ `extract_themes_from_article()` still works (uses two-layer internally)
- ✅ `backfill_themes_for_recent_articles()` still works (calls new function)
- ✅ `generate_narrative_from_theme()` enhanced to use narrative summaries
- ✅ `themes` field still populated for legacy code
- ✅ Can toggle between narrative-based and theme-based clustering

## Expected Results

### Before (Theme-based)
```
Title: "Regulatory Narrative"
Summary: "Recent developments in crypto regulation"
Entities: [generic list]
```

### After (Narrative-based)
```
Title: "SEC vs Major Exchanges: Regulators intensify enforcement against Binance and Coinbase"
Summary: "Regulators are tightening control over centralized cryptocurrency exchanges..."
Actors: ["SEC", "Binance", "Coinbase"]
Tensions: ["Regulation vs. Innovation"]
Entities: [specific to this narrative]
```

## Usage

### Enable narrative-based clustering (default)
```python
narratives = await detect_narratives(
    hours=48,
    min_articles=2,
    use_narrative_clustering=True  # Default
)
```

### Use legacy theme-based clustering
```python
narratives = await detect_narratives(
    hours=48,
    min_articles=2,
    use_narrative_clustering=False
)
```

### Backfill narrative data for existing articles
```python
count = await backfill_narratives_for_recent_articles(hours=48, limit=100)
```

## Next Steps

1. **Deploy to production** - Test with real articles
2. **Monitor narrative quality** - Ensure LLM extracts meaningful narratives
3. **Tune clustering thresholds** - Adjust actor/tension matching criteria
4. **UI updates** - Display actors and tensions in narrative cards
5. **Analytics** - Track which tensions are most common over time

## Files Changed

- `src/crypto_news_aggregator/services/narrative_themes.py` - Core implementation
- `src/crypto_news_aggregator/services/narrative_service.py` - Clustering logic
- `src/crypto_news_aggregator/models/article.py` - Data model
- `test_narrative_discovery.py` - Test suite
- `alembic/versions/a1555ddf25dc_*.py` - Migration placeholder

## Commit

```
refactor: replace theme classification with narrative discovery system
```

Branch: `feature/narrative-discovery-system`
