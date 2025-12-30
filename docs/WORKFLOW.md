# Development Workflow

**Last Updated:** 2025-12-30

This document defines the complete development workflow for Backdrop. Update this as processes evolve.

---

## Table of Contents

- [Daily Workflow](#daily-workflow)
- [Sprint Workflow](#sprint-workflow)
- [Ticket Workflow](#ticket-workflow)
- [Documentation Locations](#documentation-locations)
- [Automation Scripts](#automation-scripts)

---

## Daily Workflow

### Starting a Session

**1. Check current work**
```bash
cat docs/current-sprint.md
```

This shows you:
- Current sprint goal
- Tickets in progress
- Next priorities
- Any blockers

**2. Review specific ticket details**
- Location: `/Users/mc/Documents/claude-vault/projects/app-backdrop/development/`
- Read full acceptance criteria
- Review implementation notes from previous sessions

**3. Tell Claude which ticket to work on**
```
"Let's work on FEATURE-003"
```

Claude will:
- Read the ticket details
- Update `current-sprint.md` to mark it in-progress
- Suggest a feature branch name
- Summarize acceptance criteria

**4. Create feature branch**
```bash
git checkout -b feature/ticket-name
```

**5. Move ticket file (manual step)**
```bash
# Move ticket from backlog to in-progress
mv /Users/mc/Documents/claude-vault/projects/app-backdrop/development/backlog/ticket.md \
   /Users/mc/Documents/claude-vault/projects/app-backdrop/development/in-progress/
```

Update ticket frontmatter:
```yaml
status: in-progress
updated: 2025-12-30
```

### During Work

**Claude automatically:**
- Updates `docs/current-sprint.md` with progress
- Documents technical decisions (asks before creating ADRs)
- Reminds about tests when adding functionality

**You:**
- Review code changes
- Approve architectural decisions
- Provide direction when blocked

**If you make an architectural decision:**
- Claude asks: "Should I document this as an ADR in `docs/decisions/`?"
- If yes, Claude creates `docs/decisions/NNN-decision-name.md`

### Completing a Ticket

**1. Verify completion**
- All acceptance criteria met ✅
- Tests written and passing ✅
- Documentation updated ✅

**2. Tell Claude the ticket is done**
```
"This ticket is complete"
```

Claude will:
- Verify acceptance criteria were met
- Remind you to update the ticket file
- Show you what to do next

**3. Update ticket file (manual step)**
```bash
# Move ticket from in-progress to done
mv /Users/mc/Documents/claude-vault/projects/app-backdrop/development/in-progress/ticket.md \
   /Users/mc/Documents/claude-vault/projects/app-backdrop/development/done/
```

Fill in the "Completion Summary" section:
```markdown
## Completion Summary
- Actual complexity: Medium (as estimated)
- Key decisions made: Chose Sonnet over Haiku for accuracy
- Deviations from plan: None
- Deployed to: Railway production
- Verified by: Manual testing of briefing generation
```

**4. Commit and create PR**
```bash
git add .
git commit -m "feat(api): add briefing generation endpoint"
git push origin feature/ticket-name
```

Create PR following guidelines in `claude.md`

### End of Session

**Tell Claude:**
```
"Let's wrap up the session"
```

**Claude will automatically:**

1. **Summarize work done**
   - List tickets worked on with status changes
   - Files modified
   - Tests written/status

2. **Update current-sprint.md**
   - Latest ticket status
   - Note any blockers discovered
   - Update progress

3. **Generate daily wrap**
   - Creates file in `/Users/mc/Documents/claude-vault/daily-wraps/YYYY-MM/`
   - Uses simplified template
   - Includes ticket IDs, decisions, next steps

4. **Remind you to:**
   - Update ticket files in external location (if not done)
   - Push branch if ready for PR
   - Review daily wrap before closing session

**You commit the changes:**
```bash
# Commit code and doc updates together
git add .
git commit -m "feat(api): implement briefing endpoint

- Add POST /api/v1/briefing/generate
- Integrate with narrative service
- Add anti-hallucination prompts"

git push
```

**Note:** No need to mention sprint status updates in commit messages - just describe the code changes.

---

## Sprint Workflow

### Sprint Structure

- **Duration:** Flexible (typically 3-7 days)
- **Velocity:** Track completed tickets per sprint
- **Goal:** Clear objective for the sprint
- **Scope:** 2-5 tickets depending on complexity

### Starting a New Sprint

**Tell Claude:**
```
"Let's start a new sprint"
```

**Claude will:**

1. **Prompt for confirmation:**
   ```
   Ready to transition from Sprint 1 to Sprint 2?

   Sprint 1 Summary:
   - Completed: 3 tickets (FEATURE-002, FEATURE-003, BUG-001)
   - Deferred: 1 ticket (FEATURE-007)
   - Velocity: 3 tickets in 4 days

   I'll:
   1. Archive Sprint 1 to external sprints/ folder
   2. Create retrospective template for you to fill
   3. Create fresh Sprint 2 in docs/current-sprint.md

   Proceed? (yes/no)
   ```

2. **If you confirm, Claude runs the sprint transition:**
   - Copies `docs/current-sprint.md` to external archive
   - Opens archived file for you to add retrospective notes
   - Creates new `docs/current-sprint.md` for Sprint 2
   - Commits the change

3. **You fill in the retrospective:**
   ```markdown
   ## What Went Well
   - Sonnet upgrade resolved hallucination issues
   - Good architectural decisions documented

   ## What Could Improve
   - Need better testing before Railway deploy
   - Underestimated Celery Beat complexity

   ## Action Items for Next Sprint
   - Add Railway deployment checklist
   - Research Celery Beat setup before starting work
   ```

4. **You plan Sprint 2:**
   - Review `/claude-vault/.../development/SPRINTS.md` for priorities
   - Tell Claude which tickets to add to Sprint 2
   - Claude updates `docs/current-sprint.md` with new tickets

**Or use the script directly:**
```bash
./scripts/new-sprint.sh
```

This runs the same interactive process.

### Mid-Sprint Adjustments

**Adding tickets:**
```
"Add FEATURE-008 to current sprint"
```

Claude updates `docs/current-sprint.md`

**Deferring tickets:**
```
"Let's defer FEATURE-007 to next sprint - it's more complex than expected"
```

Claude moves it to "Deferred" section and notes the reason

**Changing sprint goal:**
```
"Let's pivot the sprint goal to focus on performance instead of design"
```

Claude updates the goal and asks if you want to adjust ticket priorities

---

## Ticket Workflow

### Creating a New Ticket

**Option A: Tell Claude**
```
"Create a new feature ticket for adding email notifications"
```

Claude will:
- Use next sequential ID
- Create ticket file from template
- Ask you to fill in key sections
- Save to `/claude-vault/.../development/backlog/`

**Option B: Manual**
```bash
cp docs/ticket-templates/feature.md \
   /Users/mc/Documents/claude-vault/projects/app-backdrop/development/backlog/feature-email-notifications.md
```

Edit and fill in:
- `id: FEATURE-008` (next number)
- `priority: high/medium/low`
- `complexity: high/medium/low`
- Problem/solution
- Acceptance criteria

### Ticket Frontmatter Fields

```yaml
---
id: FEATURE-XXX
type: feature          # feature, bug, chore
status: backlog        # backlog, in-progress, done
priority: medium       # high, medium, low
complexity: medium     # high, medium, low
created: 2025-12-30
updated: 2025-12-30
---
```

### Estimating Complexity

- **Low:** < 2 hours, well-understood, no unknowns
- **Medium:** 2-4 hours, some unknowns, requires research
- **High:** > 4 hours, many unknowns, architectural impact

### Prioritization Framework

1. **Critical bugs** - Blocking user experience or production issues
2. **High-value features** - Aligned with current phase roadmap
3. **Technical debt** - If blocking future work
4. **Nice-to-haves** - Defer to later sprints

### Ticket States

```
backlog/ → in-progress/ → done/
```

**backlog/** - Not yet started, prioritized in SPRINTS.md
**in-progress/** - Actively being worked on
**done/** - Completed, includes completion summary

---

## Documentation Locations

### In Repo (`/dev-projects/crypto-news-aggregator/`)

| File | Purpose | Update Frequency |
|------|---------|------------------|
| `claude.md` | Claude Code instructions | Rarely (as process changes) |
| `docs/WORKFLOW.md` | This file - your workflow reference | As needed |
| `docs/current-sprint.md` | Active sprint status | Multiple times per session |
| `docs/architecture/` | Technical architecture docs | When architecture changes |
| `docs/decisions/` | Architectural Decision Records | Per major decision |
| `docs/ticket-templates/` | Ticket templates | Rarely |
| `CONTRIBUTING.md` | External contributor guide | When process stabilizes |

### External (`/claude-vault/projects/app-backdrop/`)

| Location | Purpose | Update Frequency |
|----------|---------|------------------|
| `development/backlog/` | Unstarted tickets | As new work identified |
| `development/in-progress/` | Active tickets | Daily |
| `development/done/` | Completed tickets | Per ticket completion |
| `development/sprints/` | Sprint retrospectives | End of each sprint |
| `development/SPRINTS.md` | Sprint planning dashboard | Weekly |
| `planning/vision.md` | Product vision | Quarterly |
| `planning/roadmap.md` | Multi-quarter roadmap | Monthly |
| `context/` | System overviews | When architecture changes |

### Daily Wraps

| Location | Purpose |
|----------|---------|
| `/claude-vault/daily-wraps/YYYY-MM/` | Session journals |

---

## Automation Scripts

### Available Now

**`scripts/new-sprint.sh`**
Interactive sprint transition with confirmation prompts.

```bash
./scripts/new-sprint.sh
```

What it does:
- Shows current sprint summary
- Asks for confirmation
- Archives current sprint
- Opens retrospective for you to fill
- Creates new sprint file
- Commits changes

### Future Scripts (To Build)

**`scripts/new-ticket.sh <type> "<title>"`**
Create ticket from template with auto-incremented ID.

**`scripts/ticket-move.sh <id> <status>`**
Move ticket between backlog/in-progress/done folders.

**`scripts/sprint-stats.sh`**
Generate velocity and completion metrics for current/past sprints.

---

## Best Practices

### Commits

✅ **Good:**
```bash
feat(api): add briefing generation endpoint
fix(ui): correct timeline date parsing
refactor(llm): extract cost tracking to separate service
```

❌ **Don't:**
```bash
update sprint status
work on ticket
changes
```

### Branch Names

✅ **Good:**
```bash
feature/briefing-generation
fix/timeline-timezone
refactor/llm-cost-tracking
```

❌ **Don't:**
```bash
feature-003
my-changes
temp-branch
```

### Ticket Acceptance Criteria

✅ **Good:**
```markdown
- [ ] POST /api/v1/briefing endpoint returns 200
- [ ] Response contains morning_briefing and evening_briefing fields
- [ ] Briefing content includes all active narratives
- [ ] No hallucinated content (verified by spot check)
```

❌ **Don't:**
```markdown
- [ ] Make it work
- [ ] Test it
- [ ] Deploy
```

### Sprint Goals

✅ **Good:**
```
Fix critical UX issues and enable automated briefings
Design cohesive experience across briefing, narratives, and signals
```

❌ **Don't:**
```
Work on stuff
Fix bugs and add features
Get things done
```

---

## Troubleshooting

### "I forgot to move a ticket file"

No problem - move it whenever you remember:
```bash
mv /path/to/old/location/ticket.md /path/to/new/location/
```

Update `docs/current-sprint.md` to reflect current reality.

### "Sprint is taking longer than expected"

Totally fine:
- Update sprint duration in `docs/current-sprint.md`
- Defer low-priority tickets to next sprint
- Focus on completing fewer tickets well

### "I want to work on something not in the sprint"

Go for it:
- Add ticket to current sprint
- Update `docs/current-sprint.md`
- Document why the priority shifted in daily wrap

### "Claude updated current-sprint.md incorrectly"

Just edit it manually:
```bash
code docs/current-sprint.md
```

Claude will see the correct state on next read.

---

## Changelog

| Date | Change |
|------|--------|
| 2025-12-30 | Initial workflow documentation created |

---

**Remember:** This workflow should serve you, not constrain you. Update this document as you discover what works best.
