from celery import Celery
from .celery_config import *
from .celery_config import get_beat_schedule

# Import all tasks to ensure they're registered
from .news import fetch_news, analyze_sentiment
from .process_article import process_article, process_new_articles
from .trends import update_trends, calculate_article_keywords
from .narrative_consolidation import consolidate_narratives_task
from .briefing_tasks import (
    generate_morning_briefing_task,
    generate_evening_briefing_task,
    cleanup_old_briefings_task,
)

app = Celery("crypto_news_aggregator")
app.config_from_object("crypto_news_aggregator.tasks.celery_config")

# Set the beat schedule after creating the app
app.conf.beat_schedule = get_beat_schedule()

# Explicitly import tasks to ensure they're registered
__all__ = [
    "app",
    "fetch_news",
    "analyze_sentiment",
    "process_article",
    "process_new_articles",
    "update_trends",
    "calculate_article_keywords",
    "generate_morning_briefing_task",
    "generate_evening_briefing_task",
    "cleanup_old_briefings_task",
]

# Auto-discover tasks (as a fallback)
app.autodiscover_tasks(
    [
        "crypto_news_aggregator.tasks.news",
        "crypto_news_aggregator.tasks.trends",
        "crypto_news_aggregator.tasks.briefing_tasks",
    ]
)

# This will be used by the worker and beat processes
if __name__ == "__main__":
    app.start()
