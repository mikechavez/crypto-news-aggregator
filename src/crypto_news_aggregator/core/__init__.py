"""Core functionality for the crypto news aggregator."""
from .config import settings
from .news_collector import NewsCollector
from .sentiment_analyzer import SentimentAnalyzer

__all__ = ['settings', 'NewsCollector', 'SentimentAnalyzer']
