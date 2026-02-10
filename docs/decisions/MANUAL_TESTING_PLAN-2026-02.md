# Manual Testing Plan - FEATURE-021: Error Handling & Pagination

**Date**: 2026-01-30
**Feature**: Error Handling with Retry + Article Pagination + Skeleton Loaders
**Status**: Ready for Testing
**Build Status**: ✅ Passing

---

## Quick Start

### Prerequisites
1. **Backend API**: Running on `http://localhost:8000`
2. **Frontend UI**: Running on `http://localhost:5173`
3. **Browser DevTools**: Installed and accessible
4. **Network Throttling**: Able to use Chrome DevTools Network tab

### Starting Servers (if not running)

**Terminal 1 - Backend API:**
```bash
poetry run uvicorn src.crypto_news_aggregator.main:app --reload --port 8000
```

**Terminal 2 - Frontend UI:**
```bash
cd context-owl-ui && npm run dev
```

Then navigate to: `http://localhost:5173`

---

## Core Features to Test

### 1️⃣ Pagination - Initial Load
- [ ] Navigate to Narratives page
- [ ] Verify narratives display with article counts
- [ ] Article counts visible and accurate

### 2️⃣ Pagination - Load More
- [ ] Expand a narrative with >20 articles
- [ ] Verify "Load 20 More Articles" button appears
- [ ] Click button and verify new articles load
- [ ] Verify remaining count updates

### 3️⃣ Skeleton Loaders
- [ ] Expand a narrative
- [ ] Verify 5 skeleton placeholders appear while loading
- [ ] Verify skeletons disappear when articles load

### 4️⃣ Error Handling - Network Errors

#### Test 4.1: Offline During Initial Load
1. Open Narratives page (narratives already loaded)
2. Open Chrome DevTools → Network tab
3. Set network to **Offline**
4. Expand a narrative (expand button should be there)
5. **Expected:**
   - ✅ Loading skeletons appear momentarily
   - ✅ Red error box appears below articles
   - ✅ Error message: "Failed to load articles. Please try again."
   - ✅ AlertCircle icon visible in red
   - ✅ "Retry" button visible and clickable

#### Test 4.2: Error Recovery
1. From Test 4.1, with error showing and network **Offline**
2. Set network to **Online**
3. Click "Retry" button
4. **Expected:**
   - ✅ Error message disappears immediately
   - ✅ Skeletons appear while loading
   - ✅ Articles load successfully
   - ✅ Error box gone

#### Test 4.3: Offline During Load More
1. Expand narrative successfully (articles loaded)
2. Set network to **Offline**
3. Click "Load 20 More Articles" button
4. **Expected:**
   - ✅ Loading skeletons appear below existing articles
   - ✅ Red error box appears below skeletons
   - ✅ Original 20 articles still visible (NOT cleared)
   - ✅ Error message: "Failed to load more articles. Please try again."
   - ✅ "Retry" button visible

#### Test 4.4: Error Recovery on Load More
1. From Test 4.3, with error showing
2. Set network to **Online**
3. Click "Retry" button
4. **Expected:**
   - ✅ Error message disappears
   - ✅ Skeletons appear
   - ✅ Next 20 articles load
   - ✅ Now showing 40 total articles
   - ✅ "Load More" button updates remaining count

### 5️⃣ Multiple Narrative Errors

1. Expand 3 narratives simultaneously
2. Set network to **Offline**
3. Try expanding 2 more narratives that haven't been loaded
4. **Expected:**
   - ✅ Each narrative with error shows independent error message
   - ✅ Clicking "Retry" on Narrative A only retries A
   - ✅ Other narratives keep their errors
   - ✅ Each error message is specific to its narrative

### 6️⃣ Dark Mode Testing

1. Switch to dark mode (usually browser setting or app theme toggle)
2. Trigger an error (offline)
3. **Expected:**
   - ✅ Error box has dark red background
   - ✅ Text is light red (readable)
   - ✅ Border is dark red
   - ✅ AlertCircle icon is visible
   - ✅ "Retry" button is styled for dark mode

### 7️⃣ Mobile Responsiveness

1. Open DevTools → Toggle Device Toolbar (Ctrl+Shift+M on Windows/Linux, Cmd+Shift+M on Mac)
2. Test on iPhone 12 (390x844)
3. Expand narrative and trigger error
4. **Expected:**
   - ✅ Error message wraps correctly
   - ✅ AlertCircle icon and text don't overlap
   - ✅ "Retry" button is clickable and properly sized
   - ✅ Load More button is full width and clickable

### 8️⃣ Rapid Retry Attempts

