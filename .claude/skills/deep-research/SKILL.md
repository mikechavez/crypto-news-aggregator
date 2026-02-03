---
name: deep-research
description: Research strategies and Context Owl architecture reference for deep codebase investigation
user-invocable: false
---

## Documentation Resources

Always check these before exploring code:

- `/Users/mc/dev-projects/crypto-news-aggregator/docs/codebase-exploration/backend-service-patterns.md` - Service layer, LLM integration, data flows
- `/Users/mc/dev-projects/crypto-news-aggregator/docs/architecture/technical_overview.md` - Project structure, tech stack, system architecture
- `/Users/mc/dev-projects/crypto-news-aggregator/docs/codebase-exploration/frontend-architecture.md` - React patterns and components
- `/Users/mc/dev-projects/crypto-news-aggregator/CLAUDE.md` in project root - Development standards and workflow

## Research Workflow

**Phase 1: Documentation First**
Check relevant docs before code exploration. Most patterns are documented.

**Phase 2: Pattern Discovery**
```bash
# Find services
find src/crypto_news_aggregator/services -name "*.py"

# Find specific patterns
grep -r "async def" src/crypto_news_aggregator/services/

# Find LLM usage
grep -r "claude-3-5-haiku\|claude-3-5-sonnet" src/
```

**Phase 3: Deep Analysis**
Read key files and trace data flows through the system.

**Phase 4: Synthesis**
Connect findings with documented patterns. Note discrepancies.

## Context Owl Quick Reference

### Service Pattern
Async-first, single responsibility, DB ops in `db/operations/`, dependency injection

### LLM Strategy
- Haiku ($0.80/$4): extraction, batch
- Sonnet ($3/$15): summaries, reasoning
- Caching: SHA256(prompt+model), 1 week TTL

### Data Flow
RSS → Articles → Entity Extraction → Signals → Narratives → API → UI

### Key Locations
**Services:** `src/crypto_news_aggregator/services/`
**LLM:** `src/crypto_news_aggregator/llm/`
**DB Ops:** `src/crypto_news_aggregator/db/operations/`
**API:** `src/crypto_news_aggregator/api/v1/endpoints/`
**Frontend:** `context-owl-ui/src/`

## Investigation Patterns

**For features:**
Check `backend-service-patterns.md` → Find service → Find DB ops → Find API

**For LLM:**
Check docs → Find in `llm/` → Check caching → Find service usage

**For frontend:**
Check `frontend-architecture.md` → Find page → Find API client

## Search Strategies

```bash
# Find definitions
grep -r "class SignalService" src/

# Find usages
grep -r "SignalService(" src/

# Trace imports
grep -r "from.*signal_service" src/

# Find DB operations
grep -r "db\\.articles\|db\\.narratives" src/
```

## Evidence Guidelines

- Cite files with line numbers: `src/services/sentiment.py:45`
- Quote signatures: `async def process_narrative(db, narrative_id)`
- Reference docs: "Per backend-service-patterns.md..."
- Compare: Documented approach vs actual implementation