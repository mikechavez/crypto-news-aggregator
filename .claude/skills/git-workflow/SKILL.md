---
name: git-workflow
description: Project-specific git conventions and commit message standards. Use for branch naming, commit formatting, and PR workflows.
user-invocable: false
---

## Branch Strategy

ALL changes require feature branches - NO direct commits to main.

Branch format: `{type}/{description}`

Types:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation
- `chore/` - Maintenance

## Commit Message Format

```
type(scope): short description

- Bullet point details
- More details if needed
```

**Types:** feat, fix, refactor, docs, test, chore, perf

**Never include:** Emojis, AI attribution, co-author tags

## Ticket-to-Commit Mapping

- BUG tickets → `fix(scope)`
- FEAT tickets → `feat(scope)`
- DOCS tickets → `docs(scope)`
- CHORE tickets → `chore(scope)`

Extract scope from ticket content (e.g., sentiment, api, ui, narratives, timeline)

## Pull Request Workflow

1. **Create PR**: Push feature branch and open PR against main
2. **PR Naming**: Use same format as commits: `type(scope): description`
3. **Merge Strategy**: Squash merge to main (one commit per PR)
4. **Requirements**: All tests must pass before merge
5. **Review**: Ensure changes match ticket requirements