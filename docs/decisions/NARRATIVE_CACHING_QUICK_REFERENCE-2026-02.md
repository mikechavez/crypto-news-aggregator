# Narrative Caching Quick Reference

## What Changed

The `discover_narrative_from_article()` function now:
1. **Accepts article dict** instead of individual parameters
2. **Checks content hash** before processing
3. **Skips unchanged articles** automatically
4. **Returns hash** in narrative data for storage

## Function Signature

**Old**:
```python
await discover_narrative_from_article(
    article_id="abc123",
    title="SEC Sues Binance",
    summary="The SEC has filed..."
)
```

**New**:
```python
await discover_narrative_from_article(
    article={
        "_id": "abc123",
        "title": "SEC Sues Binance",
        "description": "The SEC has filed..."
    }
)
```

## Caching Behavior

### ✅ Cache Hit (Skipped)
Returns `None` when:
- Article has `narrative_hash` matching current content
- Article has `narrative_summary` (not empty)
- Article has `actors` list (not empty)

**Log**: `✓ Skipping article abc123... - narrative data already current`

### ♻️ Content Changed (Re-processed)
Re-processes when:
- Article has `narrative_hash` but it doesn't match current content

**Log**: `♻️ Article abc123... content changed - re-extracting narrative`

### 🔄 New Article (Processed)
Processes when:
- Article has no `narrative_hash`
- Article missing narrative data

**Log**: `🔄 Processing article abc123...`

## Database Updates

When updating articles, include the hash:

```python
await articles_collection.update_one(
    {"_id": article["_id"]},
    {"$set": {
        "actors": narrative_data.get("actors", []),
        "actor_salience": narrative_data.get("actor_salience", {}),
        "nucleus_entity": narrative_data.get("nucleus_entity", ""),
        "actions": narrative_data.get("actions", []),
        "tensions": narrative_data.get("tensions", []),
        "implications": narrative_data.get("implications", ""),
        "narrative_summary": narrative_data.get("narrative_summary", ""),
        "narrative_hash": narrative_data.get("narrative_hash", ""),  # ← Add this
        "narrative_extracted_at": datetime.now(timezone.utc)
    }}
)
```

## Safe Resume Example

```bash
# Start backfill
poetry run python scripts/backfill_narratives.py --hours 720 --limit 1000

# Interrupt with Ctrl+C after processing 200 articles
^C

# Resume - will skip the 200 already processed
poetry run python scripts/backfill_narratives.py --hours 720 --limit 1000
# ✓ Skipping article abc123... - narrative data already current
# ✓ Skipping article def456... - narrative data already current
# 🔄 Processing article ghi789... (new article)
```

## Testing

Run tests to verify caching works:
```bash
poetry run pytest tests/services/test_narrative_themes.py -v
```

All 42 tests should pass.
