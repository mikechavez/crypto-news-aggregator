from crypto_news_aggregator.tasks.news import fetch_news

def trigger_fetch_news():
    """Triggers the news fetching task."""
    print("Triggering news fetch task...")
    result = fetch_news.delay()
    print(f"Task '{fetch_news.name}' sent with ID: {result.id}")
    print("You can monitor the Celery worker logs to see the progress.")

if __name__ == "__main__":
    trigger_fetch_news()
