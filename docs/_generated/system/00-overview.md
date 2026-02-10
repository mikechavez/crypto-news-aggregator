# System Architecture Overview

## Overview

The Crypto News Aggregator is a distributed system for collecting cryptocurrency news, analyzing market narratives, and generating daily briefings. This document provides a high-level architectural view showing module interconnections, data flow, and key design decisions.

**Anchor:** `#architecture-overview`

## System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      External Data Sources                       │
│  RSS Feeds │ NewsAPI │ Reddit │ Twitter │ CoinDask │ CoinGecko  │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
        ┌──────────────────────────────────┐
        │      RSS Fetcher & Collector     │
        │  (background/news-fetching)      │
        │  - Fetch RSS feeds every 3hrs    │
        │  - Normalize article structure   │
        │  - Deduplicate via fingerprint   │
        └──────────────┬───────────────────┘
                       │
                       ▼
        ┌──────────────────────────────────┐
        │      Article Enrichment          │
        │  (tasks/process_article.py)      │
        │  - Entity extraction (NER)       │
        │  - Sentiment analysis            │
        │  - Relevance classification      │
        └──────────────┬───────────────────┘
                       │
        ┌──────────────▼──────────────────┐
        │                                  │
        ▼                                  ▼
┌─────────────────────┐        ┌──────────────────────┐
│   Narratives Index  │        │   Signals Detection  │
│  (detect patterns)  │        │  (identify trends)   │
│  - Clustering       │        │  - Market events     │
│  - Entity linking   │        │  - Price anomalies   │
│  - Theme detection  │        │  - Sentiment shifts  │
└─────────────┬───────┘        └──────────┬───────────┘
              │                           │
              └──────────────┬────────────┘
                             │
                             ▼
            ┌────────────────────────────┐
            │   Briefing Generation      │
            │  (services/briefing_agent) │
            │  - Gather context (LLM)    │
            │  - Self-refine quality     │
            │  - Track costs             │
            └────────────────┬───────────┘
                             │
                             ▼
              ┌──────────────────────────┐
              │    MongoDB (Persistence)  │
              │  - daily_briefings        │
              │  - narratives             │
              │  - articles               │
              │  - entity_mentions        │
              └──────────────┬────────────┘
                             │
                             ▼
              ┌──────────────────────────┐
              │   Frontend UI (React)    │
              │  - Briefings page        │
              │  - Narratives timeline   │
              │  - Signals dashboard     │
              │  - Articles archive      │
              └──────────────────────────┘
