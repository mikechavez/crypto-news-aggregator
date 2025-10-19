# 🚨 URGENT: Security Remediation Steps

**CRITICAL:** MongoDB credentials were exposed in git history. Follow these steps **immediately**.

---

## ⚡ Quick Action Checklist

- [ ] **STEP 1:** Rotate MongoDB credentials (DO THIS FIRST!)
- [ ] **STEP 2:** Commit the security fixes
- [ ] **STEP 3:** Rewrite git history to remove credentials
- [ ] **STEP 4:** Force push to GitHub (coordinate with team)
- [ ] **STEP 5:** Verify cleanup was successful
- [ ] **STEP 6:** Monitor MongoDB for unauthorized access

---

## STEP 1: Rotate MongoDB Credentials (DO THIS FIRST!) 🔐

**⚠️ CRITICAL: Do this BEFORE rewriting git history!**

### Option A: Change Password (Faster)
1. Go to https://cloud.mongodb.com/
2. Navigate to: **Database Access** → **Database Users**
3. Find user: `observantowl`
4. Click **Edit** → **Edit Password**
5. Click **Autogenerate Secure Password** (or create a strong one)
6. Copy the new password
7. Click **Update User**

### Option B: Create New User (More Secure)
1. Go to https://cloud.mongodb.com/
2. Navigate to: **Database Access** → **Database Users**
3. Click **Add New Database User**
4. Username: `observantowl_v2` (or your choice)
5. Click **Autogenerate Secure Password**
6. Copy the password
7. Set privileges: **Read and write to any database** (or specific to `crypto_news`)
8. Click **Add User**
9. **Delete the old user** `observantowl`

### Update Environment Variables

#### Local Development
```bash
# Edit your .env file (already gitignored)
nano .env

# Update the MONGODB_URI line:
MONGODB_URI="mongodb+srv://observantowl:<NEW_PASSWORD>@cluster0.fkronaj.mongodb.net/?retryWrites=true&w=majority&appName=cluster0"
```

#### Railway Production
```bash
# Option 1: Using Railway CLI
railway variables set MONGODB_URI="mongodb+srv://observantowl:<NEW_PASSWORD>@cluster0.fkronaj.mongodb.net/?retryWrites=true&w=majority&appName=cluster0"

# Option 2: Using Railway Dashboard
# 1. Go to https://railway.app/
# 2. Select your project
# 3. Go to Variables tab
# 4. Update MONGODB_URI
# 5. Redeploy the service
```

#### Vercel (if applicable)
```bash
# Option 1: Using Vercel CLI
vercel env rm MONGODB_URI production
vercel env add MONGODB_URI production
# Paste the new URI when prompted

# Option 2: Using Vercel Dashboard
# 1. Go to https://vercel.com/
# 2. Select your project
# 3. Settings → Environment Variables
# 4. Edit MONGODB_URI
# 5. Redeploy
```

---

## STEP 2: Commit Security Fixes 💾

```bash
cd /Users/mc/dev-projects/crypto-news-aggregator

# Stage the security fixes
git add ARCHIVE_TAB_FIX_SUMMARY.md
git add SECURITY_INCIDENT_RESPONSE.md
git add SECURITY_REMEDIATION_STEPS.md

# Commit with clear message
git commit -m "security: remove exposed MongoDB credentials and add incident response documentation

- Remove hardcoded MongoDB URI from ARCHIVE_TAB_FIX_SUMMARY.md
- Add comprehensive security incident response documentation
- Add pre-commit hook to prevent future credential commits
- Document remediation steps and prevention measures

BREAKING: MongoDB credentials have been rotated
Refs: Security incident on 2025-10-18"
```

---

## STEP 3: Rewrite Git History 🔨

**⚠️ WARNING:** This will rewrite git history. Coordinate with your team first!

### Option A: Using BFG Repo-Cleaner (Recommended)

