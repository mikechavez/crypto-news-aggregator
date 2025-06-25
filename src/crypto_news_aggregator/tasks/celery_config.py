from celery.schedules import crontab
from ..core.config import get_settings

settings = get_settings()

broker_url = settings.CELERY_BROKER_URL
result_backend = settings.CELERY_RESULT_BACKEND

# Task settings
task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
timezone = 'UTC'
enable_utc = True

# Beat settings for scheduled tasks
beat_schedule = {
    'fetch-news-every-hour': {
        'task': 'crypto_news_aggregator.tasks.news.fetch_news',
        'schedule': crontab(minute=0),  # Run at the start of every hour
    },
    'update-trends-every-6-hours': {
        'task': 'crypto_news_aggregator.tasks.trends.update_trends',
        'schedule': crontab(minute=0, hour='*/6'),  # Run every 6 hours
    },
}
