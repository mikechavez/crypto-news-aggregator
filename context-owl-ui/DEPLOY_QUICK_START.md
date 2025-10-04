# Quick Deployment Commands

## One-Time Setup

```bash
# 1. Login to Vercel (opens browser)
vercel login

# 2. Initial deployment (creates project)
vercel

# 3. Add environment variables
vercel env add VITE_API_URL
# Enter: https://context-owl-production.up.railway.app
# Select: Production, Preview, Development (spacebar to select)

vercel env add VITE_API_KEY
# Enter: [Your API key from Railway]
# Select: Production, Preview, Development

# 4. Deploy to production
vercel --prod
```

## Future Deployments

```bash
# Just run this after making changes:
vercel --prod
```

## Verification Checklist

After deployment:
- [ ] Open production URL in browser
- [ ] Check Signals page loads
- [ ] Check Narratives page loads
- [ ] Verify data displays correctly
- [ ] Check browser console for errors
- [ ] Test on mobile viewport

## Get Your Production URL

After running `vercel --prod`, the CLI will output:
```
✅  Production: https://context-owl-ui-[hash].vercel.app [copied to clipboard]
```

**Important**: If your URL is different from `https://context-owl-ui.vercel.app`, you'll need to update the backend CORS configuration in `src/crypto_news_aggregator/main.py`.

## Common Issues

**CORS Error**: Add your Vercel URL to backend CORS origins
**401/403 Error**: Check API key matches backend
**Build Error**: Run `npm run build` locally first
**Env Vars Not Loading**: Redeploy after adding variables
