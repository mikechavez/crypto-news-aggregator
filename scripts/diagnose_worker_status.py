#!/usr/bin/env python3
"""
Comprehensive diagnostic script to check Celery worker status and task queue.

This script:
1. Verifies Celery app initialization
2. Checks Redis connection
3. Lists registered tasks
4. Checks for queued tasks
5. Attempts to queue a test task
6. Monitors queue status
"""

import sys
import json
import time
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def diagnose():
    """Run full diagnostic."""
    print("=" * 70)
    print("CELERY WORKER & REDIS DIAGNOSTIC")
    print("=" * 70)
    print()

    try:
        # 1. Check Celery app
        print("1️⃣  Checking Celery app initialization...")
        from crypto_news_aggregator.tasks import app
        print("   ✅ Celery app imported successfully")
        print()

        # 2. Check Redis connection
        print("2️⃣  Checking Redis connection...")
        from redis import Redis
        from crypto_news_aggregator.config import get_settings

        settings = get_settings()
        broker_url = settings.celery_broker_url
        print(f"   Broker URL: {broker_url}")

        # Parse Redis URL
        if "redis://" in broker_url:
            redis_url = broker_url.replace("redis://", "")
            if "@" in redis_url:
                host_port = redis_url.split("@")[1]
            else:
                host_port = redis_url
            host, port = host_port.rsplit(":", 1)
            db = redis_url.split("/")[-1] if "/" in redis_url else "0"

            print(f"   Connecting to: {host}:{port} (db={db})")

            redis_conn = Redis(
                host=host,
                port=int(port),
                db=int(db),
                decode_responses=True
            )
            ping = redis_conn.ping()
            print(f"   ✅ Redis ping: {ping}")
        else:
            print(f"   ⚠️  Unexpected broker URL format: {broker_url}")
        print()

        # 3. List registered tasks
        print("3️⃣  Registered tasks in Celery app:")
        tasks = sorted(app.tasks.keys())
        briefing_tasks = [t for t in tasks if 'briefing' in t.lower()]
        print(f"   Total: {len(tasks)} tasks")
        print(f"   Briefing tasks ({len(briefing_tasks)}):")
        for t in briefing_tasks:
            print(f"     - {t}")
        print()

        # 4. Check active queues
        print("4️⃣  Checking active queues...")
        try:
            # List all keys in Redis that look like queues
            all_keys = redis_conn.keys('*')
            queue_keys = [k for k in all_keys if k.startswith('celery') or k in ['default', 'news', 'price', 'alerts', 'briefings']]
            print(f"   Found {len(queue_keys)} queue-related keys:")
            for key in sorted(queue_keys):
                queue_length = redis_conn.llen(key)
                print(f"     - {key}: {queue_length} items")
        except Exception as e:
            print(f"   ⚠️  Could not check queues: {e}")
        print()

        # 5. Queue a test task
        print("5️⃣  Queuing test task...")
        print("   Task: force_generate_briefing")
        print("   Type: briefing_type='test'")

        test_task = app.send_task(
            'crypto_news_aggregator.tasks.briefing_tasks.force_generate_briefing',
            kwargs={'briefing_type': 'test'},
            queue='briefings'
        )

        test_task_id = test_task.id
        print(f"   ✅ Task queued: {test_task_id}")
        print()

        # 6. Monitor task status
        print("6️⃣  Monitoring task for 30 seconds...")
        print()

        max_wait = 30
        start = time.time()
        last_state = None

        while time.time() - start < max_wait:
            current_state = test_task.state

            if current_state != last_state:
                elapsed = int(time.time() - start)
                print(f"   [{elapsed}s] State: {current_state}")
                last_state = current_state

                if current_state in ['SUCCESS', 'FAILURE']:
                    print(f"   Task result: {test_task.result}")
                    break

            time.sleep(1)

        print()

        # 7. Final status
        print("7️⃣  Final Status:")
        print(f"   Task ID: {test_task_id}")
        print(f"   Final State: {test_task.state}")

        if test_task.state == 'SUCCESS':
            print("   ✅ WORKER IS PROCESSING TASKS!")
        elif test_task.state == 'PENDING':
            print("   ❌ WORKER NOT PROCESSING (task still pending)")
        elif test_task.state == 'FAILURE':
            print(f"   ❌ TASK FAILED: {test_task.result}")

        print()
        print("=" * 70)
        print("DIAGNOSTIC COMPLETE")
        print("=" * 70)

        return test_task.state == 'SUCCESS'

    except Exception as e:
        print(f"❌ Diagnostic failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = diagnose()
    sys.exit(0 if success else 1)
