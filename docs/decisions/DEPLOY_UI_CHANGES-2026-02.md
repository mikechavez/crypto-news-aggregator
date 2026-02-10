# Deploy UI Changes to Vercel

## Current Status

- **Current Branch**: `feature/multi-timeframe-signals`
- **UI Changes**: Multi-timeframe tab navigation in Signals page
- **Vercel Production URL**: https://context-owl-5zwt1nrjk-mikes-projects-92d90cb6.vercel.app

## UI Changes to Deploy

1. **Signals.tsx**: Added 24h/7d/30d tab navigation
2. **types/index.ts**: Added timeframe type definitions

## Deployment Options

### Option 1: Deploy from Feature Branch (Quick Preview)

Deploy the current feature branch directly to Vercel for testing:

```bash
cd context-owl-ui
vercel --prod
```

**Pros**: 
- Quick deployment for testing
- No need to merge first

**Cons**: 
- Bypasses PR review process
- Not following development practices rules

### Option 2: Merge to Main First (Recommended)

Follow proper workflow per development practices:

#### Step 1: Create PR and Merge
```bash
# Ensure you're on the feature branch
git checkout feature/multi-timeframe-signals

# Add the backfill scripts
git add scripts/backfill_signal_scores.py
git add scripts/verify_backfill.py
git add SIGNAL_SCORES_BACKFILL.md

# Commit
git commit -m "feat: add signal scores backfill scripts and documentation"

# Push to GitHub
git push origin feature/multi-timeframe-signals

# Create PR on GitHub
# https://github.com/mikechavez/crypto-news-aggregator/compare/feature/multi-timeframe-signals
```

#### Step 2: After PR is Merged
```bash
# Switch to main and pull
git checkout main
git pull origin main

# Deploy UI to Vercel
cd context-owl-ui
vercel --prod
```

## Vercel Deployment Process

### What Happens During Deployment

1. **Build Phase**:
   - Runs `npm run build` in `context-owl-ui/`
   - Compiles TypeScript and React components
   - Bundles with Vite
   - Outputs to `dist/` directory

2. **Environment Variables** (already configured):
   - `VITE_API_URL`: https://context-owl-production.up.railway.app
   - `VITE_API_KEY`: [configured]

3. **Deployment**:
   - Uploads `dist/` to Vercel CDN
   - Updates production URL
   - Takes ~1-2 minutes

### Deployment Command Breakdown

```bash
cd context-owl-ui          # Navigate to UI directory
vercel --prod              # Deploy to production
```

When you run `vercel --prod`:
- ✓ Builds the project
- ✓ Uses production environment variables
- ✓ Deploys to production URL
- ✓ Shows deployment URL when complete

## Post-Deployment Verification

After deploying, verify the changes:

### 1. Check Deployment Success
```bash
# Vercel will output the deployment URL
# Example: ✅ Production: https://context-owl-5zwt1nrjk-mikes-projects-92d90cb6.vercel.app
```

### 2. Test in Browser

Open the production URL and verify:

- [ ] **Signals page loads** without errors
- [ ] **Three tabs visible**: 24h, 7d, 30d
- [ ] **Tab switching works** smoothly
- [ ] **Each tab shows different signals** (20-30 per tab)
- [ ] **No console errors** (F12 → Console)
- [ ] **API calls succeed** (F12 → Network tab)

### 3. Test on Mobile
- [ ] Open on mobile device or use Chrome DevTools (F12 → Toggle device toolbar)
- [ ] Set viewport to 375px width
- [ ] Verify tabs are responsive
- [ ] Verify signals display correctly

### 4. Check Backend Logs

Ensure backend is handling requests:
```bash
# Check Railway logs for any errors
# Look for successful API calls from Vercel URL
```

## Troubleshooting

### Build Fails

**Error**: Build fails during deployment

**Solution**:
```bash
# Test build locally first
cd context-owl-ui
npm run build

# If it fails locally, fix errors then redeploy
```

### Changes Not Showing

**Error**: Deployed but changes not visible

**Solutions**:
1. **Hard refresh**: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)
2. **Clear cache**: Browser settings → Clear browsing data
3. **Check deployment**: Verify correct commit was deployed in Vercel dashboard

### CORS Errors

**Error**: CORS errors in browser console

**Solution**:
- Backend already has Vercel URL in CORS origins
- If still failing, check Railway backend is running
- Verify `VITE_API_URL` is correct in Vercel env vars

### API Authentication Errors

**Error**: 401 or 403 errors

**Solution**:
```bash
# Verify API key is set correctly
vercel env ls

# If needed, update it
vercel env rm VITE_API_KEY
vercel env add VITE_API_KEY
# Then redeploy
vercel --prod
```

## Rollback

If deployment has issues:

### Option 1: Rollback via Vercel Dashboard
1. Go to https://vercel.com/dashboard
2. Select `context-owl-ui` project
3. Go to "Deployments" tab
4. Find previous working deployment
5. Click "..." → "Promote to Production"

### Option 2: Rollback via CLI
```bash
cd context-owl-ui
vercel rollback
```

## Monitoring

### View Deployment Logs
```bash
vercel logs https://context-owl-5zwt1nrjk-mikes-projects-92d90cb6.vercel.app
```

### Vercel Dashboard
- **URL**: https://vercel.com/dashboard
- **View**: Deployment history, performance metrics, logs
- **Monitor**: Real-time analytics and errors

## Summary

### Recommended Workflow

1. ✅ **Backfill scripts created** (done)
2. ⏳ **Commit and push** backfill scripts
3. ⏳ **Create PR** for `feature/multi-timeframe-signals`
4. ⏳ **Review and merge** PR to main
5. ⏳ **Deploy to Vercel** from main branch
6. ⏳ **Verify deployment** using checklist above

### Quick Deploy (if urgent)

If you need to deploy immediately without waiting for PR:

```bash
cd context-owl-ui
vercel --prod
```

This deploys the current feature branch directly to production. However, you should still create and merge the PR afterward to keep main branch in sync.

## Related Documentation

- **Full Deployment Guide**: `context-owl-ui/DEPLOYMENT.md`
- **Vercel Setup**: `VERCEL_DEPLOYMENT_SUMMARY.md`
- **Development Practices**: `.windsurf/rules/development-practices.md`
