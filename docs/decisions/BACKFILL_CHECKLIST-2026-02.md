# Narrative Actions Backfill - Execution Checklist

## Pre-Flight Checklist

### Environment Setup
- [ ] `ANTHROPIC_API_KEY` is set in `.env`
- [ ] MongoDB is running and accessible
- [ ] `MONGODB_URI` is configured in `.env`
- [ ] Python 3.8+ is installed
- [ ] All dependencies are installed (`poetry install` or `pip install -r requirements.txt`)

### Backup (Recommended)
- [ ] Create MongoDB backup before running backfill
  ```bash
  mongodump --uri="$MONGODB_URI" --out=backup_$(date +%Y%m%d)
  ```

### Verification
- [ ] Check that narratives exist in database
- [ ] Verify some narratives have summaries
- [ ] Confirm API key has sufficient credits

## Execution Workflow

### Step 1: Test Action Extraction ✅
**Purpose**: Verify API integration works without modifying database

```bash
python3 scripts/test_action_extraction.py
```

**Expected Output**:
```
Test 1: regulatory_enforcement
✓ Extracted actions: ['filed lawsuit', 'regulatory enforcement']
```

**Checklist**:
- [ ] Script runs without errors
- [ ] API key is recognized
- [ ] Actions are extracted for all test cases
- [ ] Actions are descriptive (2-4 words each)
- [ ] No rate limiting errors

**If Failed**:
- Check `ANTHROPIC_API_KEY` is set
- Verify API key is valid
- Check internet connection
- Review error messages

---

### Step 2: Run Backfill 🔄
**Purpose**: Populate `key_actions` for all narratives with empty arrays

```bash
python3 scripts/backfill_narrative_actions.py
```

**Expected Output**:
```
INFO - Starting narrative actions backfill...
INFO - Found 45 narratives with empty key_actions
INFO - [1/45] Processing narrative 507f... (theme: regulatory_enforcement)
INFO - [1/45] ✓ Updated narrative 507f... with actions: ['filed lawsuit', 'regulatory action']
...
INFO - Progress: 10/45 processed, 9 updated, 0 skipped, 1 errors
...
================================================================================
Backfill complete!
Total narratives: 45
Successfully updated: 42
Skipped (no summary): 1
Errors: 2
================================================================================
```

**Checklist**:
- [ ] Script finds narratives with empty key_actions
- [ ] Progress logs appear every 10 narratives
- [ ] Success rate is >80%
- [ ] Script completes without fatal errors
- [ ] Final summary shows updated count

**Success Criteria**:
- ✅ Updated count is >80% of total
- ✅ Error count is <10% of total
- ✅ Script completes successfully

