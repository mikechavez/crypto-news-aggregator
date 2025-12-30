# Claude Code Instructions - Backdrop

**Backdrop** is a crypto news intelligence platform that aggregates news from 15+ RSS feeds, extracts entities using AI, detects emerging narratives, and tracks trending signals in the crypto space.

---

## Project Overview

### Architecture
- **Backend**: FastAPI (Python 3.11+) on Railway
- **Frontend**: React 19 + TypeScript + Vite on Vercel
- **Database**: MongoDB Atlas (primary), PostgreSQL (legacy)
- **Cache/Queue**: Redis + Celery
- **AI**: Anthropic Claude (Haiku for extraction, Sonnet for summaries)

### Tech Stack

**Backend:**
- FastAPI 0.115+, Python 3.11+
- MongoDB with Motor 3.5 async driver
- Celery 5.5+ for background tasks
- Anthropic Claude 3.5 (Haiku/Sonnet)
- Pydantic 2.11+ for validation

**Frontend:**
- React 19.1.1, TypeScript 5.9.3
- Vite 7.1.7, TanStack React Query 5.90
- Tailwind CSS 4.1, Framer Motion 12.23
- React Router 7.9.3

### Repository Structure
```
crypto-news-aggregator/
├── src/crypto_news_aggregator/     # Backend (Python/FastAPI)
│   ├── api/v1/endpoints/           # REST API endpoints
│   ├── services/                   # Business logic layer
│   ├── llm/                        # LLM integration (Claude)
│   ├── db/operations/              # Database operations
│   ├── background/                 # Background workers
│   ├── tasks/                      # Celery tasks
│   └── core/                       # Config, auth, monitoring
├── context-owl-ui/                 # Frontend (React/TypeScript)
│   ├── src/pages/                  # Page components
│   ├── src/components/             # Reusable UI components
│   ├── src/api/                    # API client layer
│   ├── src/types/                  # TypeScript definitions
│   └── src/contexts/               # React contexts
├── tests/                          # Test suite
├── scripts/                        # Utility scripts
└── alembic/                        # DB migrations (legacy)
```

---

## Development Workflow

### Starting the App

**Backend (FastAPI):**
```bash
cd /Users/mc/dev-projects/crypto-news-aggregator
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend (React/Vite):**
```bash
cd /Users/mc/dev-projects/crypto-news-aggregator/context-owl-ui
npm run dev
```

**Celery Worker (optional):**
```bash
cd /Users/mc/dev-projects/crypto-news-aggregator
celery -A src.crypto_news_aggregator.tasks.celery_config worker --loglevel=info
```

### Branch Strategy

**MANDATORY: ALL changes require feature branches - NO exceptions**

- **NEVER work directly on main branch**
- **ALL code changes must go through feature branches and PR process**
- Main branch is protected - direct commits are FORBIDDEN

Branch naming convention:
- `feature/` - New features or endpoints
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `chore/` - Tooling, dependencies, refactors

Examples:
- `feature/briefing-page`
- `fix/narrative-timeline-bug`
- `docs/update-api-schemas`

### Pre-Deployment Checklist

**MANDATORY before any deployment:**
1. Run full test suite locally
2. Test local server startup and verify API endpoints respond
3. Check for import errors and dependency issues
4. Verify all tests pass
5. Monitor Railway logs immediately after deployment
6. Be prepared to rollback if deployment fails

---

## Commit Messages

**DO NOT include any of the following in commit messages:**
- "Generated with Claude Code" or similar attribution
- "Co-Authored-By: Claude" or any AI co-author lines
- Any mention of AI, LLM, or Claude assistance
- Emoji decorations (🤖, etc.)

**DO follow this format:**
```
type(scope): short description

- Bullet point details
- More details if needed

Fixes: TICKET-XXX (if applicable)
```

**Types:**
- `feat` - New feature
- `fix` - Bug fix
- `refactor` - Code refactoring
- `docs` - Documentation
- `test` - Tests
- `chore` - Build, dependencies, tooling
- `perf` - Performance improvements

**Examples:**
```
feat(api): add briefing generation endpoint

