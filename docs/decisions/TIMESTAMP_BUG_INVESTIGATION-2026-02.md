# Timestamp Bug Investigation - Still Seeing Negative Widths

## Current Status

### Database Check
✅ **Database is clean** - No narratives with `first_seen > last_updated` found
- Ran aggregation pipeline to find reversed timestamps
- Result: 0 reversed narratives out of 156 total

### Frontend Error
❌ **UI still showing negative widths**
- Error: `width: -0.37873720925534826`
- Input data shows: `first_seen: '2025-10-23T06:01:36.857000'`, `last_updated: '2025-10-23T04:56:04'`
- This is ~1.5 hours reversed

### Hypothesis
The bug is **NOT in the database** but in the **API response transformation** or **article lookup**.

## Investigation Path

### Step 1: Check API Response Transformation
Added logging to `src/crypto_news_aggregator/api/v1/endpoints/narratives.py`:

**Log prefixes to monitor**:
- `[API TIMESTAMP BUG]` - When first_seen > last_updated in API response
- `[API TIMESTAMP OK]` - When first_seen <= last_updated (normal)
- `[API DEBUG]` - When last_article_at differs from last_updated

### Step 2: Identify the Source
The API endpoint does a complex aggregation pipeline:

1. **Lookup articles** by article_ids to find the most recent article
2. **Extract published_at** from the most recent article
3. **Set last_article_at** to that published_at timestamp
4. **Frontend uses** `last_article_at || last_updated` as the display timestamp

**Potential issues**:
- The article lookup might be returning articles from a different narrative
- The lookup might be returning an old/wrong article
- The lookup might be failing silently and returning null

### Step 3: Monitor Logs After Deployment

Deploy the code with debug logging and monitor Railway logs for:

```
[API TIMESTAMP BUG] Narrative 'xxx': first_seen=... > last_updated=...
[API DEBUG] Narrative 'xxx': last_article_at=... differs from last_updated=...
[API DEBUG] Narrative 'xxx': No last_article_at, using last_updated=...
```

## Root Cause Candidates

### Candidate 1: Article Lookup Bug
The aggregation pipeline lookup might be:
- Matching articles from wrong narrative
- Returning articles in wrong order
- Returning null/empty array

**Fix**: Verify the `$lookup` pipeline is correctly filtering by article_ids

### Candidate 2: Timezone Issue
- Database stores UTC datetimes
- API might be converting to different timezone
- Frontend might be parsing timezone incorrectly

**Fix**: Ensure all timestamps use UTC consistently

### Candidate 3: Data Corruption During API Response
- The API might be swapping or mishandling timestamps during transformation
- The fallback logic might be using wrong fields

**Fix**: Add validation in API response transformation

## Next Steps

1. **Deploy** code with debug logging
2. **Monitor** Railway logs for `[API TIMESTAMP BUG]` and `[API DEBUG]` entries
3. **Identify** which narratives are affected
4. **Check** if it's a lookup issue or transformation issue
5. **Fix** the identified code path
6. **Verify** no more negative widths in UI

## Files Modified

- `src/crypto_news_aggregator/api/v1/endpoints/narratives.py`
  - Added timestamp ordering validation logging
  - Added last_article_at lookup debugging
  - Commit: 65843f8

## Related Code

### Article Lookup Pipeline (lines 203-223)
```python
{'$lookup': {
    'from': 'articles',
    'let': {'article_ids': '$article_ids'},
    'pipeline': [
        {'$match': {
            '$expr': {
                '$in': [{'$toString': '$_id'}, '$$article_ids']
            }
        }},
        {'$project': {'published_at': 1}},
        {'$sort': {'published_at': -1}},
        {'$limit': 1}
    ],
    'as': 'recent_articles'
}},
```

### Last Article At Extraction (lines 219-223)
```python
{'$addFields': {
    'last_article_at': {
        '$arrayElemAt': ['$recent_articles.published_at', 0]
    }
}},
```

### Frontend Usage (Narratives.tsx line 541)
```typescript
const displayUpdated = narrative.last_article_at || narrative.last_updated || narrative.updated_at;
```

## Testing Commands

### Check for reversed timestamps in API response
```bash
# Monitor logs for [API TIMESTAMP BUG] entries
tail -f railway-logs.txt | grep "API TIMESTAMP"
```

### Manually test API endpoint
```bash
curl http://localhost:8000/api/v1/narratives/active?limit=10 | jq '.[] | {theme, first_seen, last_updated, last_article_at}'
```

### Check article lookup in MongoDB
```javascript
// Find a narrative and manually check its articles
db.narratives.findOne({theme: "xxx"}, {article_ids: 1}).article_ids.slice(0, 5)

// Then check those articles
db.articles.find({_id: {$in: [ObjectId("..."), ...]}}, {published_at: 1}).sort({published_at: -1})
```