**If Failed**:
- Review error logs
- Check which narratives failed
- Verify summaries exist
- Re-run script (it's idempotent)

---

### Step 3: Verify Results 📊
**Purpose**: Confirm backfill worked and test matching improvements

```bash
python3 scripts/verify_matching_fix.py
```

**Expected Output**:
```
🔍 NARRATIVE MATCHING VERIFICATION

PART 1: BACKFILL VERIFICATION
Total narratives: 127
Narratives with actions: 115 (90.6%)

Sample 1:
  Theme: regulatory_enforcement
  Actions: ['filed lawsuit', 'regulatory enforcement']

PART 2: MATCHING TEST (LAST 24 HOURS)
Total narratives tested: 23
Matches found: 15
Match rate: 65.2%
Top similarity: 0.850

PART 3: BEFORE vs AFTER COMPARISON
Match rate: 0.0% → 65.2% (+65.2 pp)
✅ SUCCESS: Narratives are now matching!
```

**Checklist**:
- [ ] Backfill percentage is >80%
- [ ] Sample fingerprints show 2-3 actions
- [ ] Actions are descriptive
- [ ] Match rate is >0%
- [ ] Top similarity scores are >0.6
- [ ] Conclusion shows "SUCCESS"

**Success Criteria**:
- ✅ Backfill percentage >80%
- ✅ Match rate >30%
- ✅ Top similarity >0.7
- ✅ Multiple matches found

**If Results Are Poor**:
- Check if enough narratives exist (need >10)
- Review sample actions quality
- Wait for more narratives to accumulate
- Consider threshold adjustment

---

## Post-Execution Checklist

### Immediate Verification
- [ ] Database shows updated `fingerprint.key_actions` fields
- [ ] Sample narratives have 2-3 actions each
- [ ] Actions are relevant to narrative summaries
- [ ] No narratives were corrupted

### Database Queries
```python
# Check updated count
db.narratives.count_documents({
    "fingerprint.key_actions": {"$exists": True, "$ne": []}
})

# Sample a narrative
db.narratives.find_one({
    "fingerprint.key_actions": {"$exists": True, "$ne": []}
})
```

### Monitoring
- [ ] Run verification script weekly
- [ ] Monitor match rates over time
- [ ] Check for duplicate narratives
- [ ] Review narrative continuity

---

## Success Metrics

### Backfill Metrics
- **Excellent**: >90% narratives with actions
- **Good**: 70-90% narratives with actions
- **Poor**: <70% narratives with actions

### Matching Metrics
- **Excellent**: >50% match rate
- **Good**: 30-50% match rate
- **Fair**: 10-30% match rate
- **Poor**: <10% match rate

### Similarity Metrics
- **Excellent**: Top scores >0.8
- **Good**: Top scores 0.6-0.8
- **Poor**: Top scores <0.6

---

## Troubleshooting Guide

### Issue: No API Key
**Error**: `ANTHROPIC_API_KEY not configured in environment`

**Solution**:
```bash
export ANTHROPIC_API_KEY="your-key-here"
# Or add to .env file
echo 'ANTHROPIC_API_KEY="your-key-here"' >> .env
```

---

### Issue: Rate Limiting
**Error**: `429 - Too Many Requests`

**Solution**:
- Script already includes 1-second delays
- Wait a few minutes and re-run
- Check API usage limits

---

### Issue: MongoDB Connection
**Error**: `Failed to connect to MongoDB`

**Solution**:
- Verify `MONGODB_URI` in `.env`
- Check MongoDB is running
- Test connection manually

---

### Issue: No Narratives Found
**Output**: `Found 0 narratives with empty key_actions`

**Meaning**: Already backfilled! ✅

**Action**: Run verification script to confirm

---

### Issue: Low Success Rate
**Output**: `Successfully updated: 5, Errors: 40`

**Possible Causes**:
- Many narratives lack summaries
- API errors
- Network issues

**Solution**:
- Check error logs for patterns
- Verify narrative summaries exist
- Re-run backfill script

---

### Issue: No Matches Found
**Output**: `Match rate: 0.0%`

**Possible Causes**:
- Not enough narratives in last 24 hours
- Narratives are genuinely different
- Need more time for data

**Solution**:
- Wait for more narratives
- Check if narratives exist
- Review sample fingerprints

---

## Rollback Procedure

If backfill causes issues:

### Option 1: Restore from Backup
```bash
mongorestore --uri="$MONGODB_URI" --drop backup_YYYYMMDD/
```

### Option 2: Clear key_actions
```python
# Remove key_actions from all narratives
db.narratives.update_many(
    {},
    {"$unset": {"fingerprint.key_actions": ""}}
)
```

### Option 3: Re-run Backfill
```bash
# Script is idempotent - safe to re-run
python3 scripts/backfill_narrative_actions.py
```

---

## Cost Tracking

### Estimated Costs
- **50 narratives**: ~$0.01
- **500 narratives**: ~$0.05
- **5000 narratives**: ~$0.50

### Actual Cost Calculation
```python
# From backfill logs
total_narratives = 45
cost_per_narrative = 0.0001
total_cost = total_narratives * cost_per_narrative
print(f"Total cost: ${total_cost:.4f}")
```

---

## Next Steps After Success

### Immediate
- [ ] Document results in project notes
- [ ] Share verification output with team
- [ ] Monitor narrative matching for 1 week

### Short-term (1 week)
- [ ] Run verification script weekly
- [ ] Check for reduced duplicates
- [ ] Monitor match rates
- [ ] Adjust threshold if needed

### Long-term (1 month)
- [ ] Evaluate narrative quality
- [ ] Consider threshold tuning
- [ ] Review action extraction quality
- [ ] Plan for ongoing maintenance

---

## Documentation Reference

- **Quick Start**: `BACKFILL_ACTIONS_QUICK_START.md`
- **Complete Guide**: `NARRATIVE_ACTIONS_BACKFILL.md`
- **Implementation**: `BACKFILL_ACTIONS_IMPLEMENTATION.md`
- **Verification**: `VERIFY_MATCHING_FIX.md`
- **Summary**: `BACKFILL_VERIFICATION_SUMMARY.md`
- **This Checklist**: `BACKFILL_CHECKLIST.md`

---

## Sign-off

### Execution Record
- **Date**: _______________
- **Executed by**: _______________
- **Narratives processed**: _______________
- **Success rate**: _______________
- **Match rate improvement**: _______________
- **Issues encountered**: _______________
- **Notes**: _______________

### Verification
- [ ] All steps completed successfully
- [ ] Results documented
- [ ] Team notified
- [ ] Monitoring in place

---

**Status**: Ready for execution ✅