- Create /api/v1/briefing endpoint
- Add morning/evening briefing types
- Integrate with narrative service

fix(ui): correct timeline date parsing

- Add fallback for missing last_article_at field
- Use first_seen as backup timestamp
```

---

## Code Standards

### Backend (Python)

**Service Layer Pattern:**
- Async-first design (async/await)
- Single responsibility per service
- Database operations abstracted in `db/operations/`
- Dependency injection (DB client, config)
- Error handling with Loguru logging

**Example Service:**
```python
from loguru import logger
from motor.motor_asyncio import AsyncIOMotorDatabase

class MyService:
    def __init__(self, db: AsyncIOMotorDatabase, config):
        self.db = db
        self.config = config
        self.logger = logger

    async def process_data(self, data_id: str):
        """Process data and store results."""
        try:
            result = await self._compute(data_id)
            await self.db.my_collection.insert_one(result)
            self.logger.info(f"Processed {data_id}")
            return result
        except Exception as e:
            self.logger.error(f"Error processing {data_id}: {e}")
            raise
```

**LLM Integration:**
- Use Claude 3.5 Haiku for extraction/batch processing
- Use Claude 3.5 Sonnet for summaries/reasoning
- Always implement caching for identical prompts
- Track costs with `llm/tracking.py`
- Implement fallback chain for model failures

### Frontend (React/TypeScript)

**Component Patterns:**
- Functional components with hooks
- TanStack React Query for data fetching
- Error boundaries with retry functionality
- Loading states for all async operations
- Dark mode support throughout

**Page Component Template:**
```typescript
import { useQuery } from '@tanstack/react-query';
import { myAPI } from '../api';
import { Card, CardHeader, CardTitle, CardContent } from '../components/Card';
import { Loading } from '../components/Loading';
import { ErrorMessage } from '../components/ErrorMessage';

export function MyPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['myData'],
    queryFn: () => myAPI.getData(),
    refetchInterval: 60000,
  });

  if (isLoading) return <Loading />;
  if (error) return <ErrorMessage error={error} />;

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Page Title</h1>
      <Card>
        <CardHeader>
          <CardTitle>Section Title</CardTitle>
        </CardHeader>
        <CardContent>
          {/* Content */}
        </CardContent>
      </Card>
    </div>
  );
}
```

**Routing:**
- Add routes in `src/App.tsx`
- Add navigation items in `src/components/Layout.tsx`
- Use React Router v7 declarative routing

**API Client:**
- All API calls through centralized client in `src/api/`
- Environment variables: `VITE_API_URL`, `VITE_API_KEY`
- Type-safe with TypeScript interfaces

---

## Testing Requirements

### Backend Tests
- Write smoke tests for any new endpoints
- Test database operations in isolation
- Verify external API integrations
- Mock LLM calls to avoid costs
- Run tests: `pytest tests/`

### Frontend Tests
- Test component rendering
- Test API integration
- Test error states
- Run tests: `npm test`

### Pre-Commit
- All imports must resolve
- No linting errors
- Format with Prettier/Black

---

## Key Collections (MongoDB)

**articles**
- title, text, url, source, published_at
- sentiment_score, keywords, entities
- Primary data source from RSS feeds

**entity_mentions**
- entity (normalized), entity_type, article_id
- confidence (>80%), is_primary
- Extracted via Claude Haiku

**narratives**
- theme, title, summary, entities
- lifecycle_state (emerging → hot → cooling → dormant)
- timeline_data (daily snapshots for visualization)
- Generated via salience clustering + LLM

**signal_scores**
- entity, mentions, velocity, source_count
- sentiment_score, signal_score (composite)
- Calculated every 5 minutes

**cost_tracking**
- model, operation, input/output tokens
- input/output costs, cached flag
- Tracks all LLM API usage

---

## Data Flow Pipeline

```
RSS Feeds (15+ sources)
  ↓ (every 30 minutes)
RSS Fetcher Service
  ↓
Articles Collection
  ↓
Entity Extraction (Claude Haiku - batch of 10)
  ↓
