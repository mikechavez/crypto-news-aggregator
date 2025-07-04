"""News source factory and utilities."""
from typing import Dict, Type, Optional, Any
import logging

from .base import NewsSource, NewsSourceError
from .coindesk import CoinDeskSource
from .bloomberg import BloombergSource

logger = logging.getLogger(__name__)

# Registry of available news sources
_SOURCE_REGISTRY: Dict[str, Type[NewsSource]] = {
    'coindesk': CoinDeskSource,
    'bloomberg': BloombergSource,
}

def get_available_sources() -> list[str]:
    """Get a list of available news source IDs.
    
    Returns:
        List of source IDs that can be used with create_source()
    """
    return list(_SOURCE_REGISTRY.keys())

def create_source(source_id: str, **kwargs: Any) -> NewsSource:
    """Create a news source instance by ID.
    
    Args:
        source_id: ID of the news source to create (e.g., 'coindesk')
        **kwargs: Additional arguments to pass to the source constructor
        
    Returns:
        An instance of the requested news source
        
    Raises:
        ValueError: If the source_id is not recognized
    """
    source_class = _SOURCE_REGISTRY.get(source_id.lower())
    if not source_class:
        raise ValueError(f"Unknown news source: {source_id}. "
                         f"Available sources: {', '.join(get_available_sources())}")
    
    return source_class(**kwargs)

def register_source(source_id: str, source_class: Type[NewsSource]):
    """Register a new news source class.
    
    Args:
        source_id: Unique identifier for the source
        source_class: NewsSource subclass to register
        
    Raises:
        ValueError: If the source_id is already registered or source_class is invalid
    """
    if not issubclass(source_class, NewsSource):
        raise ValueError(f"source_class must be a subclass of NewsSource")
    
    source_id = source_id.lower()
    if source_id in _SOURCE_REGISTRY:
        raise ValueError(f"Source ID '{source_id}' is already registered")
    
    _SOURCE_REGISTRY[source_id] = source_class
    logger.info(f"Registered news source: {source_id}")

# Register built-in sources
__all__ = [
    'NewsSource',
    'NewsSourceError',
    'get_available_sources',
    'create_source',
    'register_source',
    'CoinDeskSource',
    'BloombergSource',
]