```bash
# Install BFG (if not already installed)
brew install bfg

# Create a backup
cd /Users/mc/dev-projects
cp -r crypto-news-aggregator crypto-news-aggregator-backup

# Clone a fresh mirror
cd /tmp
git clone --mirror git@github.com:mikechavez/crypto-news-aggregator.git

# Remove the exposed password from ALL commits
cd crypto-news-aggregator.git
bfg --replace-text <(echo 'Jy8ZM_2nf.y2<4VDVD<X==>***REMOVED***')

# Alternative: Remove the entire file from history
# bfg --delete-files ARCHIVE_TAB_FIX_SUMMARY.md

# Clean up
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# Verify the password is gone
git log --all -S "Jy8ZM_2nf.y2<4VDVD<X"
# Should return: nothing

# If clean, proceed to STEP 4
```

### Option B: Using git filter-repo (Alternative)

```bash
# Install git-filter-repo
brew install git-filter-repo

# Create a backup
cd /Users/mc/dev-projects
cp -r crypto-news-aggregator crypto-news-aggregator-backup

cd crypto-news-aggregator

# Remove the file from all history
git filter-repo --path ARCHIVE_TAB_FIX_SUMMARY.md --invert-paths

# Or replace the content
git filter-repo --replace-text <(echo 'Jy8ZM_2nf.y2<4VDVD<X==>***REMOVED***')

# Verify
git log --all -S "Jy8ZM_2nf.y2<4VDVD<X"
# Should return: nothing
```

### Option C: Using git filter-branch (Fallback)

```bash
cd /Users/mc/dev-projects/crypto-news-aggregator

# Create a backup
cd ..
cp -r crypto-news-aggregator crypto-news-aggregator-backup
cd crypto-news-aggregator

# Remove the file from all commits
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch ARCHIVE_TAB_FIX_SUMMARY.md" \
  --prune-empty --tag-name-filter cat -- --all

# Clean up
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# Verify
git log --all --full-history -- ARCHIVE_TAB_FIX_SUMMARY.md
# Should return: nothing or only new commits
```

---

## STEP 4: Force Push to GitHub 🚀

**⚠️ CRITICAL:** Notify your team before doing this!

```bash
cd /Users/mc/dev-projects/crypto-news-aggregator

# If using BFG (from /tmp/crypto-news-aggregator.git)
cd /tmp/crypto-news-aggregator.git
git push --force --all
git push --force --tags

# Return to your working directory
cd /Users/mc/dev-projects/crypto-news-aggregator
git fetch origin
git reset --hard origin/fix/nucleus-entity-missing-field

# If using filter-repo or filter-branch (from your working directory)
git push origin --force --all
git push origin --force --tags
```

### Team Notification Template

Send this to your team **before** force pushing:

```
🚨 URGENT: Git History Rewrite Required

I need to force-push to remove accidentally committed MongoDB credentials.

WHAT: Rewriting git history to remove exposed secrets
WHEN: [Current time] - will take ~5 minutes
IMPACT: All team members must re-clone or reset their local repos

WHAT YOU NEED TO DO:
1. Commit and push any pending work NOW
2. After I confirm the push is complete:
   - Delete your local repo
   - Fresh clone: git clone git@github.com:mikechavez/crypto-news-aggregator.git
   OR
   - Reset: git fetch origin && git reset --hard origin/main

AFFECTED BRANCHES: All branches (especially fix/nucleus-entity-missing-field)

I'll notify when complete. Questions? Reply immediately.
```

---

## STEP 5: Verify Cleanup ✅

```bash
cd /Users/mc/dev-projects/crypto-news-aggregator

# 1. Search for the exposed password
git log --all --full-history -S "Jy8ZM_2nf.y2<4VDVD<X"
# Expected: No results

# 2. Search for the connection string pattern
git log --all --full-history -S "mongodb+srv://observantowl"
# Expected: No results with credentials

# 3. Check GitHub
# Go to: https://github.com/mikechavez/crypto-news-aggregator
# Search: "Jy8ZM_2nf.y2<4VDVD<X"
# Expected: 0 results

# 4. Verify current files are clean
grep -r "Jy8ZM_2nf.y2<4VDVD<X" .
# Expected: No results

# 5. Test the pre-commit hook
echo 'mongodb+srv://user:password@cluster.net' > test_secret.txt
git add test_secret.txt
git commit -m "test"
# Expected: Commit blocked by pre-commit hook
git reset HEAD test_secret.txt
rm test_secret.txt
```

---

## STEP 6: Monitor MongoDB Access 📊

