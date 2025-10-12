# Narrative Caching Implementation

**Date**: 2025-10-12  
**Status**: ✅ Complete

## Overview

Implemented content-based caching for narrative discovery to enable safe resume of backfill operations and prevent wasting API calls on already-processed articles.

## Changes Made

### 1. Core Function Updates

**File**: `src/crypto_news_aggregator/services/narrative_themes.py`

#### Added Hash Import
- Added `import hashlib` at the top of the file

#### Updated Function Signature
Changed `discover_narrative_from_article()` to accept article dict instead of individual parameters:

**Before**:
```python
async def discover_narrative_from_article(
    article_id: str,
    title: str,
    summary: str,
    max_retries: int = 3
) -> Optional[Dict[str, Any]]:
```

**After**:
```python
async def discover_narrative_from_article(
    article: Dict,
    max_retries: int = 3
) -> Optional[Dict[str, Any]]:
```

#### Added Caching Logic

**At function start** (after docstring):
1. Extract article ID and content fields
2. Generate SHA1 hash from `title:summary` content
3. Check if article already has:
   - Matching `narrative_hash`
   - Valid `narrative_summary`
   - Valid `actors` list
4. Skip processing if all conditions met (return `None`)
5. Log appropriate message:
   - ✓ Skipping if hash matches
   - ♻️ Re-extracting if content changed
   - 🔄 Processing if new article

**At validation success** (line ~430):
- Add `narrative_hash` to returned `narrative_data` dict

### 2. Caller Updates

Updated all callers to pass article dict instead of individual parameters:

#### `backfill_narratives_for_recent_articles()` 
**File**: `src/crypto_news_aggregator/services/narrative_themes.py`
- Changed to pass `article` dict
- Added `narrative_hash` to database update

#### `backfill_narratives.py` Script
**File**: `scripts/backfill_narratives.py`
- Changed to pass `article` dict
- Added `narrative_hash` to database update

### 3. Test Updates

**File**: `tests/services/test_narrative_themes.py`

Updated all test cases to use new signature:
- Modified `sample_article_data` fixture to include `_id` and `description`
- Updated all `discover_narrative_from_article()` calls to pass article dict
- Updated 8 test functions total

## How Caching Works

### Hash Generation
```python
content_for_hash = f"{title}:{summary}"
content_hash = hashlib.sha1(content_for_hash.encode()).hexdigest()
```

### Cache Hit Logic
Article is skipped if:
1. `existing_hash == content_hash` (content unchanged)
2. `existing_summary` exists (has narrative data)
3. `existing_actors` exists (has actors list)

### Cache Miss Scenarios
Article is re-processed if:
1. No existing hash (new article)
2. Hash mismatch (content changed)
3. Missing narrative data (incomplete processing)

### Database Schema
New field added to articles collection:
- `narrative_hash` (string): SHA1 hash of article content

## Benefits

1. **Safe Resume**: Backfill can be interrupted and resumed without duplicate API calls
2. **Cost Savings**: Skip re-processing unchanged articles
3. **Content Change Detection**: Automatically re-extract if article content changes
4. **Idempotent**: Running backfill multiple times is safe and efficient

## Testing

All tests pass:
- ✅ `test_discover_narrative_from_article_success`
- ✅ `test_discover_narrative_empty_content`
- ✅ `test_discover_narrative_missing_fields`
- ✅ `test_discover_narrative_llm_error`
- ✅ All validation integration tests (5 tests)

Manual caching verification:
- ✅ Cached article skipped (returns `None`)
- ✅ Changed article re-processed (hash mismatch)
- ✅ New article processed (no hash)

## Usage Example

```python
# Article with existing narrative data
article = {
    "_id": "abc123",
    "title": "SEC Sues Binance",
    "description": "The SEC has filed a lawsuit...",
    "narrative_hash": "a1b2c3...",  # Existing hash
    "narrative_summary": "...",      # Existing data
    "actors": ["SEC", "Binance"]     # Existing data
}

# Will skip processing and return None
result = await discover_narrative_from_article(article)
# result = None (cache hit)

# Article with changed content
article["title"] = "SEC Sues Binance - Updated"
# Hash will mismatch, triggers re-processing
result = await discover_narrative_from_article(article)
# result = {..., "narrative_hash": "new_hash"}
```

## Next Steps

The backfill script can now be safely run with:
```bash
poetry run python scripts/backfill_narratives.py --hours 720 --limit 1000
```

If interrupted, simply re-run the same command. Already-processed articles will be skipped automatically.
