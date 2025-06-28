"""Core functionality for the crypto news aggregator."""
from .config import get_settings
from .news_collector import NewsCollector
from .sentiment_analyzer import SentimentAnalyzer
from .redis_rest_client import redis_client

# Create a settings instance for easy access
settings = get_settings()

__all__ = ['settings', 'NewsCollector', 'SentimentAnalyzer', 'redis_client']
