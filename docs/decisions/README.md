# Architectural Decision Records (ADRs)

This directory contains records of architectural decisions made during development.

## Active Decisions

- [002. Rule-Based Article Relevance Classification](./002-rule-based-relevance-classification.md) - 2026-01-02
- [001. Use Claude Sonnet 4.5 for Briefing Generation](./001-sonnet-vs-haiku-for-briefing.md) - 2025-12-29

## What is an ADR?

An ADR documents an important architectural decision along with its context and consequences.

## When to Create an ADR

Create an ADR when making decisions about:
- Choice of technologies or frameworks
- System architecture patterns
- Database schema design
- API design approaches
- Performance optimization strategies
- Security implementations
- Third-party integrations

## How to Create an ADR

1. Copy the template:
   ```bash
   cp docs/decisions/template.md docs/decisions/001-decision-name.md
   ```

2. Fill in the sections:
   - Status (Proposed/Accepted/Deprecated/Superseded)
   - Context (what prompted this decision)
   - Decision (what was decided)
   - Consequences (positive and negative outcomes)

3. Number sequentially (001, 002, etc.)

4. Add to the list above

5. Commit with the code change it relates to

## Naming Convention

```
NNN-short-decision-title.md

Examples:
001-sonnet-vs-haiku-for-briefing.md
002-mongodb-migration-from-postgres.md
003-redis-caching-strategy.md
```

## Template

Use [template.md](./template.md) to create new ADRs.
