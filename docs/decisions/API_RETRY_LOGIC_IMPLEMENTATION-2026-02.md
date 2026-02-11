# API Retry Logic Implementation

## Summary
Added exponential backoff retry logic to handle Anthropic API rate limits (429) and overload errors (529) in the narrative discovery function.

## Changes Made

### 1. Updated Function Signature
**File:** `src/crypto_news_aggregator/services/narrative_themes.py`

- Increased `max_retries` from 3 to 4 in `discover_narrative_from_article()`
- This allows for additional retry attempts when encountering API rate limits

### 2. Added asyncio Import
- Added `import asyncio` at module level (line 8)
- Removed duplicate import from inside the function

### 3. Enhanced Error Handling
Replaced generic `Exception` handler with specific handling for:

#### Rate Limit Errors (429)
- **Detection:** Checks for '429' in error message or 'rate_limit' in error string
- **Backoff Strategy:** Exponential backoff: 5s, 10s, 20s, 40s
- **Formula:** `wait_time = (2 ** attempt) * 5`
- **Logging:** Clear warning with wait time and retry count

#### API Overload Errors (529)
- **Detection:** Checks for '529' in error message or 'overloaded' in error string
- **Backoff Strategy:** Linear backoff: 10s, 20s, 30s, 40s
- **Formula:** `wait_time = 10 * (attempt + 1)`
- **Logging:** Clear warning with wait time and retry count

#### Other Unexpected Errors
- **Behavior:** No retry, immediate return
- **Logging:** Error type and message logged for debugging

## Error Handling Flow

```
Try:
  Call LLM API
  Parse JSON response
  Validate narrative data
  
Catch json.JSONDecodeError:
  Log warning
  Retry with 1s delay (up to max_retries)
  
Catch Exception:
  If 429 (rate limit):
    - Wait with exponential backoff
    - Retry if attempts remaining
    - Return None if max retries exhausted
    
  Elif 529 (overload):
    - Wait with linear backoff
    - Retry if attempts remaining
    - Return None if max retries exhausted
    
  Else (unexpected error):
    - Log error details
    - Return None immediately (no retry)
```

## Benefits

1. **Graceful Degradation:** Backfill can continue even when hitting API limits
2. **Automatic Recovery:** Retries with appropriate delays allow API to recover
3. **Clear Logging:** Emoji indicators (⚠️ for warnings, ❌ for errors) make logs easy to scan
4. **Efficient Backoff:** Exponential backoff for rate limits prevents hammering the API
5. **Fail Fast:** Unexpected errors don't waste retry attempts

## Testing Recommendations

1. **Rate Limit Testing:**
   - Run backfill with high concurrency to trigger rate limits
   - Verify exponential backoff delays are applied
   - Confirm successful retries after waiting

2. **Overload Testing:**
   - Monitor for 529 errors during peak usage
   - Verify linear backoff is applied
   - Confirm recovery after API stabilizes

3. **Error Logging:**
   - Check logs for clear error messages
   - Verify retry counts are accurate
   - Confirm wait times match expected backoff

## Usage

The retry logic is automatically applied when calling:

```python
narrative_data = await discover_narrative_from_article(article)
```

No changes needed to calling code. The function will:
- Retry up to 4 times for validation failures
- Apply exponential backoff for rate limits
- Apply linear backoff for overload errors
- Return None if all retries exhausted

## Next Steps

1. Monitor Railway logs during next backfill run
2. Adjust backoff timings if needed based on API behavior
3. Consider adding metrics to track retry rates
4. Document any patterns in rate limit triggers
