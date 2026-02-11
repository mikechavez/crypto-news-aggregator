# Narrative Actions Backfill - Quick Start

## TL;DR
Run this to fix empty `key_actions` in narrative fingerprints:

```bash
# 1. Test first (no database changes)
python scripts/test_action_extraction.py

# 2. Run backfill
python scripts/backfill_narrative_actions.py
```

## What This Fixes
Empty `key_actions` arrays prevent narratives from matching (they can't reach the 0.6 similarity threshold).

## Prerequisites
- ✓ `ANTHROPIC_API_KEY` in `.env`
- ✓ MongoDB running and connected
- ✓ Narratives have `summary` field

## Step-by-Step

### 1. Test Action Extraction (Safe)
```bash
python3 scripts/test_action_extraction.py
```

**Expected output**:
```
Test 1: regulatory_enforcement
✓ Extracted actions: ['filed lawsuit', 'regulatory enforcement']
```

If this works, proceed to step 2.

### 2. Run Backfill
```bash
python3 scripts/backfill_narrative_actions.py
```

**Expected output**:
```
INFO - Found 45 narratives with empty key_actions
INFO - [1/45] ✓ Updated narrative with actions: ['filed lawsuit', 'regulatory action']
...
Backfill complete!
Successfully updated: 42
```

### 3. Verify Results & Test Matching
```bash
python3 scripts/verify_matching_fix.py
```

**Expected output**:
```
PART 1: BACKFILL VERIFICATION
Total narratives: 127
Narratives with actions: 115 (90.6%)

PART 2: MATCHING TEST
Match rate: 65.2%
Top similarity: 0.850

PART 3: BEFORE vs AFTER
✓ Improvement: +65.2 percentage points
✅ SUCCESS: Narratives are now matching!
```

## What It Does
1. Finds narratives with empty `key_actions`
2. Sends summary to Claude Haiku
3. Extracts 2-3 action phrases (e.g., "filed lawsuit")
4. Updates `fingerprint.key_actions` in database
5. Logs progress every 10 narratives

## Cost
- ~$0.0001 per narrative (using Claude Haiku)
- 50 narratives = ~$0.01
- 500 narratives = ~$0.05

## Rate Limiting
- 1 second between API calls (built-in)
- Safe for production use

## Troubleshooting

**No API key**:
```bash
export ANTHROPIC_API_KEY="your-key-here"
```

**MongoDB error**:
Check `.env` has `MONGODB_URI`

**No narratives found**:
Already backfilled! ✓

## Next Steps
After backfilling:
1. Test narrative matching
2. Monitor similarity scores
3. Check for fewer duplicate narratives

## Full Documentation
- Complete guide: `NARRATIVE_ACTIONS_BACKFILL.md`
- Implementation details: `BACKFILL_ACTIONS_IMPLEMENTATION.md`
