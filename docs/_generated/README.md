# Generated Documentation

This directory contains code-derived documentation that is regenerable from source code and configuration. All files here should be treated as derivations of ground truth (the source code).

## Directory Structure

### `system/` - System Documentation
Core architectural modules documented from evidence pack:

- **00-overview.md**: High-level system architecture with data flow diagram
- **10-entrypoints.md**: Application entry points (FastAPI, Celery worker, CLI)
- **20-scheduling.md**: Celery Beat scheduler and task dispatch mechanism
- **30-ingestion.md**: RSS pipeline and article ingestion workflow
- **40-processing.md**: Entity extraction, narrative clustering, signals detection
- **50-data-model.md**: MongoDB collections schema and data relationships
- **60-llm.md**: Claude API integration and briefing generation
- **70-frontend.md**: React routing and API integration

### `context/` - Historical Context
Extracted from legacy documentation and Windsurf files to preserve design rationale:

- **extracted-windsurf-context.md**: Decision context from high-priority Windsurf files
- Future context docs linking to specific system modules

### `evidence/` - Source Evidence
Raw grep output used to generate system docs (regenerable):

- Numbered `NN-*.txt` files with ripgrep search results
- Each file has 3-line header: description and generation command
- Used as input to system doc generation process

## Validation

All generated documentation is validated by `scripts/validate-docs.sh`:

```bash
./scripts/validate-docs.sh
```

### Validation Rules

**System Docs:**
- Required sections: Overview, Architecture, Implementation Details, Operational Checks
- Exception: 00-overview.md has different structure (System Diagram, Module Interconnections, etc.)
- Line count: ≤400 lines for core content
- Contains operational checks with runnable commands

**Context Docs:**
- Optional directory (can be empty)
- Entries link to valid system doc anchors
- Prevents orphaned historical information

**Evidence Pack:**
- Optional directory (regenerable)
- Warning for files >500 lines
- No empty files

## Regeneration

### Evidence Pack
Regenerate from source code with ripgrep:
```bash
./scripts/generate-evidence.sh
```

### System Docs
Generated from evidence pack by reading code patterns. To regenerate:
1. Run `generate-evidence.sh` to update evidence pack
2. Update system docs based on evidence changes (currently manual)

## Anchor References

System doc anchors enable cross-references and context linking:
- **Anchor format:** `#module-name-overview` (e.g., `#scheduling-task-dispatch`)
- **Used by:** Context docs via `relates_to` fields
- **Prevents:** Orphaned historical information without current system tie-ins

## Adding New Documentation

1. Create file in appropriate directory
2. Follow section structure (Overview, Architecture, Implementation, Operational Checks)
3. Include file:line references to evidence pack
4. Add anchors for cross-referencing
5. Run `validate-docs.sh` to check compliance

## Maintenance

- Documentation should stay synchronized with source code
- Run validation regularly to catch drift
- Use `grep` references to verify accuracy
- Update context docs when adding system capabilities
