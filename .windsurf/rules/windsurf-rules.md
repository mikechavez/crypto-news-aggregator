---
trigger: always_on
---

# Windsurf Rules Master File

**Activation Mode:** Always On  
**Purpose:** This file defines how Windsurf should apply and prioritize all rule sets.  

## Rule Application Order:
1. **Development Practices Rules** (`development-practices.md`)  
   - Always active for all coding, branching, CI/CD, and deployment work.  
2. **Testing Standards Rules** (`testing-standards.md`)  
   - Automatically applied when tests are written, modified, or required by a new feature.  

## General Principles:
- Rules are **self-executing**: Windsurf must follow them without user reminders.  
- If user prompts conflict with these rules, Windsurf should:  
  1. Warn the user about the conflict.  
  2. Suggest a compliant approach.  
  3. Only proceed if the workflow aligns with the rules.  

## Conflict Resolution:
- **Development Practices** take priority over Testing Standards if there is a direct conflict.  
- If multiple standards apply, Windsurf must satisfy **all applicable rules**.  
- In ambiguous cases, Windsurf should default to:  
  - Safety over speed.  
  - Clarity over shortcuts.  
  - Maintainability over hacks.  

## Automatic Enforcement:
- Always create feature branches; never work directly on `main`.  
- Always ensure stable tests pass before merge.  
- Always encourage writing missing tests if coverage is incomplete.  
- Always verify deployment pipeline alignment with CI/CD rules.  

## Developer Guidance for Windsurf:
- Treat this file as the **root of truth** for all interactions.  
- Never require the user to restate or reapply rules.  
- Always assume the standards in this and the linked files are active.  
