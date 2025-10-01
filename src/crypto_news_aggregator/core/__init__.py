"""Core functionality for the crypto news aggregator."""

from .config import get_settings
from .sentiment_analyzer import SentimentAnalyzer
from .redis_rest_client import redis_client

__all__ = ["get_settings", "SentimentAnalyzer", "redis_client"]
