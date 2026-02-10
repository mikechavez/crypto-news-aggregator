# Merge Duplicate Narratives - Quick Start

**Consolidate 229 duplicate narratives in 3 steps**

## Prerequisites

✅ Run `backfill_null_fingerprints.py` first to fix NULL fingerprints

## TL;DR

```bash
# 1. Preview merges (safe, no changes)
poetry run python scripts/merge_duplicate_narratives.py --dry-run

# 2. Test on one nucleus entity
poetry run python scripts/merge_duplicate_narratives.py --nucleus "Bitcoin" --verbose

# 3. Merge all duplicates
poetry run python scripts/merge_duplicate_narratives.py
```

## The Problem

After backfill, many narratives share the same `nucleus_entity`:
- 45 narratives about "Bitcoin"
- 32 narratives about "Ethereum"
- 18 narratives about "SEC"
- etc.

These should be merged into consolidated narratives.

## The Solution

This script merges narratives with similar fingerprints (similarity >= 0.6).

## Step-by-Step

### Step 1: Preview Merges (Safe)

```bash
poetry run python scripts/merge_duplicate_narratives.py --dry-run --verbose
```

**What happens:**
- Shows what would be merged
- No database changes
- Takes ~30 seconds

**Expected output:**
```
📊 Found 229 narratives
🔍 Checking nucleus 'Bitcoin' (45 narratives)
   Found 12 duplicate pairs
   [DRY RUN] Would merge 'Bitcoin Price...' (5 articles) 
   → 'Bitcoin Market...' (23 articles) [similarity: 0.723]

MERGE SUMMARY
Duplicate pairs found:         48
Would merge: 48 duplicates
Reduction: 229 → 181 narratives (21.0% reduction)
```

### Step 2: Test on One Nucleus (Recommended)

```bash
poetry run python scripts/merge_duplicate_narratives.py --nucleus "Bitcoin" --verbose
```

**What happens:**
- Only merges Bitcoin narratives
- Shows detailed logs
- Updates database
- Takes ~5 seconds

**Expected output:**
```
🎯 Filtering to nucleus: 'Bitcoin'
🔍 Checking nucleus 'Bitcoin' (45 narratives)
   ✅ Merged 'Bitcoin Price...' (5 articles) → 'Bitcoin Market...' (28 articles)
   ✅ Merged 'Bitcoin Trading...' (8 articles) → 'Bitcoin Market...' (36 articles)
   ...
Merges performed: 12
```

### Step 3: Merge All Duplicates (Production)

```bash
poetry run python scripts/merge_duplicate_narratives.py
```

**What happens:**
- Processes all nucleus entities
- Asks for confirmation (type 'y')
- Updates database
- Takes ~1 minute

**Expected output:**
```
❓ Proceed with merge? [y/N]: y
🚀 Starting merge...
✅ Merged 48 duplicate narratives
Reduction: 229 → 181 narratives
```

## Verify Results

After merge, verify it worked:

```bash
poetry run python scripts/check_duplicate_narratives.py
```

**Expected:** Significantly fewer duplicates (e.g., 181 instead of 229)

## Adaptive Thresholds

The script uses smart thresholds:
- **Recent narratives (updated within 48h):** 0.5 threshold
- **Older narratives (>48h):** 0.6 threshold

This allows recent stories to merge more easily while keeping strict matching for older ones.

## Custom Threshold

Want stricter matching?

```bash
# Use 0.7 threshold for older narratives
poetry run python scripts/merge_duplicate_narratives.py --threshold 0.7 --dry-run
```

## Troubleshooting

### "No duplicates found"
✅ Fingerprints are unique - no merges needed

### Too many merges
⚠️ Threshold too low. Try:
```bash
poetry run python scripts/merge_duplicate_narratives.py --threshold 0.7 --dry-run
```

### Too few merges
⚠️ Threshold too high. Try:
```bash
poetry run python scripts/merge_duplicate_narratives.py --threshold 0.5 --dry-run
```

## What Gets Merged

For each merge:
- **Primary:** Narrative with most articles (kept)
- **Duplicate:** Other narrative (deleted)
- **Article IDs:** Combined and deduplicated
- **Entity Salience:** Averaged across both
- **Lifecycle State:** Recalculated from combined data

## Full Documentation

For complete details, see:
- **User Guide:** `MERGE_DUPLICATE_NARRATIVES_GUIDE.md`

## Help

```bash
poetry run python scripts/merge_duplicate_narratives.py --help
```
