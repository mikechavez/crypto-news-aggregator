# RSS Source Configuration Audit

**Date:** 2025-10-09  
**Status:** ✅ All configured sources are valid and producing articles

## Summary

- **Configured RSS sources:** 13 (12 working + 1 broken)
- **Valid sources in ArticleCreate model:** 22 (includes non-RSS sources)
- **Sources in database:** 12 (all working sources)
- **Broken sources:** 1 (messari - Vercel bot protection blocks RSS access)

## 1. Configured RSS Sources (rss_service.py)

The following 13 sources are configured in `RSSService.feed_urls`:

| # | Source | Status | Articles in DB | RSS URL |
|---|--------|--------|----------------|---------|
| 1 | coindesk | ✅ Working | 214 | https://www.coindesk.com/arc/outboundfeeds/rss/ |
| 2 | cointelegraph | ✅ Working | 254 | https://cointelegraph.com/rss |
| 3 | decrypt | ✅ Working | 227 | https://decrypt.co/feed |
| 4 | bitcoinmagazine | ✅ Working | 52 | https://bitcoinmagazine.com/.rss/full/ |
| 5 | theblock | ✅ Working | 20 | https://www.theblock.co/rss.xml |
| 6 | cryptoslate | ✅ Working | 10 | https://cryptoslate.com/feed/ |
| 7 | benzinga | ✅ Working | 10 | https://www.benzinga.com/feed |
| 8 | bitcoin.com | ✅ Working | 10 | https://news.bitcoin.com/feed/ |
| 9 | dlnews | ✅ Working | 100 | https://www.dlnews.com/arc/outboundfeeds/rss/ |
| 10 | watcherguru | ✅ Working | 10 | https://watcher.guru/news/feed |
| 11 | glassnode | ✅ Working | 15 | https://insights.glassnode.com/feed/ |
| 12 | messari | ❌ **BROKEN** | 0 | https://messari.io/rss |
| 13 | thedefiant | ✅ Working | 100 | https://thedefiant.io/feed |

**Total working sources:** 12/13 (92.3%)  
**Total articles:** 1,022

### Removed/Commented Sources
- ❌ **chaingpt** - Removed (returns 404)
- ❌ **delphidigital** - Not configured (SSL/XML issues noted)
- ❌ **bankless** - Not configured (SSL/XML issues noted)
- ❌ **galaxy** - Not configured (technical issues noted)
- ❌ **defillama** - Not configured (returns HTML instead of RSS)
- ❌ **dune** - Not configured (malformed XML)

## 2. Valid Sources in ArticleCreate Model

The `ArticleBase.source` Literal includes 22 valid source values:

### Non-RSS Sources (4)
1. twitter
2. telegram
3. rss (generic)
4. reddit

### RSS Sources (18)
5. chaingpt (legacy, feed removed)
6. coindesk ✅
7. cointelegraph ✅
8. decrypt ✅
9. bitcoinmagazine ✅
10. theblock ✅
11. cryptoslate ✅
12. benzinga ✅
13. messari ⚠️
14. bitcoin.com ✅
15. glassnode ✅
16. bankless (not configured)
17. thedefiant ✅
18. defillama (not configured)
19. dune (not configured)
20. galaxy (not configured)
21. dlnews ✅
22. watcherguru ✅

## 3. Sources in Database (Article Count)

```
benzinga: 10 articles
bitcoin.com: 10 articles
bitcoinmagazine: 52 articles
coindesk: 214 articles
cointelegraph: 254 articles
cryptoslate: 10 articles
decrypt: 227 articles
dlnews: 100 articles
glassnode: 15 articles
theblock: 20 articles
thedefiant: 100 articles
watcherguru: 10 articles
```

**Total:** 12 sources with 1,022 articles

## 4. Analysis: Missing Sources

### ⚠️ Messari Issue - DIAGNOSED
**Status:** Configured in RSS service but NO articles in database

**Root cause:** Messari RSS feed is protected by Vercel bot protection
- Returns HTTP 429 (Too Many Requests)
- Requires Vercel challenge token (`x-vercel-challenge-token`)
- Feed parser gets malformed XML: `not well-formed (invalid token)`
- Zero entries parsed from feed

**Action needed:** 
1. Remove messari from RSS configuration (cannot be fetched via simple RSS)
2. Consider alternative: Messari API integration (requires API key)
3. Update ArticleCreate model to keep "messari" as valid source for future API integration

### ✅ No Validation Mismatches
All 13 configured RSS sources have matching entries in the ArticleCreate model's Literal type. The recent fix for `bitcoincom` → `bitcoin.com` resolved the last validation mismatch.

## 5. Sources in Model But Not Configured

These sources are valid in the model but not actively configured in RSS service:

1. **twitter** - Non-RSS source (API-based)
2. **telegram** - Non-RSS source (API-based)
3. **rss** - Generic RSS source identifier
4. **reddit** - Non-RSS source (API-based)
5. **chaingpt** - Removed due to 404 errors
6. **bankless** - Not configured (SSL/XML issues)
7. **defillama** - Not configured (returns HTML)
8. **dune** - Not configured (malformed XML)
9. **galaxy** - Not configured (technical issues)

## 6. Recommendations

### Immediate Actions
1. **Investigate messari feed** - Run diagnostic to determine why no articles are being saved
2. **Monitor new sources** - benzinga, cryptoslate, bitcoin.com, watcherguru only have 10 articles each (likely recent additions)

### Future Improvements
1. **Add feed health monitoring** - Track which feeds are failing to parse
2. **Implement retry logic** - For feeds with intermittent issues
3. **Add feed validation tests** - Automated testing of all configured feeds
4. **Consider re-testing broken feeds** - bankless, galaxy, delphidigital may have fixed their issues

## 7. Frontend Display Issue

**Original concern:** "18 RSS sources configured but only 10 showing in frontend"

**Resolution:** 
- **13 sources configured** (not 18) - 12 working + 1 broken (messari)
- **12 sources have articles** in database (all working sources)
- The "18" likely counted sources in ArticleCreate model that aren't RSS feeds
- If frontend shows only 10 sources, possible causes:
  - Frontend filtering logic (may be hiding sources with few articles)
  - benzinga, cryptoslate, bitcoin.com, watcherguru only have 10 articles each
  - UI may have minimum article threshold for display
  - glassnode only has 15 articles

**Next step:** Check frontend source filtering and minimum article count thresholds.

## Conclusion

✅ **No validation mismatches found**  
✅ **All configured sources are valid in ArticleCreate model**  
⚠️ **1 source (messari) blocked by Vercel bot protection - should be removed from RSS config**  
✅ **Database contains articles from 12/13 configured sources (all working sources)**

### Recommended Actions
1. **Remove messari from RSS configuration** - Cannot be fetched via RSS due to bot protection
2. **Investigate frontend filtering** - Determine why only 10 sources show when 12 have articles
3. **Monitor new sources** - Ensure benzinga, cryptoslate, bitcoin.com, watcherguru continue fetching
4. **Add feed health checks** - Automated monitoring to catch broken feeds early
