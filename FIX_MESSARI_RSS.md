# Fix Messari RSS Feed Issue

**Date:** 2025-10-09  
**Priority:** Low (affects 1/13 sources)

## Problem

Messari RSS feed (`https://messari.io/rss`) is configured but not producing articles.

**Root cause:** Vercel bot protection blocks RSS access
- Returns HTTP 429 (Too Many Requests)
- Requires `x-vercel-challenge-token` header
- Feed parser receives malformed XML
- Zero entries parsed

## Solution Options

### Option 1: Remove from RSS Configuration (RECOMMENDED)
**Effort:** Low  
**Impact:** Removes broken feed, cleans up configuration

**Steps:**
1. Comment out or remove messari from `RSSService.feed_urls`
2. Keep "messari" in ArticleCreate model for future use
3. Add comment explaining why it was removed

**Code change:**
```python
# In src/crypto_news_aggregator/services/rss_service.py
self.feed_urls = {
    # ... other feeds ...
    # "messari": "https://messari.io/rss",  # Removed - Vercel bot protection blocks RSS
}
```

### Option 2: Implement Messari API Integration
**Effort:** High  
**Impact:** Adds Messari content via official API

**Requirements:**
- Messari API key (may require paid plan)
- New service class for Messari API
- API rate limit handling
- Different data structure than RSS

**Not recommended:** High effort for single source

### Option 3: Use Browser Automation
**Effort:** Very High  
**Impact:** Bypasses bot protection but adds complexity

**Requirements:**
- Selenium/Playwright for browser automation
- Headless browser setup
- Significantly slower than RSS parsing
- More fragile (breaks if site changes)

**Not recommended:** Overkill for RSS feed

## Recommended Action

**Remove messari from RSS configuration** (Option 1)

This is the cleanest solution:
- Removes broken feed from active configuration
- Keeps model validation for future API integration
- Documents why it was removed
- No ongoing maintenance burden

## Implementation

Create a feature branch and remove messari:

```bash
git checkout -b fix/remove-broken-messari-rss
```

Edit `src/crypto_news_aggregator/services/rss_service.py`:
- Comment out messari line
- Add explanatory comment about Vercel bot protection

Commit and create PR:
```bash
git add src/crypto_news_aggregator/services/rss_service.py
git commit -m "fix: remove messari RSS feed (blocked by Vercel bot protection)"
git push origin fix/remove-broken-messari-rss
```

## Testing

After removal:
1. Run RSS fetcher locally
2. Verify no errors for messari
3. Confirm other 12 sources still work
4. Check logs for any messari-related errors

## Future Considerations

If Messari content is desired:
1. Investigate Messari API (https://messari.io/api)
2. Check if they offer a public RSS feed alternative
3. Consider web scraping as last resort (with rate limiting)
