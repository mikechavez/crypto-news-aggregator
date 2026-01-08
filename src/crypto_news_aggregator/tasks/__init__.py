from celery import Celery
from .celery_config import *

# Import all tasks to ensure they're registered
from .news import fetch_news, analyze_sentiment
from .process_article import process_article, process_new_articles
from .trends import update_trends, calculate_article_keywords
from .narrative_consolidation import consolidate_narratives_task

app = Celery("crypto_news_aggregator")
app.config_from_object("crypto_news_aggregator.tasks.celery_config")

# Explicitly import tasks to ensure they're registered
__all__ = [
    "app",
    "fetch_news",
    "analyze_sentiment",
    "process_article",
    "process_new_articles",
    "update_trends",
    "calculate_article_keywords",
]

# Auto-discover tasks (as a fallback)
app.autodiscover_tasks(
    ["crypto_news_aggregator.tasks.news", "crypto_news_aggregator.tasks.trends"]
)

# This will be used by the worker and beat processes
if __name__ == "__main__":
    app.start()
