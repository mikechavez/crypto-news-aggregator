# Salience-Based Clustering Test Results

## Test Run: Production Data (48 hours)

### Summary
- **Total articles in DB**: 288 articles
- **Articles with narrative data**: ~1-10 (most failed)
- **Narratives generated**: 1
- **Expected narratives**: 10-20

### Root Cause Analysis

#### 1. JSON Parsing Failures
**Problem**: LLM responses include explanatory text before JSON
```
"Here is the analysis of the given article: { "actors": [...] }"
```

**Fix Applied**: 
- Updated `clean_json_response()` to extract JSON object from text
- Added explicit prompt instruction: "Respond with ONLY valid JSON"

#### 2. Missing Narrative Data
**Problem**: 287 out of 288 articles missing `nucleus_entity` and `actors`

**Causes**:
- Backfill limit of 100 articles (only processes 100 out of 288)
- JSON parsing errors causing `discover_narrative_from_article()` to return `None`
- Articles not getting updated when extraction fails

#### 3. Defensive Coding Issues
**Problem**: Code crashed when `actors` or `actor_salience` was `None`

**Fix Applied**:
- Added `or []` and `or {}` defaults in clustering function
- Added skip logic for articles missing critical data
- Better error handling in iteration loops

## Code Changes Made

### 1. `narrative_themes.py` - JSON Extraction
```python
# Extract JSON object if there's text before it
first_brace = response_clean.find('{')
last_brace = response_clean.rfind('}')

if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
    response_clean = response_clean[first_brace:last_brace + 1]
```

### 2. `narrative_themes.py` - Defensive Clustering
```python
actors = article.get('actors') or []
actor_salience = article.get('actor_salience') or {}
tensions = article.get('tensions') or []

# Skip articles with missing critical data
if not nucleus or not actors:
    logger.warning(f"Skipping article {idx} - missing nucleus or actors")
    continue
```

### 3. `narrative_themes.py` - Stricter Prompt
```python
**CRITICAL**: Respond with ONLY valid JSON. Do not include any explanatory text, 
markdown formatting, or commentary. Start your response with { and end with }.
```

## Rate Limiting Fix

### Anthropic Rate Limits
- **50 requests/minute**
- **30,000 input tokens/minute** (Sonnet 4.x)
- **~1,300 tokens per article** (prompt + response)

### Solution: Batch Processing
Updated `backfill_narratives.py` to:
- Process **20 articles per batch**
- Wait **30 seconds between batches**
- **~40 articles/minute** (stays under limits)
- **Estimated time**: ~7 minutes for 288 articles

### Additional Fixes
- **Increased max_tokens** from 1024 → 2048 in `anthropic.py`
- **Better error logging** for truncated responses
- **0.5s delay** between articles within batch

## Next Steps

### Immediate Actions
1. ✅ **Added rate limiting** to backfill script
2. ✅ **Increased token limit** to prevent truncation
3. **Run backfill** with rate limiting
4. **Re-test clustering** after articles have narrative data

### Testing Strategy
```bash
# 1. Backfill all articles with rate limiting (takes ~7 minutes)
poetry run python scripts/backfill_narratives.py --hours 48 --limit 300 --batch-size 20 --batch-delay 30

# 2. Test clustering
poetry run python scripts/test_salience_with_real_data.py

# 3. Check success rate
# Expected: 80%+ articles with narrative data
# Expected: 10-20 narratives generated
```

### Success Criteria
- ✅ 80%+ articles successfully extract narrative data
- ✅ 10-20 narratives generated from 288 articles
- ✅ Bitcoin in <50% of narratives
- ✅ No JSON parsing errors
- ✅ Diverse nucleus entities (not all Bitcoin/Ethereum)

## Technical Debt
- [ ] Add retry logic for LLM failures
- [ ] Cache narrative extractions to avoid re-processing
- [ ] Add metrics for JSON parsing success rate
- [ ] Consider using structured output from LLM provider
- [ ] Add integration test with mock LLM responses
