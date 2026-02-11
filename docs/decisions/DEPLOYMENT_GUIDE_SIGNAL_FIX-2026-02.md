# Deployment Guide: Entity Normalization Signal Fix

## Quick Summary

**Problem:** UI shows duplicate entities ("$DOGE" and "Dogecoin" as separate signals)  
**Root Cause:** Signal calculation wasn't normalizing entity names before grouping  
**Solution:** Normalize entities in worker.py before calculating signal scores  

---

## Pre-Deployment Checklist

- [x] Feature branch created and pushed
- [x] Code changes committed
- [x] Tests passing (5/5)
- [x] Migration script created
- [x] Verification script created
- [x] PR documentation written
- [ ] PR created and reviewed
- [ ] Merged to main

---

## Deployment Steps

### Step 1: Merge PR to Main

```bash
# Create PR on GitHub
gh pr create --title "Fix: Entity normalization in signal calculation" \
  --body-file PR_ENTITY_NORMALIZATION_SIGNAL_FIX.md

# After review, merge to main
gh pr merge --squash
```

### Step 2: Verify Railway Deployment

Railway auto-deploys from main branch. Monitor the deployment:

```bash
# Check Railway logs
railway logs --tail

# Look for these success indicators:
# - "Starting background worker process"
# - "Signal score update task created"
# - No import errors or crashes
```

### Step 3: Run Migration Script (CRITICAL)

The code fix prevents NEW duplicates, but old duplicates still exist in the database. The migration script cleans them up.

```bash
# Option A: Run via Railway CLI (recommended)
railway run python scripts/migrate_signal_scores_normalization.py --production

# Option B: SSH into Railway container
railway shell
python scripts/migrate_signal_scores_normalization.py --production
```

**Expected output:**
```
[STEP 1] Verifying entity_mentions normalization...
✓ Entity mentions appear to be normalized correctly

[STEP 2] Clearing existing signal scores...
✓ Deleted 47 signal scores

[STEP 3] Recalculating signal scores with normalization...
Progress: 10/23 entities scored
Progress: 20/23 entities scored
✓ Signal recalculation complete: 23 processed, 0 errors

✓ Migration completed successfully!
```

### Step 4: Wait for Signal Worker Cycle

The signal worker runs every 2 minutes. Wait at least 2 minutes after migration for fresh scores.

```bash
# Monitor Railway logs for signal updates
railway logs --tail | grep "Signal scores updated"

# You should see:
# "Signal scores updated: X entities scored, top entity: Dogecoin (score Y)"
```

### Step 5: Verify in Production UI

1. Open https://context-owl.vercel.app
2. Check the "Top Signals" section
3. **Verify:** "$DOGE" and "Dogecoin" appear as ONE entity (not two)
4. **Verify:** "$BTC" and "Bitcoin" appear as ONE entity (not two)

### Step 6: Run Verification Script

```bash
# Run verification to confirm everything is working
railway run python scripts/verify_signal_normalization.py

# Expected output:
# ✅ No duplicate signals found - normalization is working!
# ✅ Entity mentions are properly normalized
# ✅ All checks passed!
```

---

## Verification Commands

### Check for Duplicate Signals
```bash
railway run python scripts/verify_signal_normalization.py
```

### Check Railway Logs for Normalization
```bash
railway logs --tail | grep "normalized"

# Should see messages like:
# "Signal calculation: normalized '$DOGE' -> 'Dogecoin'"
```

### Query MongoDB Directly (if needed)
```bash
railway shell

# Count signal scores
python -c "
import asyncio
from crypto_news_aggregator.db.mongodb import mongo_manager

async def check():
    db = await mongo_manager.get_async_database()
    count = await db.signal_scores.count_documents({})
    print(f'Total signal scores: {count}')
    
    # Check for specific entities
    doge = await db.signal_scores.find_one({'entity': 'Dogecoin'})
    doge_ticker = await db.signal_scores.find_one({'entity': '\$DOGE'})
    
    print(f'Dogecoin signal: {doge is not None}')
    print(f'\$DOGE signal: {doge_ticker is not None}')
    
    if doge_ticker:
        print('❌ DUPLICATE FOUND: \$DOGE should not exist')
    else:
        print('✅ No duplicate: Only canonical name exists')
    
    await mongo_manager.close()

asyncio.run(check())
"
```

---

## Rollback Plan

If issues occur:

### Immediate Rollback (Code)
```bash
# Revert the merge commit on main
git revert HEAD
git push origin main

# Railway will auto-deploy the previous version
```

### Database Rollback (if needed)
The migration script is safe because:
1. It only deletes signal_scores (which regenerate automatically)
2. It doesn't modify entity_mentions
3. Signal worker will recalculate scores within 2 minutes

**No manual database rollback needed** - just revert the code and wait for signal worker to run.

---

## Troubleshooting

### Issue: Still seeing duplicates in UI after deployment

**Check 1:** Did you run the migration script?
```bash
railway run python scripts/migrate_signal_scores_normalization.py --production
```

**Check 2:** Has the signal worker run since migration?
```bash
railway logs | grep "Signal scores updated"
# Should show recent timestamp (< 2 minutes ago)
```

**Check 3:** Is the UI caching old data?
- Hard refresh the UI (Cmd+Shift+R)
- Check browser console for API errors
- Verify API endpoint returns correct data: `curl https://your-api.railway.app/api/v1/signals`

### Issue: Migration script fails

**Error: "Entity mentions are not properly normalized"**
```bash
# Run entity mention migration first
railway run python scripts/migrate_entity_normalization.py
# Then retry signal migration
railway run python scripts/migrate_signal_scores_normalization.py --production
```

**Error: "MongoDB connection failed"**
```bash
# Check Railway environment variables
railway variables

# Ensure MONGODB_URI is set correctly
```

### Issue: Signal scores not regenerating

**Check worker is running:**
```bash
railway logs | grep "background worker"
# Should see: "Starting background worker process"
```

**Check for errors:**
```bash
railway logs | grep -i error
```

---

## Success Criteria

✅ **Code deployed:** Railway shows successful deployment  
✅ **Migration complete:** Script reports "Migration completed successfully"  
✅ **No duplicates in DB:** Verification script passes all checks  
✅ **UI shows merged entities:** "$DOGE" and "Dogecoin" appear as ONE entity  
✅ **Logs show normalization:** Railway logs contain "normalized" messages  
✅ **Signal worker running:** Logs show "Signal scores updated" every 2 minutes  

---

## Post-Deployment Monitoring

Monitor for 24 hours after deployment:

1. **Check UI daily:** Verify no new duplicates appear
2. **Monitor Railway logs:** Look for normalization messages
3. **Check signal counts:** Should remain stable (no exponential growth)
4. **Verify user reports:** Confirm users see merged entities

---

## Contact

If issues persist after following this guide:
- Check Railway logs for detailed error messages
- Run verification script for diagnostic output
- Review PR documentation for additional context
