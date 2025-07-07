"""Base classes for news sources."""
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, AsyncGenerator
import logging

logger = logging.getLogger(__name__)

class NewsSource(ABC):
    """Abstract base class for all news sources."""
    
    def __init__(self, name: str, base_url: str, api_key: Optional[str] = None):
        """Initialize the news source.
        
        Args:
            name: Human-readable name of the news source
            base_url: Base URL for the API
            api_key: Optional API key for the service
        """
        self.name = name
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.last_fetch_time = datetime.now(timezone.utc) - timedelta(hours=1)
        self._client = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit.
        
        Subclasses should override this to clean up resources.
        """
        pass
    
    @abstractmethod
    async def fetch_articles(self, 
                           since: Optional[datetime] = None,
                           limit: int = 50) -> AsyncGenerator[Dict[str, Any], None]:
        """Fetch articles from the source.
        
        Args:
            since: Only return articles published after this time
            limit: Maximum number of articles to return per page
            
        Yields:
            Article data as dictionaries
        """
        pass
    
    @abstractmethod
    def format_article(self, raw_article: Dict[str, Any]) -> Dict[str, Any]:
        """Format a raw article into our standard format.
        
        Args:
            raw_article: Raw article data from the source
            
        Returns:
            Formatted article data
        """
        pass
    
    def _get_default_since(self) -> datetime:
        """Get the default 'since' time (1 hour ago)."""
        return datetime.now(timezone.utc) - timedelta(hours=1)
    
    def _log_fetch(self, count: int):
        """Log a fetch operation."""
        logger.info(f"Fetched {count} new articles from {self.name}")
        self.last_fetch_time = datetime.now(timezone.utc)

class NewsSourceError(Exception):
    """Base exception for news source errors."""
    pass

class RateLimitExceededError(NewsSourceError):
    """Raised when the rate limit for a news source is exceeded."""
    pass

class AuthenticationError(NewsSourceError):
    """Raised when authentication with the news source fails."""
    pass

class APIError(NewsSourceError):
    """Raised when there is an error with the news source API."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.status_code = status_code
        super().__init__(message)
