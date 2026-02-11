# Article Links Feature - Implementation Summary

**Branch:** `feature/article-links`  
**Status:** ✅ Complete and Tested  
**Date:** 2025-10-07

## Overview

Added clickable article links to both Signals and Narratives pages, allowing users to view and access the actual articles that mention trending entities or support narrative themes.

---

## Changes Implemented

### 1. Backend API Updates

#### **Signals API** (`src/crypto_news_aggregator/api/v1/endpoints/signals.py`)

**Added Function:**
```python
async def get_recent_articles_for_entity(entity: str, limit: int = 5)
```
- Queries `entity_mentions` collection to find articles mentioning the entity
- Fetches up to 5 most recent articles per signal
- Uses MongoDB ObjectId to correctly link mentions to articles
- Returns: `title`, `url`, `source`, `published_at`

**Updated Endpoint:**
- `/api/v1/signals/trending` now includes `recent_articles` array in each signal
- Articles are fetched in parallel for all signals

**Key Fix:**
- Corrected article lookup to use `_id` field instead of `source_id` (entity_mentions stores MongoDB ObjectIds, not source URLs)

#### **Narratives API** (`src/crypto_news_aggregator/api/v1/endpoints/narratives.py`)

**Added Function:**
```python
async def get_articles_for_narrative(article_ids: List[str], limit: int = 20)
```
- Fetches up to 20 articles per narrative from stored `article_ids`
- Converts string IDs to ObjectIds for database query
- Returns same fields as signals: `title`, `url`, `source`, `published_at`

**Updated Endpoint:**
- `/api/v1/narratives/active` now includes `articles` array in each narrative
- Uses existing `article_ids` field from narrative documents

---

### 2. Frontend Type Definitions

#### **TypeScript Types** (`context-owl-ui/src/types/index.ts`)

**New Interface:**
```typescript
export interface ArticleLink {
  title: string;
  url: string;
  source: string;
  published_at: string;
}
```

**Updated Interfaces:**
- `Signal` interface: Added `recent_articles: ArticleLink[]`
- `Narrative` interface: Added `articles: ArticleLink[]`

---

### 3. Frontend UI Components

#### **Signals Page** (`context-owl-ui/src/pages/Signals.tsx`)

**Features Added:**
- Collapsible "▶ Recent mentions (X)" section below each signal card
- Shows count of available articles
- Expands on click to reveal article list
- Each article displays:
  - Title as clickable link (opens in new tab)
  - Source name (capitalized)
  - Relative time (e.g., "2 hours ago")
- Collapsed by default
- State managed with `useState<Set<number>>` for multiple expandable sections

**UI Styling:**
- Articles in light gray background (`bg-gray-50`)
- Blue clickable links with hover effects
- Small text size for compact display
- Border separator from other sections

#### **Narratives Page** (`context-owl-ui/src/pages/Narratives.tsx`)

**Features Added:**
- Collapsible "▶ 📰 View X articles" section below each narrative card
- Same interaction pattern as Signals page
- Displays up to 20 articles per narrative
- Identical styling and layout to Signals for consistency

**Query Optimization:**
- Added `staleTime: 0` to force fresh data fetches
- Prevents stale cached data from showing

---

## Technical Details

### Database Schema
- **entity_mentions collection**: Stores `article_id` as MongoDB ObjectId
- **articles collection**: Primary key is `_id` (ObjectId), `source_id` is the URL
- **narratives collection**: Stores `article_ids` as array of ObjectId strings

### API Response Format

**Signals Response:**
```json
{
  "signals": [
    {
      "entity": "JPMorgan",
      "recent_articles": [
        {
          "title": "Bitcoin Miners Posted Record Profits...",
          "url": "https://www.coindesk.com/markets/...",
          "source": "coindesk",
          "published_at": "2025-10-07T14:29:06"
        }
      ]
    }
  ]
}
```

