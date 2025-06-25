#!/bin/bash

# Start Celery worker
celery -A crypto_news_aggregator.tasks worker \
    --loglevel=info \
    --concurrency=4 \
    --hostname=worker1@%h \
    --without-gossip \
    --without-mingle \
    --without-heartbeat \
    -Ofair &


# Start Celery beat for scheduled tasks
celery -A crypto_news_aggregator.tasks beat \
    --loglevel=info \
    --pidfile=celerybeat.pid \
    --scheduler=celery.beat:PersistentScheduler &

# Keep the script running
wait
