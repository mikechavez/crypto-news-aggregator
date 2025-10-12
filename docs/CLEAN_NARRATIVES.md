# Clean Narratives Script

## Overview

The `scripts/clean_narratives.py` script deletes narratives from the MongoDB database, allowing the system to regenerate them with corrected code.

## Problem

The narrative discovery system created 30+ narratives that remain in the MongoDB database even after rolling back the code. This script provides a clean way to remove them.

## Usage

### 1. Dry Run (Recommended First Step)

See what would be deleted without actually deleting:

```bash
poetry run python scripts/clean_narratives.py --dry-run
```

### 2. List Narratives

View sample narratives before deleting:

```bash
poetry run python scripts/clean_narratives.py --list --dry-run
```

### 3. Delete All Narratives

Delete all narratives from the database:

```bash
poetry run python scripts/clean_narratives.py --yes
```

**Note:** You will be prompted to type `DELETE ALL` to confirm.

### 4. Delete Old Narratives

Delete only narratives older than N days:

```bash
# Delete narratives older than 7 days
poetry run python scripts/clean_narratives.py --days 7 --yes

# Delete narratives older than 30 days
poetry run python scripts/clean_narratives.py --days 30 --yes
```

## Options

| Option | Description |
|--------|-------------|
| `--dry-run` | Show what would be deleted without actually deleting |
| `--yes` | Confirm deletion (required to actually delete) |
| `--days N` | Only delete narratives older than N days |
| `--list` | List sample narratives before deleting |

## Safety Features

1. **Dry Run by Default**: Must explicitly use `--yes` to delete
2. **Extra Confirmation**: When deleting all narratives, you must type `DELETE ALL`
3. **Preview**: Use `--list` to see what will be deleted
4. **Verification**: Shows count of remaining narratives after deletion

## Examples

### Example 1: Safe Exploration

```bash
# Step 1: See how many narratives exist
poetry run python scripts/clean_narratives.py --dry-run

# Step 2: View sample narratives
poetry run python scripts/clean_narratives.py --list --dry-run

# Step 3: Delete if needed
poetry run python scripts/clean_narratives.py --yes
```

### Example 2: Clean Old Narratives

```bash
# Check how many narratives are older than 7 days
poetry run python scripts/clean_narratives.py --days 7 --dry-run

# Delete them
poetry run python scripts/clean_narratives.py --days 7 --yes
```

## After Cleaning

After running this script, the narrative discovery system will regenerate narratives on its next run based on the current article data and corrected code.

## Troubleshooting

### Connection Issues

If you see MongoDB connection errors:

1. Check that `MONGODB_URI` is set in your `.env` file
2. Verify MongoDB is accessible
3. Check Railway logs if using Railway MongoDB

### No Narratives Found

If the script reports 0 narratives:

- The collection may already be empty
- Check that you're connected to the correct MongoDB database
- Verify the database name in your `.env` file matches

## Related Documentation

- [Narrative Discovery Implementation](../NARRATIVE_DISCOVERY_IMPLEMENTATION.md)
- [Narrative Timeline Tracking](../NARRATIVE_TIMELINE_TRACKING.md)