**Narratives Response:**
```json
{
  "theme": "payments",
  "title": "Crypto Innovations Disrupt...",
  "articles": [
    {
      "title": "BNY Mellon Launches...",
      "url": "https://...",
      "source": "cointelegraph",
      "published_at": "2025-10-07T13:21:10"
    }
  ]
}
```

---

## Testing & Validation

### Backend Tests
✅ Article fetch functions execute without errors  
✅ API endpoints return `recent_articles` and `articles` fields  
✅ ObjectId conversion works correctly  
✅ Empty arrays returned when no articles found  

### Frontend Tests
✅ TypeScript compilation succeeds  
✅ Build completes without errors  
✅ UI renders article sections correctly  
✅ Expand/collapse functionality works  
✅ Links open in new tabs  
✅ Relative time formatting displays correctly  

### Manual Testing
✅ Verified with curl that API returns article data  
✅ Confirmed browser receives and displays articles  
✅ Tested with multiple signals and narratives  
✅ Verified all links are clickable and functional  

---

## Commits

1. **feat: add clickable article links to Signals and Narratives pages**
   - Initial implementation of backend and frontend changes
   - Added article fetch functions to both APIs
   - Updated TypeScript types
   - Implemented collapsible UI sections

2. **fix: correct article ID lookup to use MongoDB ObjectId instead of source_id**
   - Fixed critical bug in article fetching
   - Changed from `source_id` to `_id` lookup
   - Ensures articles are correctly linked to mentions

3. **fix: add staleTime to force fresh data fetch and debug logging**
   - Added query optimization to prevent stale data
   - Included debug logging for troubleshooting

---

## Deployment Notes

### Environment Configuration
- **Development**: Frontend must point to `http://localhost:8000` via `.env.local`
- **Production**: Frontend points to Railway production URL via `.env`

### Local Development Setup
```bash
# Backend
poetry run uvicorn src.crypto_news_aggregator.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (create .env.local first)
cd context-owl-ui
echo "VITE_API_URL=http://localhost:8000" > .env.local
echo "VITE_API_KEY=<your-key>" >> .env.local
npm run dev
```

### Production Deployment
- Merge `feature/article-links` to `main` via PR
- Railway will auto-deploy backend changes
- Frontend will automatically use production API URL

---

## User Experience

### Before
- Users saw trending signals but couldn't access source articles
- Narratives showed article counts but no way to read them
- No direct path from insight to source material

### After
- **Signals Page**: Click "Recent mentions (X)" to see up to 5 recent articles per signal
- **Narratives Page**: Click "📰 View X articles" to see up to 20 articles per narrative
- All article links open in new tabs for easy reference
- Clean, collapsible UI keeps pages uncluttered by default

---

## Future Enhancements

Potential improvements for future iterations:
- [ ] Add article preview/snippet on hover
- [ ] Filter articles by source or date
- [ ] Sort articles by relevance or recency
- [ ] Add "View all articles" link to dedicated page
- [ ] Cache article data to reduce API calls
- [ ] Add loading states for article fetching
- [ ] Implement pagination for narratives with many articles

---

## Files Changed

### Backend
- `src/crypto_news_aggregator/api/v1/endpoints/signals.py`
- `src/crypto_news_aggregator/api/v1/endpoints/narratives.py`

### Frontend
- `context-owl-ui/src/types/index.ts`
- `context-owl-ui/src/pages/Signals.tsx`
- `context-owl-ui/src/pages/Narratives.tsx`

### Documentation
- `ARTICLE_LINKS_FEATURE.md` (this file)

---

## Success Metrics

- ✅ Zero TypeScript errors
- ✅ Zero runtime errors
- ✅ All API endpoints return expected data structure
- ✅ UI renders correctly on all tested browsers
- ✅ Feature works with real production data
- ✅ Performance impact negligible (parallel fetching)

---

**Ready for PR and deployment to production.**
