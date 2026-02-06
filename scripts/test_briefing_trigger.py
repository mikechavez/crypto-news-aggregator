#!/usr/bin/env python3
"""
Test script to verify Celery worker and Redis broker connection for briefing generation.

This script:
1. Connects to the Celery app
2. Queues a manual briefing generation task
3. Monitors task status until completion
4. Reports success or failure

Usage:
    # Local development
    python scripts/test_briefing_trigger.py

    # Production (Railway)
    railway run python scripts/test_briefing_trigger.py
"""

import sys
import time
import logging
from datetime import datetime, timezone

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_celery():
    """Initialize Celery app with configuration."""
    from crypto_news_aggregator.tasks import app
    return app

def run_test():
    """Run the briefing generation test."""
    print("=" * 70)
    print("MANUAL BRIEFING GENERATION TEST")
    print("=" * 70)
    print()

    try:
        # Initialize Celery app
        print("📋 Initializing Celery app...")
        celery_app = setup_celery()
        print("✅ Celery app initialized")
        print()

        # Queue the task
        print("📋 Triggering briefing generation task...")
        print("   This will queue the task and return immediately.")
        print()

        task = celery_app.send_task(
            'crypto_news_aggregator.tasks.briefing_tasks.force_generate_briefing',
            kwargs={'briefing_type': 'morning'},
            queue='briefings'
        )

        task_id = task.id
        print(f"✅ Task queued successfully!")
        print(f"   Task ID: {task_id}")
        print()

        # Check initial status
        print("📊 Task Status:")
        print(f"   State: {task.state}")
        print()

        # Wait for task to complete
        print("⏳ Waiting for task to complete...")
        print("   (This may take 30-60 seconds depending on article count)")
        print()

        max_wait = 120  # 2 minutes max wait
        start_time = time.time()
        last_state = None

        while time.time() - start_time < max_wait:
            current_state = task.state

            # Report state changes
            if current_state != last_state:
                elapsed = int(time.time() - start_time)
                print(f"   [{elapsed}s] State: {current_state}")
                last_state = current_state

            # Check if task is done
            if current_state in ['SUCCESS', 'FAILURE']:
                break

            time.sleep(2)

        print()

        # Report result
        if task.state == 'SUCCESS':
            print("=" * 70)
            print("✅ BRIEFING GENERATION COMPLETE!")
            print("=" * 70)
            print()

            result = task.result
            print(f"Result: {result}")
            print()

            if isinstance(result, dict):
                if result.get('status') == 'success':
                    briefing_id = result.get('briefing_id', 'unknown')
                    generated_at = result.get('generated_at', 'unknown')
                    duration = result.get('duration_seconds', 0)

                    print(f"🎉 Success! Briefing generated successfully.")
                    print()
                    print(f"Briefing ID: {briefing_id}")
                    print(f"Generated at: {generated_at}")
                    print(f"Duration: {duration:.1f}s")
                    print()
                    print("Next steps:")
                    print("  1. Check MongoDB for the new briefing document")
                    print("  2. Verify scheduled briefings will run at 8 AM and 8 PM EST")
                    print("  3. Monitor logs for scheduled briefing execution")
                    print()
                    return True

                elif result.get('status') == 'skipped':
                    print(f"⚠️  Briefing skipped: {result.get('reason', 'unknown reason')}")
                    print()
                    print("This usually means a briefing for today already exists.")
                    print("Celery worker and Redis connection are working correctly!")
                    print()
                    return True

            print("⚠️  Task succeeded but result format unexpected")
            print()
            return False

        elif task.state == 'FAILURE':
            print("=" * 70)
            print("❌ TASK FAILED")
            print("=" * 70)
            print()

            exc_info = task.info
            if isinstance(exc_info, Exception):
                print(f"Error: {exc_info}")
            else:
                print(f"Error: {exc_info}")

            print()
            print("Troubleshooting:")
            print("  1. Check that Redis is running")
            print("  2. Check that Celery worker is running")
            print("  3. Check Railway logs for errors")
            print("  4. Verify CELERY_BROKER_URL is set correctly")
            print("  5. Verify MongoDB connection is working")
            print()
            return False

        elif task.state == 'PENDING':
            print("=" * 70)
            print("⏱️  TASK TIMEOUT")
            print("=" * 70)
            print()

            print(f"Task did not complete within {max_wait} seconds")
            print()
            print("Possible causes:")
            print("  1. Celery worker is not running")
            print("  2. Task is taking longer than expected")
            print("  3. Redis connection is slow")
            print("  4. Worker is stuck processing")
            print()
            print("Check Railway logs or worker process status")
            print()
            return False

        else:
            print("=" * 70)
            print("❓ UNKNOWN STATE")
            print("=" * 70)
            print()
            print(f"Task state: {task.state}")
            print(f"Task info: {task.info}")
            print()
            return False

    except ImportError as e:
        print("=" * 70)
        print("❌ IMPORT ERROR")
        print("=" * 70)
        print()
        print(f"Failed to import required modules: {e}")
        print()
        print("Make sure the Celery app is properly configured in:")
        print("  src/crypto_news_aggregator/tasks/celery_app.py")
        print()
        return False

    except ConnectionError as e:
        print("=" * 70)
        print("❌ CONNECTION ERROR")
        print("=" * 70)
        print()
        print(f"Failed to connect to Redis: {e}")
        print()
        print("Troubleshooting:")
        print("  1. Verify Redis is running")
        print("  2. Check CELERY_BROKER_URL environment variable")
        print("  3. Verify network connectivity to Redis server")
        print()
        if "localhost:6379" in str(e).lower():
            print("⚠️  Looks like Redis is trying to connect to localhost:6379")
            print("   In production (Railway), you need to set CELERY_BROKER_URL env var")
            print()
        return False

    except Exception as e:
        print("=" * 70)
        print("❌ UNEXPECTED ERROR")
        print("=" * 70)
        print()
        print(f"Error: {type(e).__name__}: {e}")
        print()
        import traceback
        print("Traceback:")
        print(traceback.format_exc())
        print()
        return False

if __name__ == '__main__':
    success = run_test()
    sys.exit(0 if success else 1)
