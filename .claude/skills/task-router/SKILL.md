---
name: task-router
description: Automatically routes tasks to specialized subagents based on task type. Handles test execution, script running, and code analysis delegation.
user-invocable: false
---

# Task Router Skill

This skill automatically delegates tasks to subagents when Claude detects specific patterns in user requests.


## Delegation Rules

### Script Runner Subagent

Delegate to Script Runner when the task involves:
- Running Python scripts in the `scripts/` directory
- Database migrations or seeding operations
- Data cleanup or maintenance tasks
- Performance profiling or analysis scripts
- Cost analysis or reporting scripts
- Any command starting with `python scripts/`

**Delegation pattern:**
```
/script-runner [describe what script needs to run and why]
```

### Test Runner Subagent
Delegate to Test Runner when the task involves:
- Running pytest or test suites
- Verifying bug fixes (e.g., "verify BUG-001 is fixed")
- Checking test coverage
- Running specific test files or test functions
- Any command containing `pytest`

**Delegation pattern:**
```
/test-runner [describe what tests to run and what to verify]
```

## Detection Patterns

**Script execution triggers:**
- "run the [script name] script"
- "execute the migration"
- "seed the database"
- "clean up [data type]"
- "analyze performance"
- "generate a report"

**Test execution triggers:**
- "run tests"
- "verify [bug/feature]"
- "check test coverage"
- "test the [component]"
- "make sure tests pass"

## When NOT to delegate

Do NOT delegate for:
- Code review or analysis (handle inline)
- Writing new code (handle inline)
- Explaining how code works (handle inline)
- Simple file operations (handle inline)
- Questions about the codebase (handle inline)

## Example Delegations

**User:** "Run the narrative fingerprinting script to regenerate all fingerprints"
**Action:** `/script-runner Run scripts/regenerate_fingerprints.py to update all narrative fingerprints in the database`

**User:** "Make sure the timeline tests pass after my changes"
**Action:** `/test-runner Run pytest tests/test_timeline.py to verify timeline functionality still works`

**User:** "Verify BUG-001 is actually fixed"
**Action:** `/test-runner Run the full test suite and specifically verify article count matching works correctly`

## Context to Provide

When delegating, always include:
1. What specific action needs to happen
2. What files/components are involved
3. What success looks like
4. Any relevant context from the current conversation

## Integration with Sprint Workflow

When tasks relate to sprint items (e.g., BUG-001, BUG-002, FEATURE-003):
- Include the sprint item ID in the delegation
- Mention what needs to be verified
- Reference any acceptance criteria