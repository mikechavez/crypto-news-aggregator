# Narrative Matching Quick Reference

## Function Signature

```python
async def find_matching_narrative(
    fingerprint: Dict[str, Any],
    within_days: int = 14
) -> Optional[Dict[str, Any]]
```

## Import

```python
from src.crypto_news_aggregator.services.narrative_service import find_matching_narrative
```

## Basic Usage

```python
# Create fingerprint
fingerprint = {
    'nucleus_entity': 'SEC',
    'top_actors': ['SEC', 'Binance', 'Coinbase'],
    'key_actions': ['filed lawsuit', 'regulatory enforcement']
}

# Check for match
existing = await find_matching_narrative(fingerprint, within_days=14)

if existing:
    # Merge into existing narrative
    narrative_id = existing['_id']
    print(f"Merging into: {existing['title']}")
else:
    # Create new narrative
    print("Creating new narrative")
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `fingerprint` | `Dict[str, Any]` | Required | Narrative fingerprint with `nucleus_entity`, `top_actors`, `key_actions` |
| `within_days` | `int` | `14` | Time window in days to search for matches |

## Return Value

- **Match found**: Returns narrative dict with all fields (`_id`, `title`, `status`, `article_count`, etc.)
- **No match**: Returns `None`

## Similarity Threshold

**Threshold: 0.6**

Narratives with similarity > 0.6 are considered matches.

### Similarity Calculation

| Component | Weight | Description |
|-----------|--------|-------------|
| Actor overlap | 50% | Jaccard similarity of `top_actors` |
| Nucleus match | 30% | Exact match of `nucleus_entity` |
| Action overlap | 20% | Jaccard similarity of `key_actions` |

## Query Filters

The function searches narratives matching:
- `last_updated >= cutoff_time` (within time window)
- `status in ['emerging', 'rising', 'hot', 'cooling', 'dormant']`

## Time Windows

| Use Case | Recommended Window |
|----------|-------------------|
| Breaking news | 7 days |
| Standard narratives | 14 days (default) |
| Long-term trends | 30 days |
| Historical analysis | 60+ days |

## Examples

### Example 1: Standard Check

```python
fingerprint = {
    'nucleus_entity': 'Bitcoin',
    'top_actors': ['MicroStrategy', 'Tesla'],
    'key_actions': ['purchased', 'investment']
}

match = await find_matching_narrative(fingerprint)
```

### Example 2: Custom Time Window

```python
# Check last 7 days only
match = await find_matching_narrative(fingerprint, within_days=7)
```

### Example 3: Integration with Narrative Creation

```python
async def create_or_update_narrative(cluster):
    # Extract fingerprint from cluster
    fingerprint = extract_narrative_fingerprint(cluster)
    
    # Check for existing narrative
    existing = await find_matching_narrative(fingerprint, within_days=14)
    
    if existing:
        # Update existing narrative
        await update_narrative(
            narrative_id=existing['_id'],
            new_article_ids=cluster['article_ids']
        )
        logger.info(f"Updated narrative: {existing['title']}")
        return existing['_id']
    else:
        # Create new narrative
        narrative_id = await create_narrative(cluster)
        logger.info(f"Created new narrative: {narrative_id}")
        return narrative_id
```

## Logging

The function logs:
- **Debug**: Similarity score for each candidate
- **Info**: Number of candidates evaluated
- **Info**: Best match found (with similarity score)
- **Info**: No match found (with best similarity score)

## Error Handling

- Catches all exceptions
- Logs exception with full traceback
- Returns `None` on error (allows graceful fallback)

## Performance Considerations

### Database Query
- Queries only narratives within time window
- Filters by active statuses
- Consider adding index on `last_updated` and `status`

### Similarity Calculation
- O(n) where n = number of candidate narratives
- Typically 10-100 candidates for 14-day window
- Fast enough for real-time use

## Testing

Run tests:
```bash
poetry run pytest tests/services/test_narrative_matching.py -v
```

Test coverage:
- ✅ Match found above threshold
- ✅ No match (below threshold)
- ✅ No candidates in time window
- ✅ Legacy narrative format
- ✅ Custom time window

## Common Patterns

### Pattern 1: Prevent Duplicates

```python
# Before creating narrative
existing = await find_matching_narrative(fingerprint)
if not existing:
    await create_narrative(cluster)
```

### Pattern 2: Merge Articles

```python
existing = await find_matching_narrative(fingerprint)
if existing:
    # Add new articles to existing narrative
    existing['article_ids'].extend(new_article_ids)
    existing['article_count'] = len(existing['article_ids'])
    await save_narrative(existing)
```

### Pattern 3: Reactivate Dormant Narratives

```python
existing = await find_matching_narrative(fingerprint, within_days=30)
if existing and existing['status'] == 'dormant':
    # Reactivate narrative with new articles
    existing['status'] = 'emerging'
    existing['article_ids'].extend(new_article_ids)
    await save_narrative(existing)
```

## Troubleshooting

### No matches found when expected

1. Check time window - may need to increase `within_days`
2. Verify fingerprint format - must have `nucleus_entity`, `top_actors`, `key_actions`
3. Check narrative status - only searches active statuses
4. Review similarity threshold - may need to adjust (currently 0.6)

### Too many false positives

1. Decrease time window - use shorter `within_days`
2. Increase similarity threshold in code (currently 0.6)
3. Improve fingerprint quality - more specific actors/actions

### Performance issues

1. Add database index: `db.narratives.createIndex({last_updated: 1, status: 1})`
2. Reduce time window
3. Limit number of candidates with additional filters

## Related Functions

- `extract_narrative_fingerprint()` - Extract fingerprint from article cluster
- `calculate_fingerprint_similarity()` - Calculate similarity between fingerprints
- `upsert_narrative()` - Save or update narrative in database

## Next Steps

After finding a match:
1. Merge article IDs
2. Update article count
3. Recalculate lifecycle stage
4. Update momentum
5. Refresh last_updated timestamp
6. Optionally regenerate summary
