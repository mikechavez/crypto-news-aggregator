# Browser Cache Issue - How to Fix

## 🔍 Problem Diagnosis

Your browser has **cached the old JavaScript bundle** that still points to the Railway API. Even though the server is now serving the correct code, your browser is using the old cached version.

**Verification:**
- ✅ Server HTML has `class="dark"` ← Correct
- ✅ `.env` points to `http://localhost:8000` ← Correct  
- ✅ ThemeContext has localStorage code ← Correct
- ❌ Browser is using old cached JavaScript ← **This is the problem**

---

## 🔧 Solution: Clear Browser Cache

### Method 1: Hard Refresh (Fastest)

**Chrome/Edge:**
- Mac: `Cmd + Shift + R`
- Windows/Linux: `Ctrl + Shift + R`

**Firefox:**
- Mac: `Cmd + Shift + R`
- Windows/Linux: `Ctrl + F5`

**Safari:**
- Mac: `Cmd + Option + R`

### Method 2: Clear Cache via DevTools (Most Reliable)

1. **Open DevTools** (F12 or right-click → Inspect)
2. **Right-click the refresh button** (while DevTools is open)
3. Select **"Empty Cache and Hard Reload"**

### Method 3: Manual Cache Clear (Nuclear Option)

**Chrome/Edge:**
1. Open DevTools (F12)
2. Go to **Application** tab
3. Click **Clear storage** (left sidebar)
4. Check all boxes
5. Click **Clear site data**
6. Close and reopen the tab

**Firefox:**
1. Open DevTools (F12)
2. Go to **Storage** tab
3. Right-click **localhost:5173**
4. Select **Delete All**
5. Close and reopen the tab

**Safari:**
1. Safari menu → **Preferences**
2. **Advanced** tab
3. Check "Show Develop menu"
4. **Develop** menu → **Empty Caches**
5. Close and reopen the tab

---

## 🧪 Verification Steps

After clearing cache, verify these in order:

### 1. Check Dark Background
- Open http://localhost:5173/
- **Expected:** Dark background immediately (no white flash)
- **If still white:** Try Method 2 or 3 above

### 2. Check DevTools Console
Open DevTools Console (F12) and look for:
```
VITE_API_URL should show: http://localhost:8000
```

If you see `https://context-owl-production.up.railway.app`, the cache wasn't cleared.

### 3. Check Network Tab
1. Open DevTools → **Network** tab
2. Navigate to Signals page
3. Look for API calls
4. **Expected:** Calls to `localhost:8000`
5. **If wrong:** Calls to `railway.app` = cache not cleared

### 4. Check API Speed
- Click on **Signals** tab
- **Expected:** Loads in <1 second
- **If slow (minutes):** Still using Railway API = cache not cleared

---

## 🚨 If Cache Clearing Doesn't Work

### Option A: Use Incognito/Private Window
1. Open a **new incognito/private window**
2. Go to http://localhost:5173/
3. This bypasses all cache

**Chrome/Edge:** `Cmd/Ctrl + Shift + N`  
**Firefox:** `Cmd/Ctrl + Shift + P`  
**Safari:** `Cmd + Shift + N`

### Option B: Different Browser
Try a different browser you haven't used for this app yet.

### Option C: Clear All Browser Data
**Last resort - will log you out of everything:**

**Chrome/Edge:**
1. Settings → Privacy and security
2. Clear browsing data
3. Select "All time"
4. Check: Cached images and files
5. Clear data

---

## 🎯 Expected Behavior After Cache Clear

### Dark Mode
- ✅ Dark background on page load
- ✅ No white flash
- ✅ Theme toggle button works
- ✅ Theme persists after refresh

### Performance
- ✅ Signals page: <1 second load time
- ✅ Narratives page: <1 second load time
- ✅ Articles page: <1 second load time

### API Calls (Check Network Tab)
- ✅ All calls to `localhost:8000`
- ❌ NO calls to `railway.app`

---

## 🔍 Debug: Check What the Browser Sees

Open DevTools Console and run:

```javascript
// Check API URL
console.log('API URL:', import.meta.env.VITE_API_URL)

// Check if dark class exists
console.log('Has dark class:', document.documentElement.classList.contains('dark'))

// Check localStorage theme
console.log('Stored theme:', localStorage.getItem('theme'))
```

**Expected output:**
```
API URL: http://localhost:8000
Has dark class: true
Stored theme: dark (or null on first load)
```

---

## 📊 Troubleshooting Matrix

| Symptom | Cause | Solution |
|---------|-------|----------|
| White background | Browser cache | Hard refresh (Cmd+Shift+R) |
| Slow API calls | Old JS bundle cached | Clear cache via DevTools |
| Theme toggle broken | Old React code cached | Empty cache and hard reload |
| Still using Railway | Service worker or aggressive cache | Incognito mode |

---

## ✅ Confirmation Checklist

After clearing cache, verify:

- [ ] Dark background appears immediately
- [ ] No white flash on load
- [ ] Theme toggle button switches Sun/Moon
- [ ] Clicking toggle changes background color
- [ ] Signals page loads in <1 second
- [ ] Network tab shows `localhost:8000` calls
- [ ] No calls to `railway.app` in Network tab

---

## 🎬 Quick Video Guide

If you're still stuck, record a quick video showing:
1. Opening DevTools (F12)
2. Going to Network tab
3. Loading the Signals page
4. The API calls being made

This will show exactly which API it's hitting.

---

## 💡 Why This Happened

Vite (the dev server) uses aggressive caching for performance. When you change environment variables, the old JavaScript bundle stays cached in the browser. The server is serving the new code, but your browser hasn't fetched it yet.

**The fix is simple:** Force the browser to fetch fresh code by clearing cache.

---

## 🚀 After Cache is Cleared

Everything should work perfectly:
- Dark mode loads instantly
- Theme toggle works
- All pages load in <1 second
- No more Railway API calls

If you're still having issues after trying all methods above, let me know and I'll investigate further!
