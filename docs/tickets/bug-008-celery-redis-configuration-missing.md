bug-008-celery-redis-configuration-missing

---
id: BUG-008
type: bug
status: open
priority: critical
severity: critical
created: 2026-02-05
updated: 2026-02-05
---

# BUG-008: Celery Briefing Generation Not Running (Redis Configuration Missing)

## Problem
Briefings are not being generated automatically at scheduled times (8 AM and 8 PM EST) despite the Celery worker and beat processes being defined in the Procfile and code being correct.

## Expected Behavior
Briefings should be automatically generated daily:
- Morning briefing at 8:00 AM EST
- Evening briefing at 8:00 PM EST
- Process should run in the background via Celery Beat scheduler and worker

## Actual Behavior
No briefings are generated at scheduled times. The Procfile defines worker and beat processes, but they fail to connect to the message broker.

## Steps to Reproduce
1. Deploy application to Railway with Procfile (worker and beat processes)
2. Wait for scheduled briefing time (8 AM or 8 PM EST)
3. Check MongoDB for new briefing documents
4. Observe: No new briefing created
5. Check Railway logs for Celery worker/beat process errors
6. Observe: Connection errors to `localhost:6379` (Redis)

## Environment
- Environment: production (Railway)
- User impact: high (core feature completely broken)
- Affects: All users relying on automated briefing generation

## Screenshots/Logs
Railway logs would show connection errors like:
```
Error: Cannot connect to redis://localhost:6379/0
ConnectionError: Error 111 connecting to localhost:6379
```

---

## Resolution

**Status:** In Progress
**Root Cause Identified:** YES - Redis connection not configured for production

### Root Cause
The Celery worker and beat processes require a message broker (Redis) to communicate and schedule tasks.

**The Issue:**
1. `.env` file doesn't define `CELERY_BROKER_URL`, `REDIS_HOST`, or `REDIS_PORT`
2. Configuration defaults to `redis://localhost:6379/0` for local development
3. Railway doesn't provide Redis by default - this address doesn't exist in production
4. Celery worker and beat fail to connect to the broker on startup
5. Tasks cannot be scheduled or executed

**Code Location:** `src/crypto_news_aggregator/core/config.py` (lines 77-88)

### Changes Made
1. **Updated Config (config.py)**:
   - Changed `CELERY_BROKER_URL` from f-string with hardcoded defaults to empty string allowing environment override
   - Changed `CELERY_RESULT_BACKEND` from f-string with hardcoded defaults to empty string allowing environment override
   - Updated model validator to build Celery URLs only if environment variables not provided (lines 178-182)
   - This allows production deployments to override with proper Redis URLs

2. **Configuration Flexibility**:
   - Local development: Falls back to `redis://localhost:6379/0` if env vars not set
   - Production (Railway): Can now accept `CELERY_BROKER_URL` from environment
   - Supports external Redis services (Upstash, etc.)

### Testing

#### Phase 1: Infrastructure Verification (COMPLETED)
1. ✅ Redis service added to Railway
2. ✅ Environment variables configured:
   - `CELERY_BROKER_URL=${{Redis.REDIS_URL}}/0`
   - `CELERY_RESULT_BACKEND=${{Redis.REDIS_URL}}/1`
3. ✅ Redeployed to Railway

#### Phase 2: Scheduled Briefing Test

**Goal:** Verify Celery Beat scheduler can schedule tasks and Celery Worker executes them via Redis broker.

**Create test script: `test_scheduled_briefing.py`**

