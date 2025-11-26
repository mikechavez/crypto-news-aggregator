"""Services package for crypto news aggregator"""

from .selective_processor import SelectiveArticleProcessor, create_processor

__all__ = ['SelectiveArticleProcessor', 'create_processor']
