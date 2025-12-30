# Workflow Quick Reference

**Last Updated:** 2025-12-30

One-page cheat sheet for daily development workflow.

---

## 🎯 What To Say to Claude

| What You Want | Say This |
|---------------|----------|
| See current sprint status | `"What's on the sprint?"` |
| Start work on a ticket | `"Let's work on FEATURE-003"` |
| Mark ticket complete | `"This ticket is done"` |
| End session / wrap up | `"Wrap up"` or `"End of day"` |
| Start new sprint | `"Let's start a new sprint"` |
| Check vision/roadmap context | `"What does the vision say about...?"` |

---

## 📂 Key File Locations

### In Repo (Quick Access)
```bash
docs/current-sprint.md          # Current sprint status
docs/WORKFLOW.md                # Full workflow guide
docs/ticket-templates/          # Ticket templates
scripts/new-sprint.sh           # Sprint transition script
```

### External (Full History)
```bash
/Users/mc/Documents/claude-vault/projects/app-backdrop/development/backlog/
/Users/mc/Documents/claude-vault/projects/app-backdrop/development/in-progress/
/Users/mc/Documents/claude-vault/projects/app-backdrop/development/done/
/Users/mc/Documents/claude-vault/projects/app-backdrop/development/SPRINTS.md
/Users/mc/Documents/claude-vault/projects/app-backdrop/planning/vision.md
/Users/mc/Documents/claude-vault/daily-wraps/YYYY-MM/
```

---

## ⚡ Quick Commands

### Check Sprint Status
```bash
cat docs/current-sprint.md
```

### Start New Sprint
```bash
./scripts/new-sprint.sh
```

### Create Ticket (Manual)
```bash
cp docs/ticket-templates/ticket-template-feature.md \
   /Users/mc/Documents/claude-vault/projects/app-backdrop/development/backlog/feature-name.md
# Edit the file, fill in details
```

### Move Ticket Between Stages
```bash
# Starting work
mv /path/to/backlog/ticket.md /path/to/in-progress/

# Completing work
mv /path/to/in-progress/ticket.md /path/to/done/
```

---

## 🔄 Daily Workflow (Summary)

**Morning:**
1. `cat docs/current-sprint.md` - See what's planned
2. Tell Claude: `"Let's work on TICKET-XXX"`
3. Claude updates sprint doc, you create branch
4. Move ticket file: `backlog/` → `in-progress/`

**During Work:**
- Claude auto-updates `docs/current-sprint.md`
- Code + sprint doc committed together
- No "update sprint" in commit messages

**End of Day:**
1. Tell Claude: `"Wrap up"`
2. Claude generates daily wrap
3. Commit: `git add . && git commit -m "..."`
4. Update ticket files if needed

---

## 📋 Ticket Workflow (Summary)

### Creating Tickets
```bash
# Use template
cp docs/ticket-templates/ticket-template-feature.md \
   /claude-vault/.../backlog/feature-description.md

# Fill in:
id: FEATURE-XXX        # Next sequential number
priority: high/medium/low
complexity: high/medium/low
# + problem, solution, acceptance criteria
```

### Ticket States
```
backlog/ → in-progress/ → done/
```

### Finding Next Ticket ID
```bash
# Check highest number in backlog and done folders
ls /claude-vault/.../backlog/ | grep FEATURE
ls /claude-vault/.../done/ | grep FEATURE
# Use next sequential number
```

---

## 🏃 Sprint Workflow (Summary)

### During Sprint
- Work on tickets in priority order
- Update `docs/current-sprint.md` automatically (Claude does this)
- Can add/defer tickets mid-sprint

### End Sprint / Start New Sprint
```bash
./scripts/new-sprint.sh
# Follow prompts:
# 1. Confirms transition
# 2. Archives current sprint
# 3. Opens retro for you to fill
# 4. Creates new sprint
# 5. Commits changes
```

### After Sprint Transition
1. Edit `docs/current-sprint.md` - add goal and tickets
2. Update external `SPRINTS.md` with new sprint

---

## 📐 Architectural Decision Records (ADRs)

### When to Create an ADR

Create ADR for:
- Technology/framework choices
- Database or architecture changes
- LLM model selections
- Security implementations
- Performance strategies

### Quick Creation

**Tell Claude:**
```
"This feels like an architectural decision - should we create an ADR?"
```

Claude will create the ADR file and fill in the template.

**Or manually:**
```bash
cp docs/decisions/template.md docs/decisions/002-decision-name.md
# Edit file, then add to docs/decisions/README.md
```

### See Example
`docs/decisions/001-sonnet-vs-haiku-for-briefing.md`

---

## 📚 Architecture Documentation

### Quick Reference Locations

```bash
docs/architecture/           # API, DB schemas, system overview
docs/codebase-exploration/   # Service patterns, workers, frontend
docs/coding-standards/       # Dev, testing, security, UI standards
```

### When to Check

- **Before new work:** Read `architecture/technical overview.md`
- **API changes:** Check `architecture/api-schemas.md`
- **Database changes:** Check `architecture/database-schemas.md`
- **Writing tests:** Follow `coding-standards/testing-standards.md`
- **Building UI:** Reference `codebase-exploration/frontend-architecture.md`

---

## 🔧 Git Workflow

### Branch Names
```bash
feature/ticket-description
fix/bug-description
docs/doc-description
chore/task-description
```

### Commit Format
```bash
type(scope): short description

- Bullet details
- More details

Fixes: TICKET-XXX
```

**Types:** `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`

### Commit + Push
```bash
git add .
git commit -m "feat(api): add briefing endpoint

- Create POST /api/v1/briefing
- Add morning/evening types"

git push origin feature/branch-name
```

---

## 📊 Complexity Estimates

- **Low:** < 2 hours, well-understood
- **Medium:** 2-4 hours, some unknowns
- **High:** > 4 hours, many unknowns, architectural

---

## 🎯 Priority Levels

1. **Critical bugs** - Blocking production
2. **High-value features** - Current phase alignment
3. **Technical debt** - If blocking future work
4. **Nice-to-haves** - Defer to later

---

## 🚀 Server Commands

### Start Backend
```bash
cd /Users/mc/dev-projects/crypto-news-aggregator
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Start Frontend
```bash
cd /Users/mc/dev-projects/crypto-news-aggregator/context-owl-ui
npm run dev
```

### Start Celery Worker
```bash
cd /Users/mc/dev-projects/crypto-news-aggregator
celery -A src.crypto_news_aggregator.tasks.celery_config worker --loglevel=info
```

### Run Tests
```bash
# Backend
pytest tests/

# Frontend
cd context-owl-ui && npm test
```

---

## 📝 Daily Wrap Location

Auto-generated by Claude at end of session:
```
/Users/mc/Documents/claude-vault/daily-wraps/YYYY-MM/YYYY-MM-DD.md
```

---

## 🆘 Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| Forgot to move ticket file | Move it anytime, update `docs/current-sprint.md` manually |
| Claude updated sprint doc wrong | Edit `docs/current-sprint.md` manually |
| Sprint taking longer | Update duration in `current-sprint.md`, defer low-priority tickets |
| Want to work on non-sprint item | Add ticket to sprint, update `current-sprint.md` |
| Need to reference vision/roadmap | Ask Claude: `"What does the vision say about X?"` |

---

## 📚 Full Details

For comprehensive explanations, see `docs/WORKFLOW.md`
