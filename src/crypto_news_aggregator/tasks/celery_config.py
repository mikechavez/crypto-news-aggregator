from datetime import timedelta
from celery.schedules import crontab
from ..core.config import get_settings
from .beat_schedule import get_schedule

settings = get_settings()

# Broker and result backend settings
broker_url = settings.CELERY_BROKER_URL
result_backend = settings.CELERY_RESULT_BACKEND

# Task settings
task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
timezone = 'UTC'
enable_utc = True

# Worker settings
worker_prefetch_multiplier = 1  # Process one task at a time
worker_max_tasks_per_child = 100  # Restart worker after 100 tasks to prevent memory leaks
worker_max_memory_per_child = 250000  # 250MB per worker process

# Task time limits
task_time_limit = 1800  # 30 minutes
task_soft_time_limit = 1500  # 25 minutes

# Result backend settings
result_expires = timedelta(days=1)  # Keep results for 1 day
result_persistent = True

# Queue settings
task_default_queue = 'default'
task_queues = {
    'default': {
        'exchange': 'default',
        'routing_key': 'default',
    },
    'news': {
        'exchange': 'news',
        'routing_key': 'news',
    },
    'price': {
        'exchange': 'price',
        'routing_key': 'price',
    },
    'alerts': {
        'exchange': 'alerts',
        'routing_key': 'alerts',
    },
}

task_routes = {
    'crypto_news_aggregator.tasks.alert_tasks.*': {'queue': 'alerts'},
    'crypto_news_aggregator.tasks.fetch_news.*': {'queue': 'news'},
    'crypto_news_aggregator.tasks.price_monitor.*': {'queue': 'price'},
}

# Beat settings
beat_schedule = get_schedule()
beat_schedule.update({
    # Keep any existing schedules that aren't in our dynamic schedule
    'update-trends-every-6-hours': {
        'task': 'crypto_news_aggregator.tasks.trends.update_trends',
        'schedule': crontab(minute=0, hour='*/6'),  # Run every 6 hours
        'options': {
            'expires': 3600,  # 1 hour
            'time_limit': 1800,  # 30 minutes
        },
    },
})
