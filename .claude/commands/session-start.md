## Session Management Commands

### /session-start
**Purpose**: Initialize work session and identify next task

**Process**:
1. Read `docs/SESSION_START.md`
2. Parse the "What to Work On Next" section
3. Identify Priority 1 task
4. Check for blockers


**Response Format**:
```
🚀 Session Started

**Current Sprint**: [Sprint number and goal]
**Your Next Task**: [TICKET-ID] [Ticket title]

📋 Details:
- Status: [status]
- Files: [list of files]
- Dependencies: [dependencies]
- Estimated effort: [effort]
- Blockers: [blockers if any]

📚 Relevant Documentation:
- Pattern: [relevant pattern from CLAUDE.md]
- Architecture: [relevant architecture doc if needed]

✅ Recently Completed:
[List 2-3 most recent completions]

⚠️ Active Blockers:
[List any blockers]

Ready to implement [TICKET-ID]? 
Type 'yes' to start, or ask questions first.
```

**Follow-up Actions**:
- If user confirms, read relevant architecture docs
- Check STANDARDS.md for applicable requirements
- Begin implementation with proper branch creation