```

## Module Interconnections

### Data Ingestion Layer
- **RSS Fetcher** (`background/rss_fetcher.py`): Periodically fetches articles from configured feeds
- **News Collector** (`core/news_collector.py`): Normalizes articles to consistent schema
- **Fingerprinter** (`services/article_service.py`): Deduplicates via content hashing

### Enrichment Layer
- **Entity Extractor** (`services/entity_service.py`): Identifies companies, people, concepts via Claude API
- **Sentiment Analyzer** (`core/sentiment_analyzer.py`): Classifies article tone (positive/negative/neutral)
- **Relevance Classifier** (`services/relevance_classifier.py`): Tiers articles by crypto market relevance

### Analysis Layer
- **Narrative Service** (`services/narrative_service.py`): Groups articles into story threads using semantic similarity
- **Signal Service** (`services/signal_service.py`): Detects market events, trends, anomalies
- **Pattern Detector** (`services/pattern_detector.py`): Identifies correlations and divergences

### Generation & Persistence Layer
- **Briefing Agent** (`services/briefing_agent.py`): Orchestrates briefing generation using Claude API
- **Cost Tracker** (`services/cost_tracker.py`): Logs LLM token usage for billing
- **MongoDB Operations** (`db/operations/`): CRUD operations for briefings, narratives, articles

### Frontend Layer
- **React UI** (`context-owl-ui/`): Displays briefings, narratives, signals, articles
- **API Routes** (`api/v1/endpoints/`): FastAPI endpoints for UI consumption

## Data Flow Patterns

### 1. Article Ingestion → Storage
```
RSS Feed → Normalize → Fingerprint Check → Enrich (Entity/Sentiment) → MongoDB Articles
```
Time: 5-30 seconds per article
Frequency: Every 3 hours
Storage: ~100-500 articles/day

### 2. Narrative Detection → Clustering
```
New Articles → Entity Extraction → Similarity Matching → Cluster into Narratives → MongoDB
```
Time: 2-5 seconds per article
Triggers: On each new article
Storage: 50-200 narratives active

### 3. Signal Detection → Briefing
```
Recent Signals (20) + Narratives (15) + Patterns (8) + Memory → LLM → Briefing JSON → MongoDB
```
Time: 30-60 seconds per briefing
Frequency: 3x daily (8 AM, 2 PM, 8 PM EST)
Storage: ~50 KB per briefing

### 4. Frontend Retrieval
```
React App → FastAPI /api/v1/briefings → MongoDB Query → JSON Response → UI Render
```
Time: <500ms
Access: Public (no auth for briefings), Admin for manual triggers

## Architectural Decisions

### 1. Distributed Task Processing (Celery)
**Decision:** Use Celery workers for async article processing
- **Rationale:** Decouples ingestion from enrichment; enables horizontal scaling
- **Trade-off:** Requires Redis broker and monitoring; adds complexity
- **Alternative:** Direct processing in FastAPI (simpler but blocks requests)

### 2. LLM-Centric Briefing
**Decision:** Use Claude API for generation + self-refine loop
- **Rationale:** High-quality narratives; handles ambiguity better than templates
- **Trade-off:** Higher cost (~$0.05/briefing), 30-60s latency
- **Alternative:** Template-based (faster, cheaper, lower quality)

### 3. MongoDB for Scalability
**Decision:** NoSQL document store instead of PostgreSQL
- **Rationale:** Flexible schema for narratives/signals; horizontal sharding support
- **Trade-off:** No ACID guarantees; requires index management
- **Alternative:** PostgreSQL (simpler, ACID, less flexible schema)

### 4. Semantic Similarity for Narrative Detection
**Decision:** Use embedding-based clustering instead of keyword matching
- **Rationale:** Detects related topics without keyword tuning
- **Trade-off:** Slower (5s/article), requires embedding model
- **Alternative:** Keyword/regex matching (faster, requires manual updates)

### 5. Cost Tracking for LLM
**Decision:** Log all LLM token usage for transparency
- **Rationale:** Enables optimization; supports billing chargeback
- **Trade-off:** Adds logging overhead (<1% latency impact)
- **Alternative:** Manual cost estimation (inaccurate)

## Key Performance Characteristics

| Component | Latency | Throughput | Reliability |
|-----------|---------|-----------|-------------|
| RSS Fetch | 30-60s | 100-500 articles/run | 99.5% (no rate limit) |
| Entity Extraction | 2-5s/article | 200-400 articles/hour | 95% (API retries) |
| Narrative Detection | 5-10s/article | 100-200 articles/hour | 97% (similarity failures) |
| Briefing Generation | 30-60s | 3 briefings/day | 99% (LLM fallback models) |
| Frontend API | <500ms | 1000 req/sec | 99.9% (MongoDB load) |

## Scaling Characteristics

- **Articles:** Horizontal (add RSS fetchers, workers)
- **Narratives:** Vertical (requires embedding model memory) + MongoDB sharding
- **Briefings:** Vertical (LLM token limits ~1000s req/min per key)
- **UI:** Horizontal (CDN, load balancer)

## Deployment Architecture

```
┌─────────────────────┐
│   FastAPI (8000)    │  Public API + Admin
├─────────────────────┤
│  Celery Workers (4) │  Async task processing
├─────────────────────┤
│  Celery Beat        │  Scheduler (1 instance)
├─────────────────────┤
│  MongoDB Atlas      │  Cloud-hosted persistence
├─────────────────────┤
│  Redis (broker)     │  Task queue
├─────────────────────┤
│  React App (3000)   │  Frontend UI
└─────────────────────┘
```

## Relevant Module Documentation

- **[20-scheduling.md](#scheduling-task-dispatch)** - Celery Beat configuration for daily briefings
- **[30-ingestion.md](#ingestion-pipeline)** - Article fetching, parsing, deduplication
- **[40-processing.md](#processing-pipeline)** - Entity extraction, sentiment, narrative detection
- **[50-data-model.md](#data-model-mongodb)** - MongoDB collections and schemas
- **[60-llm.md](#llm-integration-generation)** - Claude API integration and briefing generation
- **[70-frontend.md](#frontend-architecture)** - React UI routing and state management

## Related Documentation
- **Debugging Guide** - Operational troubleshooting for each module
- **Test Plan** - Integration tests for data flow verification
- **Cost Optimization** - LLM token reduction strategies

---
*Last updated: 2026-02-10* | *Anchor: architecture-overview*
