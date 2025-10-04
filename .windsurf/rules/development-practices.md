---
trigger: always_on
---

# Development Practices Rules

**Activation Mode:** Always On

## Pre-Development Rules:
1. Always create feature branch before starting work
2. **NEVER work directly on main branch**
3. **ALL code changes must go through feature branches and PR process**
4. Commit frequently with descriptive messages following conventional commit format

## Branch Strategy:
**ALL changes require feature branches - NO exceptions**

1. **Infrastructure/Safety code** → use feature branches:
   - Smoke tests, deployment scripts, CI configuration
   - Bug fixes (small, well-tested)
   - Development tooling and safety improvements
   - CORS configuration changes
   - Environment variable updates

2. **Feature development** → use feature branches:
   - New API endpoints or functionality
   - Database schema changes
   - Integration with new services
   - Any user-facing changes

3. **Experimental/Risky changes** → use feature branches:
   - Large refactors
   - Architecture changes
   - Dependency upgrades
   - Complex integrations

## UI Development Branch Strategy:
**ALL UI changes require feature branches**

1. **Component library work** → feature branches:
   - New reusable components
   - Styling system changes
   - Design system updates

2. **Page implementations** → feature branches:
   - New routes/pages
   - Complex interactions
   - Integration with new API endpoints

3. **UI tweaks and fixes** → feature branches:
   - Copy changes
   - Button color adjustments
   - Spacing/padding fixes
   - Bug fixes in existing components

## Pre-Deployment Rules:
1. MANDATORY: Run full test suite locally before any deployment
2. MANDATORY: Test local server startup and verify API endpoints respond
3. MANDATORY: Check for import errors and dependency issues locally
4. Only deploy if all local tests pass

## Testing Requirements:
1. Write smoke tests for any new endpoints or services
2. Test database schema changes in isolation before deployment
3. Verify all imports resolve before committing
4. Add tests for any code that touches external APIs or databases

## Deployment Safety:
1. Monitor Railway logs immediately after deployment
2. Be prepared to rollback if deployment fails
3. Document working configurations
4. Test major changes in feature branches first

## Code Quality:
1. Keep changes small and focused
2. One database migration per PR
3. Avoid large refactors without proper testing
4. Document breaking changes and migration requirements

## Main Branch Protection:
1. **Main branch is protected - direct commits are FORBIDDEN**
2. All changes must be merged via pull requests
3. Feature branches should be merged to main after review
4. Use descriptive branch names: `feature/`, `fix/`, `docs/`, `chore/`