1. Trigger error (offline)
2. Spam click "Retry" button rapidly (5+ times)
3. Set network back **Online**
4. **Expected:**
   - ✅ Only one retry request happens
   - ✅ Button is disabled during loading (can't click multiple times)
   - ✅ Articles load once successfully
   - ✅ No duplicate requests in DevTools Network tab

### 9️⃣ Edge Case: Error on Empty Narrative

1. Find a narrative with 0 articles
2. Trigger offline mode
3. Try to expand it
4. **Expected:**
   - ✅ Error message appears (even though no articles to show)
   - ✅ "Retry" button works
   - ✅ No console errors

### 🔟 Error Message Text

Verify the exact text messages appear (case-sensitive):
- Initial load error: `"Failed to load articles. Please try again."`
- Load more error: `"Failed to load more articles. Please try again."`
- Both should be user-friendly (no technical jargon)

---

## Visual Inspection Checklist

### Error Box Styling (Light Mode)
- [ ] Background color: Light red (`bg-red-50`)
- [ ] Border color: Red (`border-red-200`)
- [ ] Border width: Thin line
- [ ] Text color: Dark red (`text-red-700`)
- [ ] Padding: Balanced (p-3)
- [ ] Rounded corners: Slight (rounded-lg)

### Error Box Styling (Dark Mode)
- [ ] Background: Dark red with opacity (`dark:bg-red-900/20`)
- [ ] Border: Dark red (`dark:border-red-800`)
- [ ] Text: Light red (`dark:text-red-300`)
- [ ] Contrast is sufficient (text readable)

### Icon & Button Layout
- [ ] AlertCircle icon: 4x4 size (w-4 h-4)
- [ ] Icon color matches text (red)
- [ ] Icon aligns with top of text
- [ ] "Retry" button: Right-aligned
- [ ] Button text: "Retry" (underlines on hover)
- [ ] Button doesn't break to new line on mobile

---

## Browser Compatibility

Test in the following browsers:
- [ ] Chrome (latest) - Windows/Mac/Linux
- [ ] Firefox (latest)
- [ ] Safari (latest) - macOS & iOS
- [ ] Edge (latest)
- [ ] Mobile Chrome (Android)
- [ ] Mobile Safari (iOS)

---

## Network Simulation Methods

### Method 1: Chrome DevTools (Recommended)
1. Open DevTools (F12)
2. Network tab
3. Click throttling dropdown (usually shows "No throttling")
4. Select "Offline" to simulate offline
5. Or select "Slow 3G" for timeout testing

### Method 2: Browser Extensions
- **ModHeader** (Chrome) - Simulate error responses
- **Network Throttle Simulator** (Chrome)

### Method 3: Request Blocking
1. DevTools → Network tab
2. Right-click on request
3. Select "Block request URL"
4. This simulates network failure for that endpoint

---

## Console Logging

While testing, check DevTools Console for:

### Expected Messages (DEBUG level):
```
[DEBUG] Fetching initial articles for narrative: [ID]
[DEBUG] Pagination API Response: {articles: [...], ...}
[DEBUG] Loading more articles - offset: 20, narrativeId: [ID]
[DEBUG] Retry initial load for narrative: [ID]
[DEBUG] Retrying load more for narrative: [ID]
```

### Expected Messages (ERROR level):
```
[ERROR] Failed to fetch articles: Error: Failed to load articles...
[ERROR] Failed to load more articles: Error: Failed to load more articles...
[ERROR] Retry failed: Error: ...
```

### No errors should appear:
- No `undefined` reference errors
- No `Cannot read property` errors
- No TypeScript errors

---

## Test Data Requirements

You'll need narratives with varying article counts:
- **Narrative A**: >20 articles (for Load More testing)
- **Narrative B**: <20 articles (for no Load More button)
- **Narrative C**: 0 articles (edge case)
- **Multiple narratives**: For multi-error testing

---

## Signoff Checklist

After completing all tests, verify:

- [ ] ✅ All pagination tests pass
- [ ] ✅ All skeleton loader tests pass
- [ ] ✅ All error handling tests pass
- [ ] ✅ All error recovery tests pass
- [ ] ✅ Dark mode styling correct
- [ ] ✅ Mobile responsive
- [ ] ✅ Multiple narratives work independently
- [ ] ✅ No console errors
- [ ] ✅ No memory leaks observed
- [ ] ✅ Build still passes (`npm run build`)
- [ ] ✅ TypeScript no errors (`tsc -b`)

---

## Issues Found

Document any issues found during testing:

| Issue | Severity | Steps to Reproduce | Expected | Actual | Status |
|-------|----------|-------------------|----------|--------|--------|
| | | | | | |

---

## Notes

- Test on both light and dark mode
- Test on multiple browsers if possible
- Test on mobile devices or mobile emulation
- Verify console logs match expectations
- Check Network tab to confirm only 1 request per action

---

## Next Steps After Testing

1. **If all tests pass:**
   - ✅ Commit changes to `feature/article-pagination` branch
   - ✅ Create Pull Request to `main`
   - ✅ Schedule for deployment

2. **If issues found:**
   - 🔧 Document issue details above
   - 🔧 Review code changes
   - 🔧 Fix and re-test

---

**Tester**: ________________
**Date**: ________________
**Status**: ________________