Entity Mentions Collection
  ↓
Signal Scoring (every 5 min) → Signal Scores
  ↓
Narrative Detection (every 10 min) → Narratives
  ↓
REST API Endpoints
  ↓
Frontend UI (React)
```

---

## Critical File Paths

**Backend Services:**
- `src/crypto_news_aggregator/services/signal_service.py`
- `src/crypto_news_aggregator/services/narrative_service.py`
- `src/crypto_news_aggregator/services/narrative_themes.py`
- `src/crypto_news_aggregator/services/entity_normalization.py`

**LLM Integration:**
- `src/crypto_news_aggregator/llm/anthropic.py`
- `src/crypto_news_aggregator/llm/optimized_anthropic.py`
- `src/crypto_news_aggregator/llm/cache.py`
- `src/crypto_news_aggregator/llm/tracking.py`

**API Endpoints:**
- `src/crypto_news_aggregator/api/v1/endpoints/signals.py`
- `src/crypto_news_aggregator/api/v1/endpoints/narratives.py`
- `src/crypto_news_aggregator/api/v1/endpoints/articles.py`

**Frontend Pages:**
- `context-owl-ui/src/pages/Signals.tsx` - Trending entities
- `context-owl-ui/src/pages/Narratives.tsx` - Narrative clusters
- `context-owl-ui/src/pages/Articles.tsx` - Article feed
- `context-owl-ui/src/pages/CostMonitor.tsx` - LLM cost dashboard

**Frontend API Layer:**
- `context-owl-ui/src/api/client.ts` - Base API client
- `context-owl-ui/src/api/signals.ts` - Signals API
- `context-owl-ui/src/api/narratives.ts` - Narratives API

---

## Architecture Patterns

### Backend
1. **Service-Database Separation** - Services call db/operations, not direct queries
2. **Async-First Design** - All IO operations use async/await
3. **Dependency Injection** - Services receive DB client and config
4. **Multi-Layer Caching** - LLM cache → API cache → DB indexes
5. **Cost Optimization** - Haiku for extraction, Sonnet for summaries, caching everywhere

### Frontend
1. **Component Composition** - Card, CardHeader, CardTitle, CardContent
2. **Query-Based State** - TanStack React Query (no Redux)
3. **Centralized Types** - All TypeScript types in `types/index.ts`
4. **Safe Date Parsing** - Fallbacks for missing/invalid timestamps
5. **Dark Mode Support** - ThemeContext with localStorage persistence

---

## Security & Best Practices

### Backend
- Never commit `.env` files
- Use environment variables for secrets
- Validate all inputs with Pydantic
- Rate limit API endpoints
- Log errors with Loguru

### Frontend
- Sanitize user inputs
- Use API key headers (`X-API-Key`)
- Handle errors gracefully with retry
- No sensitive data in localStorage
- CORS configured for Vercel domain

---

## Pull Requests

- Same rules as commits - no AI attribution in PR descriptions
- Include test results and screenshots for UI changes
- Link to related issues or tickets
- Describe what was changed and why
- List any breaking changes or migration steps

---

## Project Management Workflow

### Documentation Locations

**In Repo (for development context):**
- `docs/WORKFLOW.md` - Complete development workflow guide (read this for details)
- `docs/current-sprint.md` - Active sprint status (update frequently during work)
- `docs/architecture/` - Technical architecture documentation
- `docs/decisions/` - Architectural Decision Records (ADRs)
- `docs/ticket-templates/` - Templates for creating tickets

**External (for planning and history):**
- `/Users/mc/Documents/claude-vault/projects/app-backdrop/development/` - All tickets
  - `backlog/` - Unstarted tickets
  - `in-progress/` - Active work
  - `done/` - Completed tickets
  - `sprints/` - Sprint retrospectives
  - `SPRINTS.md` - Sprint planning dashboard
- `/Users/mc/Documents/claude-vault/projects/app-backdrop/planning/` - Strategic docs
  - `vision.md` - Product vision and roadmap
  - `roadmap.md` - Multi-quarter planning
- `/Users/mc/Documents/claude-vault/projects/app-backdrop/context/` - System overviews
- `/Users/mc/Documents/claude-vault/daily-wraps/` - Session journals

### Current Sprint Reference

Always check `docs/current-sprint.md` at the start of each session to understand:
- Current sprint goal
- Tickets in progress
- Next priorities
- Any blockers

---

## Automated Workflow Protocols

These are the automation behaviors you should follow during development sessions.

### When User Says: "Start working on TICKET-XXX"

**Your actions:**

1. **Read ticket details**
   - Location: `/Users/mc/Documents/claude-vault/projects/app-backdrop/development/backlog/TICKET-XXX.md`
   - Parse frontmatter and full ticket content

2. **Update current-sprint.md**
   - Move ticket from "Backlog" to "In Progress" section
   - Add started date

3. **Suggest feature branch**
   - Format: `feature/ticket-xxx-short-descriptive-name`
   - Example: `feature/briefing-generation` for FEATURE-003

4. **Summarize and confirm**
   ```
   Starting work on FEATURE-003: Briefing prompt engineering

   Acceptance Criteria:
   - No hallucinated content
   - No generic filler language
   - All narratives covered

   Suggested branch: feature/briefing-prompt-engineering

   Ready to proceed?
   ```

**User will then:**
- Create the feature branch
- Manually move ticket file from `backlog/` to `in-progress/`
- Update ticket frontmatter status

### During Active Work

**Your actions (automatic):**

1. **Update docs/current-sprint.md**
   - Add progress notes to the ticket's "In Progress" section
   - Note any blockers discovered
   - Keep sprint doc in sync with work state

2. **Document architectural decisions**

   **When to ask about creating an ADR:**
   - Technology/framework choices (e.g., choosing Redis over Memcached)
   - Database architecture changes (e.g., MongoDB migration, indexing strategy)
   - LLM model selections (e.g., Sonnet vs Haiku for specific tasks)
   - System architecture patterns (e.g., caching strategy, queue design)
   - Security implementations (e.g., auth method, encryption approach)
   - Performance optimization strategies with trade-offs
   - API design approaches that set precedent

   **When NOT to create an ADR:**
   - Small implementation details (e.g., variable names)
   - Obvious choices with no alternatives
   - Temporary workarounds or patches
   - Code style preferences (those go in coding-standards/)

   **If a significant decision is made, ask:**
   ```
   This looks like an architectural decision: [brief description]
   Should I create an ADR in docs/decisions/?
   ```

   **If user confirms:**
   - Find next sequential ADR number (check docs/decisions/)
   - Create `docs/decisions/NNN-decision-name.md` using template
   - Fill in:
     - Context (what problem prompted this)
     - Decision (what was chosen)
     - Alternatives considered (what else was evaluated)
     - Consequences (positive, negative, neutral)
     - Validation metrics
   - Add to `docs/decisions/README.md` index
   - Include ADR creation in same commit as the code change

3. **Remind about tests**
   - When new functionality is added, remind user:
     ```
     New functionality added. Remember to write tests before marking complete.
     ```

4. **Keep commits focused**
   - When ready to commit, suggest commit message following the format in this file
   - Include code changes and `docs/current-sprint.md` updates in same commit
   - DO NOT mention "update sprint status" in commit messages

### When User Says: "This ticket is done"

**Your actions:**

1. **Verify completion**
   - Check acceptance criteria from ticket
   - Confirm tests are written and passing
   - Verify documentation updated if needed

2. **Update current-sprint.md**
   - Move ticket from "In Progress" to "Completed This Sprint"
   - Add completion date

3. **Remind user to finalize ticket**
   ```
   ✅ Ticket appears complete!

   Please finalize:
   1. Move ticket file: in-progress/ → done/
   2. Fill in "Completion Summary" section:
      - Actual complexity vs estimated
      - Key decisions made
      - Any deviations from plan

   Ready to start next ticket?
   ```

4. **Suggest next work**
   - Show remaining tickets from current sprint backlog
   - Highlight highest priority

### When User Says: "Wrap up" or "End of day"

**Your actions (automatic):**

1. **Summarize work completed**
   ```
   Session Summary:

   Tickets worked on:
   - [FEATURE-003] Briefing prompt engineering - In Progress
     - Added anti-hallucination prompts
     - Tested with Sonnet
     - Still need to verify edge cases

   Files changed:
   - src/crypto_news_aggregator/services/briefing_agent.py
   - docs/current-sprint.md

   Tests:
   - 12 passing, 0 failing
   ```

2. **Update docs/current-sprint.md**
   - Ensure all progress from session is captured
   - Note any blockers or open questions

3. **Generate daily wrap**
   - Create file: `/Users/mc/Documents/claude-vault/daily-wraps/YYYY-MM/YYYY-MM-DD.md`
   - Use simplified template:
     ```markdown
     ---
     date: YYYY-MM-DD
     sprint: sprint-XXX
     session_hours: X.X
     ---

     # Daily Wrap - [Date]

     ## Tickets Worked On
     - [TICKET-ID] Title - Status (in-progress/done)

     ## Key Decisions Made
     - **Decision:** Brief description
       - **Rationale:** Why

     ## Blockers & Questions
     - [ ] Open question or blocker

     ## Tomorrow's Focus
     1. [TICKET-ID] - Continue/start work

     ## Metrics
     - LLM cost today: $X.XX
     - Tests: X passing / X total
     ```

4. **Remind user of next steps**
   ```
   Session wrap complete!

   Next steps:
   1. Review daily wrap: /Users/mc/Documents/claude-vault/daily-wraps/YYYY-MM/YYYY-MM-DD.md
   2. Commit changes: git add . && git commit -m "..."
   3. Update ticket files in external location if needed
   4. Push branch if ready for PR

   See you next session! 👋
   ```

### When User Says: "Let's start a new sprint"

**Your actions:**

1. **Gather current sprint info**
   - Read `docs/current-sprint.md`
   - Extract current sprint number
   - Count completed tickets for velocity

2. **Show transition prompt**
   ```
   Ready to transition from Sprint X to Sprint Y?

   Sprint X Summary:
   - Completed: N tickets
   - Deferred: M tickets
   - Velocity: N tickets in X days

   I'll run the sprint transition script which will:
   1. Archive Sprint X to external sprints/ folder
   2. Open retrospective template for you to fill
   3. Create fresh Sprint Y in docs/current-sprint.md
   4. Commit the changes

   Run ./scripts/new-sprint.sh? (You'll see confirmation prompts)
   ```

3. **If user confirms, run script**
   ```bash
   ./scripts/new-sprint.sh
   ```
   - Script handles all interactive prompts
   - User fills in retrospective
   - User provides new sprint details

4. **After script completes**
   ```
   Sprint Y created!

   Next steps:
   1. Edit docs/current-sprint.md to add:
      - Sprint goal
      - Tickets from backlog
   2. Update external SPRINTS.md with Sprint Y details

   Ready to start planning Sprint Y?
   ```

### When User Asks About Strategic Context

**If user mentions vision, roadmap, or long-term planning:**

1. **Read external planning docs**
   - `/Users/mc/Documents/claude-vault/projects/app-backdrop/planning/vision.md`
   - `/Users/mc/Documents/claude-vault/projects/app-backdrop/planning/roadmap.md`

2. **Reference in context**
   - Use vision/roadmap to inform technical decisions
   - Align current work with broader product goals
   - Suggest features that fit the strategic direction

**Example:**
```
Based on the vision doc, we're in Phase 2 (Intelligence Layer).
This briefing work aligns with "Daily Intelligence Briefing" feature.
Should we also consider the Q&A capability mentioned in the roadmap?
```

---

## Conflict Resolution

- Development Practices (this file) take priority over other standards
- If multiple standards apply, satisfy ALL applicable rules
- Default to: Safety over speed, Clarity over shortcuts, Maintainability over hacks

---

**Remember:** Always create feature branches, test locally before deploying, and follow the commit message format. Main branch is protected!
