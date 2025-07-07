"""Celery Beat schedule configuration."""
from datetime import timedelta
from celery.schedules import crontab
from ..core.config import get_settings

settings = get_settings()

# The beat schedule is a dictionary that contains the schedule of periodic tasks
# See: https://docs.celeryq.dev/en/stable/userguide/periodic-tasks.html
beat_schedule = {
    # Fetch news from all enabled sources every 5 minutes
    'fetch-news-every-5-minutes': {
        'task': 'crypto_news_aggregator.tasks.fetch_news.fetch_news',
        'schedule': timedelta(seconds=settings.NEWS_FETCH_INTERVAL),
        'args': (None,),  # None means fetch from all enabled sources
        'options': {
            'expires': settings.NEWS_FETCH_INTERVAL / 2,  # Prevent duplicate tasks
            'time_limit': 600,  # 10 minutes
        },
    },
    
    # Check for price movements every 5 minutes
    'check-price-movements': {
        'task': 'crypto_news_aggregator.tasks.price_monitor.check_price_movements',
        'schedule': timedelta(seconds=settings.PRICE_CHECK_INTERVAL),
        'options': {
            'expires': settings.PRICE_CHECK_INTERVAL / 2,
            'time_limit': 300,  # 5 minutes
        },
    },
    
    # Check and process price alerts every 5 minutes
    'check-price-alerts': {
        'task': 'crypto_news_aggregator.tasks.alert_tasks.check_price_alerts',
        'schedule': timedelta(seconds=settings.PRICE_CHECK_INTERVAL),
        'options': {
            'expires': 240,  # 4 minutes
            'time_limit': 240,  # 4 minutes
            'queue': 'alerts',
        },
    },
}

def get_schedule():
    """Get the beat schedule configuration.
    
    This function allows for dynamic schedule configuration based on settings.
    """
    return beat_schedule
