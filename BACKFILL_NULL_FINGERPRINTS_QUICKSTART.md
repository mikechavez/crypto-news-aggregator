# Backfill NULL Fingerprints - Quick Start

**Fix 229 narratives with NULL fingerprints in 3 steps**

## TL;DR

```bash
# 1. Preview what will be fixed (safe, no changes)
poetry run python scripts/backfill_null_fingerprints.py --dry-run

# 2. Test with 10 narratives
poetry run python scripts/backfill_null_fingerprints.py --limit 10

# 3. Fix all 229 narratives
poetry run python scripts/backfill_null_fingerprints.py
```

## The Problem

229 narratives have `nucleus_entity = None` in their fingerprints, causing:
- ❌ Failed narrative matching
- ❌ Duplicate narratives
- ❌ Fragmented signal scores

## The Solution

This script regenerates fingerprints by extracting entity data from articles.

## Step-by-Step

### Step 1: Preview Changes (Safe)

```bash
poetry run python scripts/backfill_null_fingerprints.py --dry-run
```

**What happens:**
- Shows what would be updated
- No database changes
- Takes ~2 minutes

**Expected output:**
```
📊 Found 229 narratives with NULL fingerprints
✅ Successfully updated: 220
⚠️  Skipped: 9
⚠️  This was a DRY RUN - no changes were saved
```

### Step 2: Test with Sample (Recommended)

```bash
poetry run python scripts/backfill_null_fingerprints.py --limit 10 --verbose
```

**What happens:**
- Processes only 10 narratives
- Shows detailed logs
- Updates database
- Takes ~20 seconds

**Expected output:**
```
✅ Updated 'Bitcoin Price Volatility...' - nucleus=Bitcoin, actors=5, actions=3
✅ Updated 'Ethereum Network Upgrade...' - nucleus=Ethereum, actors=5, actions=2
...
Success rate: 90.0%
```

### Step 3: Fix All Narratives (Production)

```bash
poetry run python scripts/backfill_null_fingerprints.py
```

**What happens:**
- Processes all 229 narratives
- Asks for confirmation (type 'y')
- Updates database
- Takes ~5-10 minutes

**Expected output:**
```
❓ Proceed with backfill of 229 narratives? [y/N]: y
🚀 Starting backfill...
📦 Processing batch 1/5 (50 narratives)
...
✅ Successfully updated: 220
```

## Verify Results

After backfill, verify it worked:

```bash
poetry run python scripts/check_duplicate_narratives.py
```

**Expected:** 0 narratives with NULL nucleus_entity

## Next Steps

After fixing fingerprints, merge duplicates:

```bash
poetry run python scripts/match_duplicate_narratives.py
```

This will merge the 229 duplicate narratives into consolidated stories.

## Troubleshooting

### "No narratives found with NULL fingerprints"
✅ Already fixed! Nothing to do.

### High skip rate (>20%)
⚠️ Articles missing entity data. Run entity extraction first:
```bash
poetry run python scripts/backfill_entities.py
```

### Script hangs
⚠️ Reduce batch size:
```bash
poetry run python scripts/backfill_null_fingerprints.py --batch-size 10
```

## Full Documentation

For complete details, see:
- **User Guide:** `BACKFILL_NULL_FINGERPRINTS_GUIDE.md`
- **Implementation:** `BACKFILL_NULL_FINGERPRINTS_IMPLEMENTATION.md`

## Help

```bash
poetry run python scripts/backfill_null_fingerprints.py --help
```
