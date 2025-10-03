---
trigger: always_on
---

# Testing Standards Rules

**Activation Mode:** Model Decision
**When to apply:** When writing tests, modifying test files, or implementing new features that need testing

## Test Coverage Requirements:
1. Every new API endpoint must have smoke tests
2. Every new service must have unit tests for core methods
3. Database operations must have integration tests
4. Background workers must have startup/shutdown tests

## Test Writing Standards:
1. Use realistic test data, avoid overly complex mocks
2. Test happy path and error conditions
3. Mock external APIs but use real database connections in test environment
4. Focus on testing integration points and boundaries

## Before Deployment Testing:
1. All tests must pass: `poetry run pytest`
2. Manual verification of critical paths
3. Check Railway logs for successful startup
4. Verify API endpoints return expected responses

## Test Organization:
1. Unit tests in tests/services/
2. Integration tests in tests/integration/
3. API tests in tests/api/
4. Background worker tests in tests/background/

## UI Testing Standards (Phase 2+):
1. Critical user flows must have integration tests
2. Test accessibility: keyboard navigation, ARIA labels
3. Test error states: network failures, empty states
4. Visual tests for key components (Storybook or Chromatic)

## Manual Testing Checklist:
- [ ] Test on mobile viewport (375px width)
- [ ] Test with slow 3G network throttling
- [ ] Test with browser extensions disabled
- [ ] Verify API key authentication works
- [ ] Check browser console for errors