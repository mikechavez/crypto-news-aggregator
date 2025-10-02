---
trigger: always_on
---

# Development Practices Rules

**Activation Mode:** Always On

## Pre-Development Rules:
1. **ALWAYS create feature branch before starting work**
2. **NEVER commit directly to main branch**
3. **ALL changes must go through PR and CI/CD pipeline**
4. Commit frequently with descriptive messages following conventional commit format

## Branch Strategy:
**ALL changes require feature branches and PRs:**

1. **Infrastructure/Tooling** → feature branch + PR:
   - Smoke tests, deployment scripts, CI configuration
   - Development tooling and safety improvements
   - Example: `feat/backfill-entities-script`

2. **Bug fixes** → feature branch + PR:
   - Small, well-tested bug fixes
   - Example: `fix/entity-extraction-403-error`

3. **Feature development** → feature branch + PR:
   - New API endpoints or functionality
   - Database schema changes
   - Integration with new services
   - Any user-facing changes
   - Example: `feat/entity-extraction-batch`

4. **Experimental/Risky changes** → feature branch + PR:
   - Large refactors
   - Architecture changes
   - Dependency upgrades
   - Complex integrations
   - Example: `refactor/mongodb-connection-pool`

## Branch Naming Convention:
- `feat/description` - New features
- `fix/description` - Bug fixes
- `refactor/description` - Code refactoring
- `docs/description` - Documentation only
- `test/description` - Test additions/changes
- `chore/description` - Maintenance tasks

## PR Workflow:
1. Create feature branch from main
2. Make changes and commit frequently
3. Push branch to GitHub
4. Open Pull Request
5. **Wait for CI/CD tests to pass**
6. Review PR (self-review or team review)
7. Merge to main only after:
   - ✅ All CI/CD tests pass
   - ✅ No merge conflicts
   - ✅ Code review approved (if applicable)

## Pre-PR Rules:
1. MANDATORY: Run full test suite locally before pushing
   ```bash
   poetry run pytest
   ```
2. MANDATORY: Test local server startup and verify API endpoints respond
   ```bash
   poetry run python main.py
   ```
3. MANDATORY: Check for import errors and dependency issues locally
4. MANDATORY: Verify all new files are included in commit
5. Only push if all local tests pass

## Testing Requirements:
1. Write smoke tests for any new endpoints or services
2. Test database schema changes in isolation before deployment
3. Verify all imports resolve before committing
4. Add tests for any code that touches external APIs or databases
5. Ensure existing tests still pass

## Deployment Safety:
1. Monitor Railway logs immediately after merge to main
2. Be prepared to rollback if deployment fails
3. Document working configurations
4. Test major changes in feature branches first
5. Never bypass CI/CD pipeline

## Code Quality:
1. Keep changes small and focused
2. One database migration per PR
3. Avoid large refactors without proper testing
4. Document breaking changes and migration requirements
5. Use conventional commit messages:
   - `feat: add entity backfill script`
   - `fix: resolve ObjectId conversion error`
   - `docs: add backfill documentation`
   - `test: add entity extraction tests`
   - `refactor: improve batch processing`

## Commit Message Format:
```
<type>(<scope>): <subject>

<body>

<footer>
```

Examples:
```
feat(scripts): add entity backfill script with safety features

- Queries articles without entities
- Processes in batches of 10
- Includes dry-run mode and failure detection
- Creates entity_mentions records

Closes #123
```

```
fix(entity-extraction): handle ObjectId conversion in backfill

Previously the script failed to update articles because string IDs
weren't converted to ObjectId format for MongoDB queries.

Fixes #124
```

## Emergency Hotfixes:
Even for critical production issues:
1. Create hotfix branch: `hotfix/critical-issue`
2. Make minimal fix
3. Open PR (can be fast-tracked)
4. Wait for CI/CD to pass
5. Merge after tests pass
6. Monitor deployment

**Rationale**: CI/CD catches issues that manual testing might miss. Even urgent fixes benefit from automated validation.

## Summary:
- ❌ **NEVER** commit directly to main
- ✅ **ALWAYS** use feature branches
- ✅ **ALWAYS** open PRs
- ✅ **ALWAYS** wait for CI/CD to pass
- ✅ **ALWAYS** run tests locally first
