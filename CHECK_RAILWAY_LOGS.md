# Quick Railway Log Check Guide

## How to Check Logs

1. Go to Railway dashboard
2. Select the crypto-news-aggregator service
3. Click on "Deployments" tab
4. Click on the latest deployment
5. View logs in real-time or use the search feature

## Key Log Patterns to Search For

### 1. Entity Extraction Started
```
Search: "Processing entity extraction batch"
```
This shows when entity extraction begins for a batch of articles.

### 2. Raw API Response
```
Search: "Raw Anthropic response"
```
**What to check:**
- Is the response valid JSON?
- Does it start with `[` or `{`?
- Is it wrapped in markdown (```json)?
- Does it contain entity data?

### 3. Parsed Results
```
Search: "Parsed"
```
**What to check:**
- How many article results were parsed?
- Does the structure match expectations?
- Are primary_entities and context_entities present?

### 4. Entity Counts
```
Search: "Batch entity breakdown"
```
**What to check:**
- Total primary entities > 0?
- Total context entities > 0?
- If both are 0, LLM isn't extracting entities

### 5. Per-Article Results
```
Search: "Article.*primary.*context"
```
**What to check:**
- Are entities being assigned to articles?
- Any warnings about "No entities extracted"?

### 6. Database Saves
```
Search: "Attempting to save.*entity mentions"
```
**What to check:**
- Is the count > 0?
- Do you see "Successfully saved" after?
- Any errors between attempt and success?

## Quick Diagnosis

### If you see:
- ✅ "Raw Anthropic response" with JSON → API is working
- ✅ "Parsed X article results" where X > 0 → JSON parsing works
- ❌ "Batch entity breakdown: 0 primary entities, 0 context entities" → **LLM not extracting**
- ❌ "No entities extracted" for all articles → **Extraction or mapping issue**
- ❌ "Attempting to save 0 entity mentions" → **No entities to save**
- ❌ Error after "Attempting to save" → **Database save failing**

## Example Commands (if using Railway CLI)

```bash
# Tail logs in real-time
railway logs

# Search for specific pattern
railway logs | grep "entity"

# Get last 100 lines
railway logs --lines 100

# Filter by service
railway logs --service crypto-news-aggregator
```

## Timeline

- **RSS Fetch Interval:** Every 30 minutes
- **Next Expected Cycle:** Check current time + 30 minutes
- **Log Retention:** Railway keeps logs for 7 days

## What to Share

When sharing logs, include:
1. The full "Processing entity extraction batch" section
2. Any "Raw Anthropic response" logs
3. The "Batch entity breakdown" line
4. Any errors or warnings
5. Timestamp of the logs

## Expected Success Pattern

```
[timestamp] INFO: Processing entity extraction batch 0-5 of 5 articles
[timestamp] INFO: Attempting entity extraction with Haiku 3.5
[timestamp] INFO: Raw Anthropic response (first 500 chars): [{"article_index": 0, "article_id": "...
[timestamp] INFO: Parsed 5 article results from LLM
[timestamp] INFO: Sample result structure - primary_entities: 3, context_entities: 2
[timestamp] INFO: Successfully extracted entities using Haiku 3.5
[timestamp] INFO: Entity extraction returned 5 results for batch
[timestamp] INFO: Batch entity breakdown: 15 primary entities, 10 context entities
[timestamp] INFO: Article 67890abc: 3 primary, 2 context entities
[timestamp] INFO: Attempting to save 5 entity mentions to database
[timestamp] INFO: Successfully saved 5 entity mentions
```

If you don't see this pattern, the logs will show exactly where the process breaks down.
