"""Celery Beat schedule configuration."""

from datetime import timedelta
from celery.schedules import crontab
from ..core.config import get_settings

# settings = get_settings()  # Removed top-level settings; use lazy initialization in functions as needed.


# The beat schedule is a dictionary that contains the schedule of periodic tasks
# See: https://docs.celeryq.dev/en/stable/userguide/periodic-tasks.html
def get_schedule():
    """Get the beat schedule configuration.

    This function allows for dynamic schedule configuration based on settings.
    """
    settings = get_settings()
    return {
        # DISABLED (BUG-019): API-based news fetching deprecated
        # CoinDesk and Bloomberg APIs are blocked/failing
        # RSS-based system provides articles successfully
        # Uncomment if APIs are fixed or when switching news sources
        # "fetch-news-every-5-minutes": {
        #     "task": "fetch_news",  # Task registered with short name in tasks/__init__.py
        #     "schedule": timedelta(seconds=settings.NEWS_FETCH_INTERVAL),
        #     "args": (None,),  # None means fetch from all enabled sources
        #     "options": {
        #         "expires": settings.NEWS_FETCH_INTERVAL / 2,  # Prevent duplicate tasks
        #         "time_limit": 600,  # 10 minutes
        #     },
        # },
        # Check and process price alerts every 5 minutes
        "check-price-alerts": {
            "task": "check_price_alerts",  # Task registered with short name in tasks/__init__.py
            "schedule": timedelta(seconds=settings.PRICE_CHECK_INTERVAL),
            "options": {
                "expires": 240,  # 4 minutes
                "time_limit": 240,  # 4 minutes
                "queue": "alerts",
            },
        },
        # ============================================================
        # Briefing Tasks - Daily crypto briefings at 8 AM and 8 PM EST
        # ============================================================
        # Morning briefing at 8:00 AM EST (13:00 UTC, or 12:00 UTC during DST)
        # Using America/New_York timezone for automatic DST handling
        "generate-morning-briefing": {
            "task": "crypto_news_aggregator.tasks.briefing_tasks.generate_morning_briefing",
            "schedule": crontab(
                hour=8,
                minute=0,
                # Note: Celery uses the configured timezone (UTC by default)
                # 8 AM EST = 13:00 UTC (or 12:00 UTC during EDT)
                # For production, set celery timezone to America/New_York
            ),
            "options": {
                "expires": 3600,  # 1 hour
                "time_limit": 600,  # 10 minutes
            },
        },
        # Evening briefing at 8:00 PM EST (01:00 UTC next day, or 00:00 UTC during DST)
        "generate-evening-briefing": {
            "task": "crypto_news_aggregator.tasks.briefing_tasks.generate_evening_briefing",
            "schedule": crontab(
                hour=20,
                minute=0,
            ),
            "options": {
                "expires": 3600,  # 1 hour
                "time_limit": 600,  # 10 minutes
            },
        },
        # Weekly cleanup of old briefings (every Sunday at 3 AM EST)
        "cleanup-old-briefings": {
            "task": "crypto_news_aggregator.tasks.briefing_tasks.cleanup_old_briefings",
            "schedule": crontab(
                hour=3,
                minute=0,
                day_of_week="sunday",
            ),
            "args": (30,),  # Keep 30 days of briefings
            "options": {
                "expires": 3600,  # 1 hour
                "time_limit": 300,  # 5 minutes
            },
        },
        # Consolidate duplicate narratives every hour
        "consolidate-narratives": {
            "task": "consolidate_narratives",  # Task registered with short name in tasks/__init__.py
            "schedule": crontab(minute=0),  # Every hour at :00
            "options": {
                "expires": 3600,  # 1 hour timeout
                "time_limit": 3600,  # 1 hour
            },
        },
    }