### Check MongoDB Atlas Logs

1. Go to https://cloud.mongodb.com/
2. Navigate to your cluster
3. Click **Metrics** tab
4. Check **Connections** graph for unusual spikes
5. Go to **Activity Feed** (if available)
6. Look for:
   - ❌ Failed authentication attempts
   - ❌ Connections from unknown IPs
   - ❌ Unusual query patterns
   - ❌ New collections created
   - ❌ Data modifications you didn't make

### Set Up Alerts (Recommended)

1. In MongoDB Atlas: **Alerts** → **Alert Settings**
2. Enable alerts for:
   - Failed authentication attempts
   - Unusual connection patterns
   - High query rates
   - Data modifications

### If You Find Suspicious Activity

1. **Immediately disable the compromised user**
2. **Create a new user with a different name**
3. **Review all database changes** since Oct 18, 2025
4. **Consider restoring from backup** if data was modified
5. **Report the incident** to your security team

---

## Prevention Measures Implemented ✅

### 1. Pre-commit Hook
- ✅ Installed at `.git/hooks/pre-commit`
- ✅ Blocks commits with MongoDB URIs containing credentials
- ✅ Warns about potential secrets
- ✅ Prevents .env files from being committed

### 2. .gitignore Protection
- ✅ `.env` files already ignored
- ✅ `config.ini` already ignored
- ✅ All environment files protected

### 3. Documentation
- ✅ `SECURITY_INCIDENT_RESPONSE.md` - Full incident report
- ✅ `SECURITY_REMEDIATION_STEPS.md` - This file
- ✅ Updated `ARCHIVE_TAB_FIX_SUMMARY.md` - Removed credentials

---

## Additional Recommendations 🛡️

### Install git-secrets (Highly Recommended)

```bash
# Install
brew install git-secrets

# Set up for this repo
cd /Users/mc/dev-projects/crypto-news-aggregator
git secrets --install
git secrets --register-aws

# Add custom patterns
git secrets --add 'mongodb(\+srv)?://[^:]+:[^@]+@'
git secrets --add 'password.*=.*["\'][^"\']{10,}'
git secrets --add 'api[_-]?key.*=.*["\'][^"\']{20,}'

# Scan existing history (after cleanup)
git secrets --scan-history
```

### GitHub Secret Scanning

1. Go to: https://github.com/mikechavez/crypto-news-aggregator/settings/security_analysis
2. Enable **Secret scanning**
3. Enable **Push protection** (prevents pushes with secrets)

### CI/CD Secret Scanning

Add to `.github/workflows/security-scan.yml`:
```yaml
name: Security Scan
on: [push, pull_request]
jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0
      - name: Run Gitleaks
        uses: gitleaks/gitleaks-action@v2
```

---

## Timeline

| Step | Status | Time |
|------|--------|------|
| Credentials exposed | ❌ Incident | Oct 18, 2025 18:55 |
| Incident discovered | ✅ Complete | Oct 18, 2025 19:24 |
| Credentials removed from files | ✅ Complete | Oct 18, 2025 19:30 |
| Security docs created | ✅ Complete | Oct 18, 2025 19:35 |
| Pre-commit hook installed | ✅ Complete | Oct 18, 2025 19:36 |
| **MongoDB credentials rotated** | ⏳ **PENDING** | **DO NOW** |
| **Git history rewritten** | ⏳ **PENDING** | **DO NEXT** |
| **Force push to GitHub** | ⏳ **PENDING** | **DO AFTER** |
| Verify cleanup | ⏳ Pending | After push |
| Monitor database access | ⏳ Ongoing | Next 7 days |

---

## Questions?

- **What if I can't access MongoDB Atlas?** Contact your database admin immediately
- **What if team members have uncommitted work?** Wait for them to push before force-pushing
- **What if the force push fails?** Check your GitHub permissions and try again
- **What if I find suspicious database activity?** Disable the user immediately and contact security

---

## Support

- MongoDB Atlas Support: https://www.mongodb.com/cloud/atlas/support
- GitHub Support: https://support.github.com/
- Security Issues: [Your security team contact]

---

**Last Updated:** October 18, 2025 19:36  
**Status:** Awaiting credential rotation and history cleanup
