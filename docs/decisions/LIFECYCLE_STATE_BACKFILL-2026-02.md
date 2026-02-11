# Lifecycle State Backfill Implementation

## Overview

Created scripts to backfill the `lifecycle_state` field for 36 narratives that are missing it. The backfill uses the same logic from `narrative_service.py` to calculate the appropriate lifecycle state based on narrative metrics.

## Scripts Created

### 1. `scripts/backfill_lifecycle_state.py`

**Purpose:** Backfill missing `lifecycle_state` and initialize `lifecycle_history` for narratives.

**What it does:**
1. Queries narratives where `lifecycle_state` doesn't exist or is `None`
2. For each narrative, calculates the appropriate state using `determine_lifecycle_state()` based on:
   - `article_count` - Number of articles in the narrative
   - `mention_velocity` - Articles per day rate
   - `first_seen` - When narrative was first detected
   - `last_updated` - When narrative was last updated
3. Initializes `lifecycle_history` array with:
   - `state` - The calculated lifecycle state
   - `timestamp` - Current timestamp
   - `article_count` - Current article count
   - `mention_velocity` - Current velocity
4. Updates each narrative document in MongoDB
5. Provides progress logging and final summary with state distribution

**Lifecycle States:**
- `emerging` - New narratives with < 4 articles
- `rising` - Moderate velocity (≥1.5/day), not yet hot
- `hot` - High activity (≥7 articles or ≥3.0/day velocity)
- `cooling` - No updates in 3-7 days
- `dormant` - No updates in 7+ days
- `echo` - Dormant narrative with light activity (1-3 articles in 24h)
- `reactivated` - Dormant/echo narrative with sustained activity (4+ articles in 48h)

### 2. `scripts/check_lifecycle_state_coverage.py`

**Purpose:** Verify current state before and after backfill.

**What it does:**
1. Counts total narratives in database
2. Counts narratives with vs. without `lifecycle_state`
3. Shows coverage percentage
4. Displays lifecycle state distribution
5. Shows sample narratives missing the field

### 3. `scripts/test_lifecycle_state_backfill.py`

**Purpose:** Test backfill logic without modifying database (dry run).

**What it does:**
1. Fetches up to 10 sample narratives missing `lifecycle_state`
2. Calculates what their lifecycle_state would be
3. Tests lifecycle_history initialization
4. Displays results and state distribution
5. **Does NOT update the database** - safe to run anytime

## Usage

### Step 1: Check Current Coverage

```bash
cd /Users/mc/dev-projects/crypto-news-aggregator
poetry run python scripts/check_lifecycle_state_coverage.py
```

**Expected output:**
```
📊 Total narratives: X
✅ Narratives with lifecycle_state: Y
❌ Narratives missing lifecycle_state: 36
📈 Coverage: Z%

📋 Sample narratives missing lifecycle_state:
  • 'Narrative Title': 5 articles, velocity=1.2, last_updated=...
```

### Step 2: Test Backfill Logic (Optional Dry Run)

```bash
poetry run python scripts/test_lifecycle_state_backfill.py
```

**Expected output:**
```
🔍 Testing lifecycle_state calculation on 10 sample narratives

Sample 1:
  Title: 'Bitcoin ETF Approval Narrative'
  Articles: 12
  Velocity: 3.50 articles/day
  Days since update: 1.2
  → Calculated state: hot
  → History entries: 1
     - state: hot
     - article_count: 12
     - mention_velocity: 3.5

...

TEST SUMMARY
📊 Tested 10 narratives
📈 Calculated State Distribution:
  • hot: 4 narratives
  • emerging: 3 narratives
  • cooling: 2 narratives
  • dormant: 1 narratives
✅ Test completed successfully - no database changes made
```

### Step 3: Run Backfill

```bash
poetry run python scripts/backfill_lifecycle_state.py
```

**Expected output:**
```
📊 Narratives missing lifecycle_state: 36
🔍 Processing 36 narratives...
✅ Progress: 5 narratives updated (5/36 processed)
...
✅ Progress: 36 narratives updated (36/36 processed)

BACKFILL COMPLETE
📊 Total narratives processed: 36
✅ Narratives updated with lifecycle_state: 36
❌ Errors encountered: 0

📈 Lifecycle State Distribution:
  • hot: 15 narratives
  • emerging: 10 narratives
  • cooling: 8 narratives
  • dormant: 3 narratives
```

### Step 4: Verify Results

```bash
poetry run python scripts/check_lifecycle_state_coverage.py
```

**Expected output:**
```
📊 Total narratives: X
✅ Narratives with lifecycle_state: X
❌ Narratives missing lifecycle_state: 0
📈 Coverage: 100.0%
```

## Implementation Details

### Lifecycle State Calculation Logic

The script uses `determine_lifecycle_state()` from `narrative_service.py` which:

1. **Checks recency first:**
   - 7+ days since update → `dormant`
   - 3-7 days since update → `cooling`

2. **Checks for high activity:**
   - ≥7 articles OR ≥3.0/day velocity → `hot`

3. **Checks for rising activity:**
   - ≥1.5/day velocity AND <7 articles → `rising`

4. **Defaults to emerging:**
   - <4 articles → `emerging`

5. **Special states (require previous_state):**
   - `echo` - Dormant with 1-3 articles in 24h
   - `reactivated` - Dormant/echo with 4+ articles in 48h

### Lifecycle History Structure

Each entry in `lifecycle_history` array contains:
```json
{
  "state": "hot",
  "timestamp": "2025-10-16T22:00:00Z",
  "article_count": 12,
  "mention_velocity": 3.5
}
```

### Error Handling

- Handles missing or None timestamps by using current time
- Ensures timezone-aware datetime objects
- Logs errors for individual narratives but continues processing
- Provides detailed error messages and stack traces

## Testing

The backfill script includes:
- Progress logging every 5 narratives
- Debug logging for each narrative update
- Final summary with state distribution
- Error tracking and reporting

## Database Impact

- **Query:** Finds narratives where `lifecycle_state` is missing or None
- **Update:** Sets `lifecycle_state` and `lifecycle_history` fields
- **No data loss:** Only adds fields, doesn't modify existing data
- **Idempotent:** Safe to run multiple times (skips narratives that already have the field)

## Next Steps

After running the backfill:

1. ✅ Verify all narratives have `lifecycle_state`
2. ✅ Check state distribution makes sense
3. ✅ Test API endpoints that use `lifecycle_state`
4. ✅ Monitor narrative lifecycle transitions in production
5. ✅ Consider adding index on `lifecycle_state` for query performance

## Related Files

- `src/crypto_news_aggregator/services/narrative_service.py` - Source of lifecycle logic
- `src/crypto_news_aggregator/db/operations/narratives.py` - Database operations
- `src/crypto_news_aggregator/api/v1/endpoints/narratives.py` - API endpoints using lifecycle_state
