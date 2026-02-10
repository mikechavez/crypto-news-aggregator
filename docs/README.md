# Backdrop Documentation Guide

Welcome to the Backdrop (Context Owl) documentation. This guide helps you find the right documentation for your task.

## Which Doc to Trust? 📚

**Trust hierarchy (in order of authority):**

1. **`_generated/system/`** — **Current truth** (code-derived, regenerable)
   - Authoritative system architecture and implementation
   - Automatically generated from codebase via evidence pack
   - Regenerate when code changes: `scripts/generate-evidence.sh`
   - Use for: Production debugging, understanding how things work now

2. **`_generated/context/`** — **Why & history** (curated, linked to system docs)
   - Explains design decisions and historical context
   - Every entry links to a system doc anchor
   - Prevents orphaned "trivia" without current system references
   - Use for: Understanding why decisions were made

3. **`decisions/`** — **Historical reference** (immutable, dated)
   - Legacy docs from earlier development phases
   - Preserved for historical context, not current reference
   - All files marked with archive date (e.g., `-2026-02.md`)
   - Use for: Understanding what was tried, historical timeline

4. **When in doubt** → Code > System Docs > Context Docs > Decisions

---

## Quick Navigation 🧭

### Start Here
- **[QUICKSTART.md](./QUICKSTART.md)** — At-a-glance development cheat sheet
- **[WORKFLOW.md](./WORKFLOW.md)** — Comprehensive workflow guide
- **[current-sprint.md](./current-sprint.md)** — Active sprint status

### System Documentation (Current Truth)
Start with the overview, then dive into specific modules:

- **[_generated/system/00-overview.md](_generated/system/00-overview.md)** — Architecture overview & data flow
- **[_generated/system/10-entrypoints.md](_generated/system/10-entrypoints.md)** — Web API, Celery, CLI entry points
- **[_generated/system/20-scheduling.md](_generated/system/20-scheduling.md)** — Celery Beat scheduler & task dispatch
- **[_generated/system/30-ingestion.md](_generated/system/30-ingestion.md)** — RSS fetching & article ingestion
- **[_generated/system/40-processing.md](_generated/system/40-processing.md)** — Entity extraction & narrative clustering
- **[_generated/system/50-data-model.md](_generated/system/50-data-model.md)** — MongoDB schema & data flow
- **[_generated/system/60-llm.md](_generated/system/60-llm.md)** — Claude API integration & briefing generation
- **[_generated/system/70-frontend.md](_generated/system/70-frontend.md)** — React UI, routing, API integration

**For production debugging:**
- Briefings not running? → See `20-scheduling.md` + `50-data-model.md`
- LLM errors? → See `60-llm.md`
- Data missing? → See `50-data-model.md`

### Context & Decision Docs
- **[_generated/context/](\_generated/context/)** — Why decisions were made (with system doc links)
- **[decisions/](./decisions/)** — Archived legacy docs from earlier phases

### Development Guides
- **[SIGNALS_CACHING.md](./SIGNALS_CACHING.md)** — Signal caching strategy
- **[NARRATIVE_FINGERPRINT.md](./NARRATIVE_FINGERPRINT.md)** — Narrative deduplication
- **[ENTITY_NORMALIZATION.md](./ENTITY_NORMALIZATION.md)** — Entity name standardization

---

## Regenerating System Docs 🔄

System documentation is **code-derived and regenerable**. When the codebase changes:

```bash
# 1. Generate evidence pack (grep output of important code patterns)
./scripts/generate-evidence.sh

# 2. Use Claude Code to regenerate system docs from evidence
# (See _generated/README.md for detailed instructions)

# 3. Update context docs manually if behavior changed (optional)

# 4. Validate structure and consistency
./scripts/validate-docs.sh
```

**Important:** Never edit system docs by hand. Regenerate instead.

See **[_generated/README.md](_generated/README.md)** for detailed regeneration procedures.

---

## Document Structure 📁

```
docs/
├── README.md                    ← You are here
├── QUICKSTART.md               ← Development cheat sheet
├── WORKFLOW.md                 ← Full workflow guide
├── current-sprint.md           ← Sprint status
├── session-start.md            ← Session notes
│
├── _generated/                 ← Code-derived docs (regenerable)
│   ├── system/                 ← Current truth (8 modules)
│   │   ├── 00-overview.md
│   │   ├── 10-entrypoints.md
│   │   ├── 20-scheduling.md
│   │   ├── 30-ingestion.md
│   │   ├── 40-processing.md
│   │   ├── 50-data-model.md
│   │   ├── 60-llm.md
│   │   ├── 70-frontend.md
│   │   └── README.md           ← Regeneration guide
│   ├── context/                ← Why & history (with system links)
│   ├── evidence/               ← Code grep output (raw data)
│   └── ...
│
├── decisions/                  ← Archived legacy docs (dated)
│   ├── background-workers-2026-02.md
│   ├── news-fetching-architecture-2026-02.md
│   └── ... (200+ legacy docs)
│
├── tickets/                    ← Feature/bug ticket tracking
├── sprints/                    ← Sprint planning & completion
└── ...
```

---

## For New Team Members 👋

1. **Read [QUICKSTART.md](./QUICKSTART.md)** (5 min) — Get oriented
2. **Skim [_generated/system/00-overview.md](_generated/system/00-overview.md)** (10 min) — Understand architecture
3. **Dive into specific modules** as needed for your task
4. **Check [_generated/context/](\_generated/context/)** if you need to understand *why* something works

---

## FAQ ❓

**Q: I found a contradiction between two docs. Which is right?**
A: Trust the system doc over context docs. System docs are code-derived and automatically regenerated. If you find a stale system doc, file an issue—it should be regenerated.

**Q: Should I edit system docs directly?**
A: No. They're regenerated from code. Instead:
1. Fix the code
2. Run `scripts/generate-evidence.sh`
3. Regenerate the system doc (see _generated/README.md)

**Q: Why are there 200+ docs in `decisions/`?**
A: Those are session notes and implementation logs from development. They're archived for historical reference but not active documentation. Start with system docs.

**Q: How do I report a doc issue?**
A: System docs out of date? Run regeneration. Context docs unclear? Edit directly. Decisions docs have errors? Leave them as-is (immutable history).

---

**Last updated:** 2026-02-10 | **Sprint:** 9
