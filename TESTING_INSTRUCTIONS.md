# Manual Testing Instructions - FEATURE-021

**Date**: 2026-01-30
**Sprint**: Sprint 4 (UX Enhancements & Pagination)

---

## 📋 Pre-Testing Checklist

### Before You Start

- [ ] Backend API is running on `http://localhost:8000`
- [ ] Frontend is running on `http://localhost:5173`
- [ ] Both servers are responsive and working
- [ ] Browser DevTools are available (F12)
- [ ] You have at least 2-3 narratives with >20 articles for testing
- [ ] Build passed: `npm run build` in context-owl-ui directory

### Quick Server Start

**If servers are NOT running:**

**Terminal 1 - Backend (port 8000):**
```bash
cd /Users/mc/dev-projects/crypto-news-aggregator
poetry run uvicorn src.crypto_news_aggregator.main:app --reload --port 8000
```

**Terminal 2 - Frontend (port 5173):**
```bash
cd /Users/mc/dev-projects/crypto-news-aggregator/context-owl-ui
npm run dev
```

Then open `http://localhost:5173` in your browser.

---

## 🎯 Testing Priority Tiers

### Tier 1: Critical (Must Test)
These are core features that users will interact with daily:

1. **Pagination Works** - Can expand narratives and load articles
2. **Error Handling** - Network errors show friendly message
3. **Retry Works** - Clicking Retry recovers from errors
4. **Dark Mode** - Error styling works in dark mode
5. **Mobile** - Layout works on mobile devices

### Tier 2: Important (Should Test)
These ensure quality and robustness:

6. **Skeleton Loaders** - Loading placeholders appear
7. **Multiple Errors** - Each narrative tracks errors independently
8. **Data Preservation** - Existing articles don't disappear on error
9. **Button States** - Buttons disable during loading

### Tier 3: Nice to Have (Can Skip)
These are for thorough validation:

10. **Rapid Clicks** - Spam clicking doesn't break anything
11. **Console Logs** - Debug messages are helpful
12. **Browser Compat** - Works in other browsers

---

## 🚀 Quick Test Flow (15 minutes)

If you're short on time, run this quick validation:

### 1. Basic Pagination (2 min)
```
1. Navigate to http://localhost:5173
2. Look for "Active Narratives" heading
3. Find a narrative
4. Click expand button
5. ✅ Verify articles appear
6. If >20 articles exist, verify "Load More" button appears
7. Click "Load More"
8. ✅ Verify new articles load and count increases
```

### 2. Error Handling (5 min)
```
1. Still on Narratives page
2. Open DevTools (F12)
3. Go to Network tab
4. Find the throttling selector (usually top of Network tab)
5. Click it and select "Offline"
6. Expand a NEW narrative (not yet loaded)
7. ✅ Verify red error box appears
8. ✅ Verify "Retry" button is visible
9. Set network back to "Online"
10. Click "Retry"
11. ✅ Verify articles load successfully
12. ✅ Verify error disappeared
```

### 3. Dark Mode & Mobile (3 min)
```
1. Look for theme toggle (usually top-right corner)
2. Switch to dark mode
3. Trigger error again (offline)
4. ✅ Verify error styling works in dark
5. Toggle device toolbar (Cmd+Shift+M)
6. Select iPhone 12 (390x844)
7. ✅ Verify error box and buttons look good on mobile
```

**Total Time: ~15 minutes for core validation**

---

## 📖 Detailed Test Scenarios

### Scenario A: Network Error During Initial Load

**Objective**: Verify app gracefully handles network errors when loading articles

**Steps:**
1. Navigate to Narratives page (articles should already be listed)
2. Open Chrome DevTools (F12)
3. Click on the "Network" tab
4. Find the network throttling dropdown (shows "No throttling" by default)
5. Click it and select **"Offline"**
6. In the app, expand a narrative that hasn't been loaded yet
   - Look for the expand/collapse button with article count
   - Click it to expand

**Expected Behavior:**
- [ ] Loading animation appears (skeleton loaders)
- [ ] After ~2-3 seconds, loading animation disappears
- [ ] A red alert box appears below where articles would be
- [ ] Error message reads: `"Failed to load articles. Please try again."`
- [ ] AlertCircle icon appears in red
- [ ] "Retry" button is visible in the error box
- [ ] Console shows: `[ERROR] Failed to fetch articles: ...`

**If this passes:** ✅ Initial load error handling works

