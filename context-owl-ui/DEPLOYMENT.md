# Context Owl UI - Vercel Deployment Guide

## Production URL
**Production**: `https://context-owl-5zwt1nrjk-mikes-projects-92d90cb6.vercel.app`

**Note**: Vercel may also assign a simpler URL like `context-owl-ui.vercel.app`. Check your Vercel dashboard for all assigned domains.

## Prerequisites

1. **Vercel CLI installed** (already done):
   ```bash
   npm install -g vercel
   ```

2. **Environment Variables Required**:
   - `VITE_API_URL`: Backend API URL (Railway production)
   - `VITE_API_KEY`: API authentication key

## Deployment Steps

### 1. Login to Vercel
```bash
cd context-owl-ui
vercel login
```
This will open a browser window for authentication. Follow the prompts to login with your Vercel account.

### 2. Initial Deployment
```bash
vercel
```

When prompted:
- **Set up and deploy**: `Yes`
- **Link to existing project**: `No` (create new)
- **Project name**: `context-owl-ui`
- **Directory**: `./` (current directory - just press Enter)
- **Override settings**: `No`

This will create a preview deployment and set up the project.

### 3. Configure Environment Variables

Add the required environment variables to Vercel:

```bash
# Add API URL
vercel env add VITE_API_URL
```
When prompted:
- Value: `https://context-owl-production.up.railway.app`
- Select environments: `Production`, `Preview`, `Development` (use spacebar to select all)

```bash
# Add API Key
vercel env add VITE_API_KEY
```
When prompted:
- Value: `[Your API key from Railway backend .env]`
- Select environments: `Production`, `Preview`, `Development` (use spacebar to select all)

### 4. Deploy to Production
```bash
vercel --prod
```

This will create a production deployment with your environment variables.

### 5. Note Your Production URL

After deployment completes, Vercel will display your production URL. It will be something like:
- `https://context-owl-ui.vercel.app`
- Or a custom domain if configured

**Update this document with your actual production URL.**

## Post-Deployment Verification

### Test the Deployment

1. **Open the production URL** in your browser
2. **Check Signals page**: Should load with data from Railway backend
3. **Check Narratives page**: Should display narrative clusters
4. **Check browser console**: Should have no CORS errors
5. **Verify API calls**: Open Network tab and verify requests to Railway backend succeed

### CORS Configuration

The backend is already configured to allow requests from `https://context-owl-ui.vercel.app`.

If you get a different Vercel URL, update the CORS configuration in:
`src/crypto_news_aggregator/main.py` (lines 149-154)

Add your actual Vercel URL to the `origins` list:
```python
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://context-owl-ui.vercel.app",  # Default Vercel URL
    "https://your-actual-url.vercel.app",  # Your actual URL if different
    "*"
]
```

Then redeploy the backend to Railway.

## Updating the Deployment

### Deploy New Changes
```bash
# Make your changes, then:
vercel --prod
```

### Update Environment Variables
```bash
# Remove old variable
vercel env rm VITE_API_URL

# Add new value
vercel env add VITE_API_URL
```

### View Deployment Logs
```bash
vercel logs [deployment-url]
```

## Troubleshooting

### Build Failures

**Issue**: Build fails during deployment
**Solution**: 
1. Test build locally: `npm run build`
2. Check for TypeScript errors: `npm run lint`
3. Verify all dependencies are in `package.json`

### CORS Errors

**Issue**: Browser console shows CORS errors
**Solution**:
1. Verify your Vercel URL is in the backend CORS origins
2. Check that API requests use HTTPS (not HTTP)
3. Verify `X-API-Key` header is being sent

### Environment Variables Not Loading

**Issue**: App shows "Missing environment variables" error
**Solution**:
1. Verify variables are set in Vercel dashboard
2. Ensure variables are set for "Production" environment
3. Redeploy after adding variables: `vercel --prod`

### API Authentication Errors

**Issue**: 401 or 403 errors from API
**Solution**:
1. Verify `VITE_API_KEY` matches the backend API key
2. Check Railway backend logs for authentication errors
3. Ensure API key is not expired or revoked

## Vercel Dashboard

Access your deployment dashboard at:
https://vercel.com/dashboard

From there you can:
- View deployment history
- Monitor performance
- Configure custom domains
- Manage environment variables
- View deployment logs

## Rollback

If a deployment has issues, rollback to a previous version:

1. Go to Vercel dashboard
2. Select your project
3. Go to "Deployments" tab
4. Find a working deployment
5. Click "..." menu → "Promote to Production"

## Custom Domain (Optional)

To add a custom domain:

1. Go to Vercel dashboard → Your project → Settings → Domains
2. Add your domain
3. Configure DNS records as instructed by Vercel
4. Update backend CORS to include your custom domain

## Performance Monitoring

Vercel provides built-in analytics:
- Real User Monitoring (RUM)
- Web Vitals tracking
- Deployment performance metrics

Access at: https://vercel.com/[your-username]/context-owl-ui/analytics

## Security Notes

1. **Never commit `.env` files** - they are gitignored
2. **API keys are sensitive** - only add via Vercel CLI or dashboard
3. **HTTPS only** - Vercel enforces HTTPS for all deployments
4. **Environment variables** - are encrypted at rest in Vercel

## Support

- Vercel Documentation: https://vercel.com/docs
- Vercel CLI Reference: https://vercel.com/docs/cli
- Community Support: https://github.com/vercel/vercel/discussions
