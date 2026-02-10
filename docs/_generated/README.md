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

## Regeneration Workflow

### When to Regenerate
- **System docs**: After significant code changes (new modules, architecture shifts)
- **Evidence pack**: Before regenerating system docs
- **Context docs**: When system behavior changes (optional, links are maintained)

### Step 1: Generate Evidence Pack
Extracts code patterns via ripgrep (must be in git repo root):
```bash
cd /path/to/repo
./scripts/generate-evidence.sh
```

This creates/updates 12 evidence files in `docs/_generated/evidence/`:
- `01-entrypoints.txt` - Application entry points
- `02-celery-registration.txt` - Task registration
- `02-celery-beat.txt` - Scheduled tasks
- `03-mongo-init.txt` - MongoDB client init
- `03-mongo-collections.txt` - Collection usage
- `04-llm-client.txt` - LLM client init
- `04-llm-prompts.txt` - Prompt construction
- `05-briefing-generation.txt` - Briefing workflow
- `05-briefing-save.txt` - Database persistence
- `06-frontend-routes.txt` - Frontend routing
- `07-error-handlers.txt` - Exception handling
- `08-config.txt` - Configuration

### Step 2: Regenerate System Docs
Read the updated evidence pack and generate/update system docs. This is a Claude Code task:

```bash
# Example prompt:
# "Regenerate 20-scheduling.md from the updated evidence pack in
#  docs/_generated/evidence/. Use file:line references from 02-celery-beat.txt
#  and 02-celery-registration.txt. Keep all existing anchors."
```

For each module doc:
- **00-overview.md** - Summary of all interconnections (from 01-entrypoints.txt, evidence files)
- **10-entrypoints.md** - From 01-entrypoints.txt
- **20-scheduling.md** - From 02-celery-beat.txt + 02-celery-registration.txt
- **30-ingestion.md** - From relevant evidence files
- **40-processing.md** - From relevant evidence files
- **50-data-model.md** - From 03-mongo-*.txt files
- **60-llm.md** - From 04-llm-*.txt files
- **70-frontend.md** - From 06-frontend-routes.txt

### Step 3: Update Context Docs (Optional)
If system behavior changed, update context docs to maintain anchor links:
- Verify all `relates_to` anchors still exist
- Add new context entries for new behavior
- Mark obsolete entries with dates

### Step 4: Validate
Check that all docs conform to structure requirements:
```bash
./scripts/validate-docs.sh
```

Should exit with status 0 (all checks pass).

---

**Important:** Never edit system docs directly. Always regenerate from evidence pack.

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