---

### Scenario B: Recover from Network Error

**Objective**: Verify users can recover from errors by retrying

**Prerequisites:** You must have completed Scenario A (error visible)

**Steps:**
1. Network is still "Offline" with error showing
2. Set network back to "Online"
   - Click throttling dropdown again
   - Select "No throttling"
3. Click the "Retry" button in the error box

**Expected Behavior:**
- [ ] Error message immediately disappears
- [ ] Skeleton loaders appear again
- [ ] Articles load successfully
- [ ] Error box is gone
- [ ] Remaining article count shows correctly
- [ ] Console shows: `[DEBUG] Retrying initial load for narrative: [ID]`

**If this passes:** ✅ Error recovery works

---

### Scenario C: Error During "Load More"

**Objective**: Verify error handling preserves existing articles

**Prerequisites:**
- You need a narrative with >20 articles
- Network should be online

**Steps:**
1. Find a narrative with articles (already expanded from previous tests)
2. Look for "Load 20 More Articles" button at the bottom
3. Open DevTools → Network tab
4. Set network to "Offline"
5. Click "Load 20 More Articles" button

**Expected Behavior:**
- [ ] Skeleton loaders appear below existing articles
- [ ] Original articles are still visible (NOT removed)
- [ ] After ~2 seconds, red error box appears
- [ ] Error message reads: `"Failed to load more articles. Please try again."`
- [ ] "Retry" button is visible
- [ ] Console shows: `[ERROR] Failed to load more articles: ...`

**Important Check:**
- [ ] Count the existing articles - they should STILL be there!
- [ ] This proves we don't clear data on error

**If this passes:** ✅ Data preservation works

---

### Scenario D: Recover Load More Error

**Objective**: Verify Load More recovery appends new articles

**Prerequisites:** You must have Scenario C with error showing

**Steps:**
1. Error is showing for "Load More" operation
2. Set network back to "Online"
3. Click "Retry" button

**Expected Behavior:**
- [ ] Error message disappears
- [ ] Skeleton loaders appear
- [ ] New articles load and are added to existing articles
- [ ] Total article count increases (e.g., 20 → 40)
- [ ] "Load More" button updates remaining count
- [ ] Console shows: `[DEBUG] Retrying load more for narrative: [ID]`

**If this passes:** ✅ Pagination recovery works

---

### Scenario E: Multiple Narratives with Errors

**Objective**: Verify each narrative tracks errors independently

**Steps:**
1. Collapse all currently expanded narratives
2. Set network to "Offline"
3. Expand Narrative A
4. Expand Narrative B
5. Expand Narrative C
6. All three should have error messages

**Expected Behavior:**
- [ ] Narrative A shows error
- [ ] Narrative B shows error
- [ ] Narrative C shows error
- [ ] Each error is independent (not affecting others)
- [ ] All show same generic error message

**Now test independent retry:**
1. Set network to "Online"
2. Click "Retry" ONLY on Narrative B
3. Wait for B to load

**Expected Behavior:**
- [ ] Narrative A error persists
- [ ] Narrative B loads articles successfully (error gone)
- [ ] Narrative C error persists
- [ ] Only B was retried (not A or C)

**If this passes:** ✅ Independent error tracking works

---

### Scenario F: Dark Mode Styling

**Objective**: Verify error box looks good in dark mode

**Steps:**
1. Look for theme/dark mode toggle
   - Usually in top navigation bar
   - Look for sun/moon icon
2. Switch to dark mode
3. Trigger an error (set network offline, expand narrative)
4. Examine the error box styling

**Expected Styling (Dark Mode):**
- [ ] Background is dark red with slight transparency
- [ ] Text is light red (very readable, not too dark)
- [ ] Border is dark red
- [ ] AlertCircle icon is light red
- [ ] "Retry" button is light red and underlines on hover
- [ ] Overall contrast is sufficient (WCAG AA at least)

**Expected Styling (Light Mode):**
- [ ] Background is light red (pale)
- [ ] Text is dark red
- [ ] Border is medium red
- [ ] AlertCircle icon is dark red
- [ ] "Retry" button is dark red and underlines on hover

**If this passes:** ✅ Dark mode styling works

---

### Scenario G: Mobile Responsiveness

**Objective**: Verify error handling works on mobile devices

