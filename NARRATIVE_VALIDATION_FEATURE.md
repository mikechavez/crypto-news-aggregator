# Narrative Validation Feature

## Summary
Added LLM response validation to catch malformed narrative data before saving to database, with automatic retry logic for validation failures.

## Implementation Date
October 12, 2025

## Changes Made

### 1. Validation Function (`validate_narrative_json`)
**Location**: `src/crypto_news_aggregator/services/narrative_themes.py` (lines 20-70)

**Features**:
- ✅ Validates all required fields: `actors`, `actor_salience`, `nucleus_entity`, `actions`, `tensions`, `narrative_summary`
- ✅ Type checking for all fields
- ✅ Caps actors list at 20 to prevent bloat
- ✅ Auto-fix: Ensures `nucleus_entity` is in `actors` list
- ✅ Validates salience scores are numeric and in range 1-5
- ✅ Ensures `nucleus_entity` has a salience score
- ✅ Validates `narrative_summary` is at least 10 characters

**Return Value**: `Tuple[bool, Optional[str]]`
- `(True, None)` if validation passes
- `(False, error_message)` if validation fails

### 2. Integration with `discover_narrative_from_article()`
**Location**: `src/crypto_news_aggregator/services/narrative_themes.py` (lines 288-428)

**Enhancements**:
- Added `max_retries` parameter (default: 3)
- Implemented retry loop for validation failures
- Validates LLM response before returning
- Logs validation success/failure with ✓/✗ symbols
- Retries with 1-second delay between attempts
- Returns `None` after max retries exhausted

**Retry Logic**:
```python
for attempt in range(max_retries):
    # Call LLM
    # Parse JSON
    # Validate
    if is_valid:
        return narrative_data
    else:
        if attempt < max_retries - 1:
            await asyncio.sleep(1)
            continue
        else:
            return None
```

## Test Coverage

### Unit Tests (20 tests)
**Location**: `tests/services/test_narrative_themes.py::TestValidateNarrativeJson`

**Coverage**:
1. ✅ Valid data passes validation
2. ✅ Missing required fields detected
3. ✅ Empty actors list rejected
4. ✅ Non-list actors rejected
5. ✅ Actors capped at 20
6. ✅ Empty nucleus_entity rejected
7. ✅ Non-string nucleus_entity rejected
8. ✅ Auto-adds nucleus to actors (with salience)
9. ✅ Auto-adds nucleus to actors (without salience fails)
10. ✅ Non-dict actor_salience rejected
11. ✅ Invalid salience type rejected
12. ✅ Salience < 1 rejected
13. ✅ Salience > 5 rejected
14. ✅ Float salience scores accepted
15. ✅ Missing nucleus salience rejected
16. ✅ Narrative summary < 10 chars rejected
17. ✅ Non-string narrative summary rejected
18. ✅ Exactly 10 char summary accepted
19. ✅ All required fields validated

### Integration Tests (5 tests)
**Location**: `tests/services/test_narrative_themes.py::TestValidateNarrativeJsonIntegration`

**Coverage**:
1. ✅ Valid LLM response passes validation
2. ✅ Malformed LLM response caught (missing nucleus_entity)
3. ✅ Empty actors list caught
4. ✅ Invalid salience scores caught (out of range)
5. ✅ Auto-fix nucleus in actors works

## Test Results
```bash
poetry run pytest tests/services/test_narrative_themes.py -v
```

**Results**: 42 passed, 7 skipped, 6 warnings in 8.11s

## Benefits

### 1. Data Quality
- Prevents malformed data from entering database
- Ensures all required fields are present
- Validates data types and ranges

### 2. Robustness
- Automatic retry on validation failure
- Graceful degradation (returns None after retries)
- Auto-fixes common issues (nucleus in actors)

### 3. Debugging
- Clear validation error messages
- Detailed logging with ✓/✗ symbols
- Tracks retry attempts

### 4. Performance
- Caps actors at 20 to prevent bloat
- Early validation before database write
- Reduces downstream errors

## Usage Example

```python
# Automatic validation in discover_narrative_from_article
narrative_data = await discover_narrative_from_article(
    article_id="123",
    title="SEC Sues Binance",
    summary="The SEC has filed a lawsuit...",
    max_retries=3  # Optional, defaults to 3
)

# Manual validation
from crypto_news_aggregator.services.narrative_themes import validate_narrative_json

data = {
    "actors": ["SEC", "Binance"],
    "actor_salience": {"SEC": 5, "Binance": 4},
    "nucleus_entity": "SEC",
    "actions": ["Filed lawsuit"],
    "tensions": ["Regulation"],
    "narrative_summary": "SEC enforcement action."
}

is_valid, error = validate_narrative_json(data)
if is_valid:
    # Save to database
    pass
else:
    logger.error(f"Validation failed: {error}")
```

## Logging Output

**Success**:
```
DEBUG: ✓ Validation passed for article abc123
```

**Failure with retry**:
```
WARNING: ✗ Validation failed for article abc123: Invalid salience 10 for SEC (must be 1-5)
INFO: Retrying with stricter prompt (attempt 2/3)
```

**Max retries exhausted**:
```
ERROR: Max retries exhausted for article abc123, validation failed: Missing required field: nucleus_entity
```

## Future Enhancements

1. **Adaptive prompts**: Modify prompt based on validation error type
2. **Validation metrics**: Track validation failure rates
3. **Partial recovery**: Save partial data with warnings
4. **Schema versioning**: Support multiple validation schemas
5. **Custom validators**: Allow plugin validators for specific use cases

## Related Files
- `src/crypto_news_aggregator/services/narrative_themes.py` - Implementation
- `tests/services/test_narrative_themes.py` - Test suite
- `NARRATIVE_THEME_REBUILD.md` - Context document
- `NARRATIVE_DISCOVERY_ANALYSIS.md` - Analysis document
