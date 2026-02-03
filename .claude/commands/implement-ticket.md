## Automated Workflow Protocols

### Starting a Ticket: "Start working on TICKET-XXX"

1. Read ticket: `/Users/mc/Documents/claude-vault/projects/app-backdrop/development/backlog/TICKET-XXX.md`
2. Update `docs/current-sprint.md` (move to "In Progress")
3. Suggest branch: `feature/ticket-xxx-descriptive-name`
4. Summarize acceptance criteria and confirm

### During Work

1. Update `docs/current-sprint.md` with progress
2. Ask about ADRs for:
   - Tech/framework choices
   - Database architecture changes
   - LLM model selections
   - System architecture patterns
   - Security implementations
   - Performance strategies with trade-offs
3. Remind about tests when new functionality added
4. Suggest commit messages following format above

### Completing a Ticket: "This ticket is done"

1. Verify acceptance criteria met
2. Confirm tests pass
3. Update `docs/current-sprint.md` (move to "Completed")
4. Remind user to finalize ticket (move file, add completion summary)

### End of Day: "Wrap up"

1. Summarize work completed (tickets, files, tests)
2. Update `docs/current-sprint.md`
3. Generate daily wrap: `/Users/mc/Documents/claude-vault/daily-wraps/YYYY-MM/YYYY-MM-DD.md`
   ```markdown
   ---
   date: YYYY-MM-DD
   sprint: sprint-XXX
   session_hours: X.X
   ---

   # Daily Wrap - [Date]

   ## Tickets Worked On
   - [TICKET-ID] Title - Status

   ## Key Decisions Made
   - **Decision:** Brief description
     - **Rationale:** Why

   ## Blockers & Questions
   - [ ] Open items

   ## Tomorrow's Focus
   1. [TICKET-ID] - Continue/start

   ## Metrics
   - LLM cost today: $X.XX
   - Tests: X passing / X total
   ```
4. Remind user of next steps (commit, push, etc.)