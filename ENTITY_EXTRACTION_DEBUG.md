# Entity Extraction Debug Logging

## Problem
Entity extraction returns 0 entities despite successful Anthropic API calls.

## Hypothesis
The issue is likely one of:
1. **JSON parsing failing silently** - Response format doesn't match expected structure
2. **Response format mismatch** - Claude returns different structure than expected
3. **Entities being filtered out** - Validation logic removing all entities
4. **Database save failing silently** - Entities extracted but not persisted

## Changes Made (Commit: 6655fdd)

### 1. Added Logging to `anthropic.py` (extract_entities_batch)

**After API response:**
```python
logger.info(f"Raw Anthropic response (first 500 chars): {response_text[:500]}")
```

**After parsing JSON:**
```python
logger.info(f"Parsed {len(results)} article results from LLM")
logger.info(f"Sample result structure - primary_entities: {primary_count}, context_entities: {context_count}")
logger.info(f"Sample primary entities: {first_result.get('primary_entities', [])[:3]}")
logger.info(f"Sample context entities: {first_result.get('context_entities', [])[:3]}")
```

### 2. Added Logging to `rss_fetcher.py` (process_new_articles_from_mongodb)

**After batch extraction:**
```python
logger.info(f"Entity extraction returned {results_count} results for batch")
logger.info(f"Batch entity breakdown: {total_primary} primary entities, {total_context} context entities")
```

**Per article processing:**
```python
logger.info(f"Article {article_id_str}: {len(primary_entities)} primary, {len(context_entities)} context entities")
logger.warning(f"Article {article_id_str}: No entities extracted")
```

**Database save:**
```python
logger.info(f"Attempting to save {len(mentions_to_create)} entity mentions to database")
logger.info(f"Successfully saved {len(mentions_to_create)} entity mentions")
```

## What to Look For in Railway Logs

### 1. Check Raw API Response
Look for: `Raw Anthropic response (first 500 chars):`
- Is it valid JSON?
- Does it contain entity data?
- Is it wrapped in markdown code blocks?

### 2. Check Parsed Results
Look for: `Parsed X article results from LLM`
- Is X > 0?
- Do results have `primary_entities` and `context_entities` keys?
- Are the entity arrays populated?

### 3. Check Entity Counts
Look for: `Batch entity breakdown:`
- Are primary_entities > 0?
- Are context_entities > 0?
- If both are 0, the LLM isn't extracting entities

### 4. Check Per-Article Processing
Look for: `Article {id}: X primary, Y context entities`
- Are entities being mapped to the correct article IDs?
- Do we see warnings: `No entities extracted`?

### 5. Check Database Saves
Look for: `Attempting to save X entity mentions`
- Is X > 0?
- Do we see `Successfully saved X entity mentions`?
- Any errors between attempt and success?

## Expected Log Flow (Success Case)

```
INFO: Attempting entity extraction with Haiku 3.5
INFO: Raw Anthropic response (first 500 chars): [{"article_index": 0, "article_id": "...
INFO: Parsed 5 article results from LLM
INFO: Sample result structure - primary_entities: 3, context_entities: 2
INFO: Sample primary entities: [{'name': 'Bitcoin', 'type': 'cryptocurrency', ...}]
INFO: Successfully extracted entities using Haiku 3.5
INFO: Entity extraction returned 5 results for batch
INFO: Batch entity breakdown: 15 primary entities, 10 context entities
INFO: Article 67890abc: 3 primary, 2 context entities
INFO: Preparing to create entity mentions for article 67890abc
INFO: Attempting to save 5 entity mentions to database
INFO: Successfully saved 5 entity mentions
```

## Expected Log Flow (Failure Cases)

### Case 1: JSON Parsing Fails
```
INFO: Raw Anthropic response (first 500 chars): ```json\n[{"article_index": 0...
ERROR: Failed to parse JSON response from Haiku 3.5: ...
```
**Fix:** Strip markdown code blocks before parsing

### Case 2: Empty Response
```
INFO: Raw Anthropic response (first 500 chars): [{"article_index": 0, "article_id": "...", "primary_entities": [], "context_entities": []}]
INFO: Parsed 5 article results from LLM
INFO: Batch entity breakdown: 0 primary entities, 0 context entities
```
**Fix:** Check prompt, model temperature, or confidence threshold

### Case 3: Wrong Response Structure
```
INFO: Parsed 5 article results from LLM
ERROR: 'primary_entities' key not found
```
**Fix:** Update prompt or parsing logic to match actual response format

### Case 4: Database Save Fails
```
INFO: Attempting to save 15 entity mentions to database
ERROR: Failed to create entity mentions for article ...: ...
```
**Fix:** Check database connection, schema, or validation

## Next Steps

1. **Deploy to Railway** ✅ (Pushed to `fix/llm-provider-anthropic-only`)
2. **Wait for next RSS fetch cycle** (Check Railway logs)
3. **Analyze logs** using patterns above
4. **Identify root cause** based on where entities disappear
5. **Implement fix** based on findings

## Deployment Status

- **Branch:** `fix/llm-provider-anthropic-only`
- **Commit:** `6655fdd`
- **Status:** Pushed to GitHub, Railway will auto-deploy
- **Next Fetch:** Check Railway logs after next RSS cycle (every 30 minutes)
