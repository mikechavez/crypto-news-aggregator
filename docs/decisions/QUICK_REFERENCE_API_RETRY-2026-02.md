# Quick Reference: API Retry Logic

## 🎯 What Was Added

Exponential backoff retry logic for Anthropic API errors in narrative discovery.

## 📍 Location

**File:** `src/crypto_news_aggregator/services/narrative_themes.py`  
**Function:** `discover_narrative_from_article()`  
**Lines:** ~487-528

## 🔢 Retry Behavior

| Error Type | Status Code | Detection | Backoff Strategy | Wait Times |
|------------|-------------|-----------|------------------|------------|
| **Rate Limit** | 429 | `'429'` or `'rate_limit'` in error | Exponential | 5s, 10s, 20s, 40s |
| **Overload** | 529 | `'529'` or `'overloaded'` in error | Linear | 10s, 20s, 30s, 40s |
| **Other** | Any | All other exceptions | None | No retry |
| **JSON Parse** | N/A | `json.JSONDecodeError` | Simple | 1s (existing) |

## 🔧 Configuration

```python
# Default (4 attempts)
narrative_data = await discover_narrative_from_article(article)

# Custom retry count
narrative_data = await discover_narrative_from_article(article, max_retries=5)
```

## 📊 Formulas

```python
# Rate Limit (Exponential)
wait_time = (2 ** attempt) * 5

# Overload (Linear)
wait_time = 10 * (attempt + 1)
```

## 🔍 Log Messages

```bash
# Warning (retry in progress)
⚠️  Rate limited for article abc12345... Waiting 10s before retry 2/4

# Error (max retries exhausted)
❌ Max retries exhausted due to rate limiting for article abc12345...

# Error (unexpected, no retry)
❌ Unexpected error for article abc12345...: ConnectionError: Connection timeout
```

## ✅ Testing

```bash
# Run retry logic tests
poetry run pytest tests/services/test_api_retry_logic.py -v

# Run all narrative theme tests
poetry run pytest tests/services/test_narrative_themes.py -v
```

## 📈 Monitoring

Watch for these patterns in Railway logs:
- `⚠️  Rate limited` - API quota issues
- `⚠️  API overloaded` - Infrastructure issues
- `❌ Max retries exhausted` - Persistent failures

## 🚀 Deployment Checklist

- [x] Implementation complete
- [x] Tests passing (9/9 new, 42/42 existing)
- [x] Documentation complete
- [ ] Create feature branch
- [ ] Commit changes
- [ ] Create PR
- [ ] Deploy to Railway
- [ ] Monitor logs

## 📝 Key Changes

1. Added `import asyncio` at module level
2. Increased `max_retries` from 3 to 4
3. Added exponential backoff for 429 errors
4. Added linear backoff for 529 errors
5. Enhanced error logging with emojis
6. Added 9 comprehensive tests

## 🎓 Best Practices Applied

- ✅ Exponential backoff for rate limits
- ✅ Linear backoff for overload
- ✅ No retry for unrecoverable errors
- ✅ Clear, actionable logging
- ✅ Comprehensive test coverage
- ✅ Configurable retry limits
