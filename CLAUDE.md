# Crypto News Aggregator - Project Instructions

## Git Workflow Standards

### Branch Strategy
- ALL changes require feature branches - NO direct commits to main
- Branch format: `{type}/{description}`
- Types: `feature/`, `fix/`, `docs/`, `chore/`

### Commit Message Format
```
type(scope): short description

- Bullet point details if needed
```

**Commit types:** feat, fix, refactor, docs, test, chore, perf

**Rules:**
- No emojis
- No AI attribution or co-author tags
- Extract scope from ticket (e.g., sentiment, api, ui, narratives, timeline)
- Map tickets to types: BUG→`fix()`, FEAT→`feat()`, DOCS→`docs()`, CHORE→`chore()`

### Pull Request Workflow
1. Create PR: Push feature branch and open PR against main
2. PR naming: Use same format as commits: `type(scope): description`
3. Merge strategy: Squash merge to main (one commit per PR)
4. Requirements: All tests must pass before merge
5. Review: Ensure changes match ticket requirements