**Steps:**
1. Open DevTools (F12)
2. Click "Toggle device toolbar" button (or Cmd+Shift+M / Ctrl+Shift+M)
3. Select "iPhone 12" from device list (390 × 844)
4. Navigate to narratives
5. Trigger error (offline, expand narrative)

**Expected Behavior (Mobile):**
- [ ] Error box is visible and properly sized
- [ ] Error text wraps correctly (doesn't overflow)
- [ ] AlertCircle icon is visible
- [ ] "Retry" button is visible and clickable
- [ ] No text overlaps or layout issues
- [ ] Error box doesn't hide important content

**Also test:**
- [ ] Expand button is clickable on mobile
- [ ] Articles are readable on mobile
- [ ] "Load More" button is full width
- [ ] Error message is visible without scrolling

**Test other devices:**
- [ ] iPad (768 × 1024)
- [ ] Galaxy S21 (360 × 800)
- [ ] Larger phone (428 × 926)

**If this passes:** ✅ Mobile responsive design works

---

### Scenario H: Skeleton Loaders

**Objective**: Verify loading placeholders appear

**Prerequisites:**
- Network should be "No throttling" (not offline)
- Have at least one narrative not yet loaded

**Steps:**
1. Expand a narrative that hasn't been loaded
2. Watch carefully - skeleton loaders should appear briefly

**Expected Behavior:**
- [ ] ~5 skeleton placeholder lines appear
- [ ] Skeletons have a subtle animation (shimmer/fade)
- [ ] Skeletons disappear when articles load
- [ ] No sudden layout shift when articles replace skeletons

**If you don't see skeletons:**
- Articles might load too fast
- Slow down your connection:
  - DevTools → Network tab
  - Select "Slow 3G" throttling
  - Then expand a narrative
  - Now you should see skeletons longer

**If this passes:** ✅ Skeleton loader UX works

---

### Scenario I: Rapid Button Clicks (Edge Case)

**Objective**: Verify app handles spam clicking gracefully

**Steps:**
1. Expand a narrative successfully (articles loaded)
2. Set network to "Slow 3G"
3. Click "Load More" button
4. Immediately spam click it 5+ times rapidly
5. Stop clicking and wait

**Expected Behavior:**
- [ ] Button is disabled during loading (can't click again)
- [ ] Only ONE request is sent to API (check DevTools)
- [ ] No duplicate articles appear
- [ ] Articles load once
- [ ] Button re-enables after loading completes

**This proves the app prevents duplicate requests.**

**If this passes:** ✅ Button state management works

---

### Scenario J: No Data Loss on Error

**Objective**: Verify articles are never lost due to errors

**Steps:**
1. Expand a narrative successfully (let's say it shows 30 articles)
2. Set network to "Offline"
3. Click "Load More"
4. Error appears

**Critical Check:**
- [ ] Count the visible articles - still 20? (first batch)
- [ ] None were removed
- [ ] Articles appear exactly as before

**This is the most important data preservation check.**

**If this passes:** ✅ Data integrity is preserved

---

## 🔍 Console Logging Verification

While testing, open DevTools Console (F12 → Console tab) and look for:

### ✅ Messages You SHOULD See:
```
[DEBUG] Fetching initial articles for narrative: abc123
[DEBUG] Pagination API Response: {articles: [...], limit: 20, ...}
[DEBUG] Loading more articles - offset: 20, narrativeId: xyz789
[DEBUG] Load more response: 20 new articles
[DEBUG] Retrying initial load for narrative: abc123
[DEBUG] Retrying load more for narrative: xyz789
```

### ❌ Errors You SHOULD NOT See:
```
Cannot read property 'xxx' of undefined
Uncaught TypeError
Uncaught ReferenceError
[object Object]
```

### ✅ Error Messages You SHOULD See (when offline):
```
[ERROR] Failed to fetch articles: Error: Failed to load articles...
[ERROR] Failed to load more articles: Error: Failed to load more articles...
```

---

## 🐛 Common Issues & How to Debug

### Issue 1: Can't Trigger Error

**Problem**: Setting network to "Offline" doesn't trigger error

**Solution:**
1. Make sure you're expanding a narrative that HASN'T been loaded yet
2. Already-loaded narratives won't retry
3. Or try a different approach:
   - DevTools → Network tab
   - Right-click on the API request
   - Select "Block request URL"
   - Then expand the narrative

### Issue 2: Skeleton Loaders Not Visible

**Problem**: Don't see skeleton placeholders when expanding

**Solution:**
1. Articles load too fast
2. Slow down network:
   - DevTools → Network tab → Select "Slow 3G"
   - Then try again

### Issue 3: Error Message Doesn't Appear

**Problem**: Set network to offline but no error shows

**Solution:**
1. Verify you're expanding a NOT-YET-LOADED narrative
2. Wait 3-5 seconds for timeout
3. Check Console for actual error
4. If still no error, the API might have cached response

### Issue 4: Dark Mode Toggle Not Found

**Problem**: Can't find dark mode button

**Solution:**
1. Look for sun/moon icon in top navigation
2. Check theme selector (might be in user menu)
3. If not found in UI, use DevTools:
   - Right-click → Inspect
   - Find `<html>` element
   - Check if it has `dark` class
   - Or open Console and type:
     ```javascript
     document.documentElement.classList.toggle('dark')
     ```

### Issue 5: Button Stuck in Loading State

**Problem**: "Retry" button shows "Loading..." but never finishes

**Solution:**
1. Check if network is actually online
2. Check DevTools Console for errors
3. Try pressing F5 to refresh and test again
4. Reload the page completely

---

## ✅ Signoff Checklist

After completing testing, mark these boxes:

### Pagination Features
- [ ] Articles load when expanding narrative
- [ ] Article count displays correctly
- [ ] "Load More" button appears for >20 articles
- [ ] "Load More" works and appends new articles
- [ ] Remaining count updates correctly

### Error Handling Features
- [ ] Network error shows red alert box
- [ ] Error message is user-friendly (not technical)
- [ ] AlertCircle icon appears
- [ ] "Retry" button is visible and clickable
- [ ] Error appears for both initial load AND "Load More"

### Error Recovery
- [ ] Clicking "Retry" clears error
- [ ] Clicking "Retry" retries the request
- [ ] Articles eventually load on successful retry
- [ ] Load More articles are appended (not replacing)
- [ ] Previous articles never disappear

### Visual & UX
- [ ] Skeleton loaders appear during loading
- [ ] Dark mode error styling looks correct
- [ ] Mobile layout is responsive
- [ ] No overlapping text or layout issues
- [ ] Error box doesn't hide critical content

### Robustness
- [ ] Multiple narratives can error independently
- [ ] Each shows its own error message
- [ ] Button state prevents duplicate requests
- [ ] No console errors or warnings
- [ ] No memory leaks (devtools performance check)

### Browser/Device Compatibility
- [ ] Works in Chrome
- [ ] Works in Firefox (if tested)
- [ ] Works in Safari (if tested)
- [ ] Mobile view is usable (tested at 390x844)
- [ ] Tested on larger mobile screens too

---

## 📝 Documenting Issues

If you find any issues, document them:

```markdown
### Issue: [Brief Title]

**Severity**: Critical / High / Medium / Low

**Steps to Reproduce:**
1.
2.
3.

**Expected Behavior:**


**Actual Behavior:**


**Screenshots:**
[Attach if possible]

**Browser/Device:**
- Browser: Chrome 120
- OS: macOS 14.5
- Device: Desktop / Mobile

**Console Errors:**
[Paste any console errors]

**Notes:**
```

---

## 🎉 Success Criteria

You're done testing when:

1. ✅ All Tier 1 (Critical) tests pass
2. ✅ All Tier 2 (Important) tests pass
3. ✅ Most Tier 3 (Nice to Have) tests pass
4. ✅ No critical bugs found
5. ✅ App is production-ready

---

## 📞 Need Help?

If you get stuck:

1. **Re-read this guide** - Answer is usually here
2. **Check console logs** - They often show the real error
3. **Restart servers** - Sometimes fixes transient issues
4. **Clear browser cache** - Ctrl+Shift+Delete (Chrome)
5. **Ask for help** - Document what you tried

---

## Next Steps After Testing

### If All Tests Pass ✅
```bash
# Commit changes
git add .
git commit -m "feat(ui): add error handling with retry and pagination [FEATURE-021]"

# Create pull request to main
gh pr create --title "feat(ui): error handling and pagination" \
  --body "Implements FEATURE-021, FEATURE-020, and FEATURE-019"
```

### If Issues Found 🐛
1. Document the issue above
2. Review the issue with the team
3. Decide if it blocks deployment
4. Either fix and re-test, or file as follow-up ticket

---

**Good luck with testing! You've got this! 🚀**