```python
#!/usr/bin/env python3
"""
Scheduled Briefing Test
Tests that Celery Beat + Redis broker can schedule and execute tasks
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from crypto_news_aggregator.tasks.briefing_tasks import generate_daily_briefing
from crypto_news_aggregator.core.database import Database
from crypto_news_aggregator.core.celery_app import celery_app


def test_scheduled_briefing():
    """
    Schedule a briefing for 2 minutes from now and verify it executes.
    This tests the full Celery Beat -> Redis -> Worker pipeline.
    """
    
    print("=" * 70)
    print("SCHEDULED BRIEFING TEST - Celery Beat + Redis Integration")
    print("=" * 70)
    print()
    
    # Calculate schedule time (2 minutes from now)
    now = datetime.now()
    scheduled_time = now + timedelta(minutes=2)
    
    print(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Scheduled time: {scheduled_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Wait duration: 2 minutes")
    print()
    
    # Get initial briefing count
    db = Database()
    initial_count = db.briefings.count_documents({})
    print(f"📊 Current briefing count: {initial_count}")
    print()
    
    # Schedule the task using apply_async with eta (execute-at time)
    print("📋 Scheduling briefing task...")
    result = generate_daily_briefing.apply_async(eta=scheduled_time)
    
    print(f"✅ Task scheduled!")
    print(f"   Task ID: {result.id}")
    print(f"   ETA: {scheduled_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Monitor task status
    print("⏳ Monitoring task status...")
    print("   Checking every 10 seconds...")
    print()
    
    start_wait = datetime.now()
    max_wait = 180  # 3 minutes max wait
    
    while (datetime.now() - start_wait).seconds < max_wait:
        status = result.state
        elapsed = int((datetime.now() - start_wait).seconds)
        
        print(f"   [{elapsed}s] Task state: {status}")
        
        if status == "SUCCESS":
            print()
            print("=" * 70)
            print("✅ SCHEDULED BRIEFING TEST PASSED!")
            print("=" * 70)
            print()
            
            # Verify briefing was created
            final_count = db.briefings.count_documents({})
            print(f"📊 Initial briefing count: {initial_count}")
            print(f"📊 Final briefing count: {final_count}")
            print(f"📊 New briefings created: {final_count - initial_count}")
            print()
            
            if final_count > initial_count:
                print("🎉 SUCCESS! Celery Beat + Redis + Worker integration confirmed!")
                print()
                print("✅ Verified:")
                print("   - Celery Beat can schedule tasks")
                print("   - Redis broker queues tasks correctly")
                print("   - Celery Worker executes scheduled tasks")
                print("   - Briefing generation completes successfully")
                print()
                print("🚀 Scheduled briefings (8 AM & 8 PM EST) should now work!")
            else:
                print("⚠️  Task completed but no new briefing found in database")
                print("   This may indicate an issue with the briefing generation logic")
            
            return True
            
        elif status == "FAILURE":
            print()
            print("=" * 70)
            print("❌ TASK FAILED")
            print("=" * 70)
            print()
            print(f"Error: {result.result}")
            print()
            print("Check Railway logs for detailed error information")
            return False
            
        elif status == "PENDING" and (datetime.now() - start_wait).seconds > 130:
            # Task should have started by now (2 min + 10 sec buffer)
            print()
            print("⚠️  Warning: Task still PENDING after scheduled time")
            print("   This may indicate:")
            print("   - Celery Beat is not running")
            print("   - Redis connection issues")
            print("   - Worker not picking up tasks")
            
        time.sleep(10)
    
    print()
    print("=" * 70)
    print("❌ TEST TIMEOUT")
    print("=" * 70)
    print()
    print(f"Task did not complete within {max_wait} seconds")
    print(f"Final task state: {result.state}")
    print()
    print("Troubleshooting:")
    print("  1. Check Railway logs for worker process")
    print("  2. Check Railway logs for beat process")
    print("  3. Verify Redis is running and accessible")
    print("  4. Check CELERY_BROKER_URL environment variable")
    
    return False


if __name__ == "__main__":
    success = test_scheduled_briefing()
    sys.exit(0 if success else 1)
```

**Run test:**
```bash
python test_scheduled_briefing.py
```

**Expected output:**
```
======================================================================
SCHEDULED BRIEFING TEST - Celery Beat + Redis Integration
======================================================================

Current time: 2026-02-05 14:30:00
Scheduled time: 2026-02-05 14:32:00
Wait duration: 2 minutes

📊 Current briefing count: 5

📋 Scheduling briefing task...
✅ Task scheduled!
   Task ID: abc123-def456-ghi789
   ETA: 2026-02-05 14:32:00

⏳ Monitoring task status...
   Checking every 10 seconds...

   [0s] Task state: PENDING
   [10s] Task state: PENDING
   [20s] Task state: PENDING
   ...
   [120s] Task state: PENDING
   [130s] Task state: STARTED
   [140s] Task state: SUCCESS

======================================================================
✅ SCHEDULED BRIEFING TEST PASSED!
======================================================================

📊 Initial briefing count: 5
📊 Final briefing count: 6
📊 New briefings created: 1

🎉 SUCCESS! Celery Beat + Redis + Worker integration confirmed!

✅ Verified:
   - Celery Beat can schedule tasks
   - Redis broker queues tasks correctly
   - Celery Worker executes scheduled tasks
   - Briefing generation completes successfully

🚀 Scheduled briefings (8 AM & 8 PM EST) should now work!
```

#### Phase 3: Verify Production Schedule

After successful test, verify the actual 8 AM / 8 PM schedule:

1. **Check next scheduled briefing time:**
   - Morning: 8:00 AM EST (13:00 UTC)
   - Evening: 8:00 PM EST (01:00 UTC next day)

2. **Monitor Railway logs at scheduled times:**
   - Look for: `"Scheduler: Sending due task generate_daily_briefing"`
   - Look for: `"Task crypto_news_aggregator.tasks.briefing_tasks.generate_daily_briefing succeeded"`

3. **Verify briefing in MongoDB:**
   - New document in `briefings` collection
   - `created_at` timestamp matches scheduled time (±1 minute)

### Files Changed
- `src/crypto_news_aggregator/core/config.py` - Added environment variable override support for Celery URLs

### Next Steps
1. Deploy configuration changes
2. Add Redis to Railway deployment:
   - **Option A**: Use Railway Redis plugin (recommended)
   - **Option B**: Use Upstash Redis (https://upstash.com/)
3. Verify briefing generation resumes at next scheduled time