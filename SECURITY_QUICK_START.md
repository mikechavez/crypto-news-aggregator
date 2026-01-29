# 🚨 Security Incident - Quick Start Guide

**CRITICAL:** MongoDB credentials exposed in git. Follow these steps **in order**.

---

## ⚡ 5-Minute Quick Start

### 1️⃣ Rotate MongoDB Password (2 min)
```
1. Go to: https://cloud.mongodb.com/
2. Database Access → Database Users → [your user] → Edit
3. Click "Autogenerate Secure Password" → Copy it
4. Update User
```

### 2️⃣ Update Environment Variables (1 min)
```bash
# Local
nano .env
# Update: MONGODB_URI="mongodb+srv://<username>:<password>@<cluster>..."

# Railway
railway variables set MONGODB_URI="mongodb+srv://<username>:<password>@..."
```

### 3️⃣ Commit Security Fixes (1 min)
```bash
cd /Users/mc/dev-projects/crypto-news-aggregator
git add ARCHIVE_TAB_FIX_SUMMARY.md SECURITY_*.md
git commit -m "security: remove exposed MongoDB credentials"
```

### 4️⃣ Clean Git History (1 min)
```bash
# Install BFG (if needed)
brew install bfg

# Clean history
cd /tmp
git clone --mirror git@github.com:mikechavez/crypto-news-aggregator.git
cd crypto-news-aggregator.git
bfg --replace-text <(echo '[EXPOSED_PASSWORD]==>***REMOVED***')
git reflog expire --expire=now --all && git gc --prune=now --aggressive
```

### 5️⃣ Force Push (30 sec)
```bash
# ⚠️ Notify team first!
git push --force --all
git push --force --tags
```

### 6️⃣ Verify (30 sec)
```bash
# Should return nothing:
git log --all -S "[EXPOSED_PASSWORD]"
```

---

## 📋 What Was Exposed

- **File:** `ARCHIVE_TAB_FIX_SUMMARY.md` line 107
- **Commit:** `d304639`
- **Password:** [REDACTED]
- **Cluster:** [REDACTED]

---

## ✅ What's Been Done

- ✅ Credentials removed from working files
- ✅ Security documentation created
- ✅ Pre-commit hook installed
- ✅ .gitignore verified

---

## ⏳ What You Must Do

- ⏳ **Rotate MongoDB password** (DO FIRST!)
- ⏳ **Update environment variables**
- ⏳ **Rewrite git history**
- ⏳ **Force push to GitHub**
- ⏳ **Monitor MongoDB for 7 days**

---

## 📚 Full Documentation

- **Quick Start:** This file
- **Summary:** `SECURITY_INCIDENT_SUMMARY.md`
- **Detailed Steps:** `SECURITY_REMEDIATION_STEPS.md`
- **Full Report:** `SECURITY_INCIDENT_RESPONSE.md`

---

## 🆘 Emergency Contacts

- MongoDB Atlas: https://cloud.mongodb.com/
- GitHub: https://github.com/mikechavez/crypto-news-aggregator

---

**START HERE:** Rotate MongoDB password NOW → https://cloud.mongodb.com/
