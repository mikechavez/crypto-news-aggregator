"""News collection module for fetching and processing cryptocurrency news.

This module provides the NewsCollector class which handles fetching news articles
from various sources using the NewsAPI, processing them, and storing them in MongoDB
"""

import asyncio
import logging
import random
import time
from datetime import datetime, timezone, timedelta
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, cast, TYPE_CHECKING

from newsapi import NewsApiClient

from crypto_news_aggregator.core.config import get_settings

# Avoid circular imports
if TYPE_CHECKING:
    from crypto_news_aggregator.services.article_service import ArticleService

# Type variable for generic function type
F = TypeVar('F', bound=Callable[..., Any])

# Constants
DEFAULT_PAGE_SIZE = 50
RATE_LIMIT_DELAY = 0.1  # seconds between API calls to respect rate limits
MAX_RETRIES = 3
NEWS_API_MAX_PAGES = 5  # Maximum number of pages to fetch per source

logger = logging.getLogger(__name__)
# settings = get_settings()  # Removed top-level settings; use lazy initialization in functions as needed.

def retry_with_backoff(retries: int = 3, backoff_in_seconds: float = 1.0):
    """Retry decorator with exponential backoff.
    
    Args:
        retries: Number of retry attempts
        backoff_in_seconds: Initial backoff time in seconds
        
    Returns:
        Decorated function with retry logic
    """
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            current_delay = backoff_in_seconds
            
            for attempt in range(retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < retries:
                        # Exponential backoff with jitter
                        sleep_time = current_delay * (2 ** attempt) + (random.uniform(0, 0.1) * current_delay)
                        logger.warning(
                            f"Attempt {attempt + 1}/{retries} failed with error: {str(e)}. "
                            f"Retrying in {sleep_time:.2f} seconds..."
                        )
                        await asyncio.sleep(sleep_time)
            
            # If we've exhausted all retries, log and re-raise the last exception
            logger.error(f"All {retries} attempts failed. Last error: {str(last_exception)}")
            raise last_exception if last_exception else Exception("Unknown error in retry decorator")
            
        return cast(F, wrapper)
    return decorator

class NewsCollector:
    """Collects news from various sources using the NewsAPI.
    
    Handles rate limiting, retries, and deduplication of articles.
    Uses the article_service for MongoDB storage.
    """
    
    def __init__(self, 
                 newsapi_client: Optional[NewsApiClient] = None,
                 article_service: Optional['ArticleService'] = None):
        """Initialize the NewsCollector with API clients and configuration.
        
        Args:
            newsapi_client: Optional pre-configured NewsApiClient instance.
                           If not provided, a new one will be created using NEWS_API_KEY.
            article_service: Optional ArticleService instance for saving articles.
                            If not provided, will be obtained from get_article_service().
        """
        if not settings.NEWS_API_KEY and newsapi_client is None:
            raise ValueError("NewsAPI key is not configured. Set NEWS_API_KEY in your environment.")
            
        self.newsapi = newsapi_client or NewsApiClient(api_key=settings.NEWS_API_KEY)
        
        # Lazy import to avoid circular imports
        if article_service is None:
            from crypto_news_aggregator.services.article_service import get_article_service
            self.article_service = get_article_service()
        else:
            self.article_service = article_service
            
        self._last_request_time: float = 0
        self._metrics = {
            'articles_processed': 0,
            'articles_skipped': 0,
            'api_errors': 0,
            'last_success': None,
            'start_time': datetime.now(timezone.utc).isoformat()
        }
        logger.info("NewsCollector initialized with MongoDB storage")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current collection metrics.
        
        Returns:
            Dict containing various metrics about the collector's operation.
        """
        metrics = self._metrics.copy()
        metrics['uptime'] = str(
            datetime.now(timezone.utc) - datetime.fromisoformat(metrics['start_time'])
        )
        return metrics
    
    def _update_metric(self, metric: str, value: Any = None, increment: int = 1) -> None:
        """Update a metric value.
        
        Args:
            metric: Name of the metric to update
            value: Value to set (if None, increments existing value)
            increment: Amount to increment by (used when value is None)
        """
        if value is not None:
            self._metrics[metric] = value
        else:
            self._metrics[metric] = self._metrics.get(metric, 0) + increment
    
    async def _respect_rate_limit(self) -> None:
        """Ensure we respect the rate limit by waiting if needed."""
        now = time.time()
        time_since_last = now - self._last_request_time
        
        if time_since_last < RATE_LIMIT_DELAY:
            sleep_time = RATE_LIMIT_DELAY - time_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            await asyncio.sleep(sleep_time)
            
        self._last_request_time = time.time()
    
    def _parse_date(self, date_str: Optional[str]) -> datetime:
        """Parse a date string from the API into a timezone-aware datetime.
        
        Args:
            date_str: Date string from the API (e.g., "2023-01-01T12:00:00Z")
            
        Returns:
            Timezone-aware datetime object, or current UTC time if parsing fails
        """
        if not date_str:
            return datetime.now(timezone.utc)
            
        try:
            # Handle ISO 8601 format with timezone
            if 'Z' in date_str:
                date_str = date_str.replace('Z', '+00:00')
                
            dt = datetime.fromisoformat(date_str)
            
            # Ensure timezone-aware
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
                
            return dt
            
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse date '{date_str}': {str(e)}")
            return datetime.now(timezone.utc)
    
    @retry_with_backoff(retries=MAX_RETRIES, backoff_in_seconds=RATE_LIMIT_DELAY)
    async def _fetch_articles_page(
        self, 
        source_id: str, 
        from_date: str, 
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Fetch a single page of articles from NewsAPI.
        
        Args:
            source_id: ID of the news source
            from_date: Start date for articles in YYYY-MM-DD format
            page: Page number to fetch
            page_size: Number of articles per page (max 100)
            
        Returns:
            Tuple of (articles, total_results)
        """
        await self._respect_rate_limit()
        
        try:
            response = self.newsapi.get_everything(
                sources=source_id,
                from_param=from_date,
                language='en',
                sort_by='publishedAt',
                page_size=min(page_size, DEFAULT_PAGE_SIZE),
                page=page
            )
            
            if response['status'] != 'ok':
                error_msg = response.get('message', 'Unknown error')
                if 'rate limited' in error_msg.lower():
                    raise Exception(f"Rate limited by NewsAPI: {error_msg}")
                raise Exception(f"NewsAPI error: {error_msg}")
                
            return response.get('articles', []), response.get('totalResults', 0)
            
        except Exception as e:
            logger.error(f"Error fetching page {page} from {source_id}: {str(e)}")
            raise
    
    async def _save_article(self, article_data: Dict[str, Any]) -> bool:
        """Save an article using the article service.
        
        Args:
            article_data: Raw article data from the API
            
        Returns:
            bool: True if article was saved, False if it was a duplicate or had an error
        """
        try:
            # Prepare article data for MongoDB
            article = {
                'source_id': article_data.get('source', {}).get('id', 'unknown'),
                'source_name': article_data.get('source', {}).get('name', 'Unknown'),
                'author': article_data.get('author'),
                'title': article_data.get('title', 'Untitled'),
                'description': article_data.get('description'),
                'content': article_data.get('content') or article_data.get('description', ''),
                'url': article_data.get('url', ''),
                'url_to_image': article_data.get('urlToImage'),
                'published_at': self._parse_date(article_data.get('publishedAt')),
                'raw_data': article_data  # Store the raw data for reference
            }
            
            # Save the article using the article service
            saved = await self.article_service.create_article(article)
            
            if saved:
                self._update_metric('articles_processed')
                self._metrics['last_success'] = datetime.now(timezone.utc).isoformat()
                logger.debug(f"Saved article: {article['title']}")
            else:
                self._update_metric('articles_skipped')
                logger.debug(f"Skipped duplicate article: {article['title']}")
                
            return saved
            
        except Exception as e:
            self._update_metric('api_errors')
            logger.error(f"Error saving article: {str(e)}", exc_info=True)
            return False
    
    async def collect_from_source(self, source_name: str, days: int = 1) -> int:
        """Collect articles from a specific source.
        
        Args:
            source_name: Name of the source to collect from
            days: Number of days of articles to collect
            
        Returns:
            int: Number of new articles collected
        """
        logger.info(f"Starting collection from {source_name} for the last {days} days")
        
        # Calculate date range
        to_date = datetime.now(timezone.utc)
        from_date = to_date - timedelta(days=days)
        
        page = 1
        total_articles = 0
        errors = 0
        
        try:
            while True:
                # Respect rate limiting
                await self._respect_rate_limit()
                
                try:
                    # Fetch a page of articles
                    response = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: self.newsapi.get_everything(
                            sources=source_name,
                            from_param=from_date.strftime('%Y-%m-%d'),
                            to=to_date.strftime('%Y-%m-%d'),
                            page=page,
                            page_size=min(100, DEFAULT_PAGE_SIZE),  # NewsAPI max is 100
                            language='en',
                            sort_by='publishedAt',
                            q='crypto OR cryptocurrency OR bitcoin OR ethereum OR blockchain'
                        )
                    )
                    
                    articles = response.get('articles', [])
                    if not articles:
                        logger.info(f"No more articles found on page {page}")
                        break
                    
                    # Process articles in parallel with limited concurrency
                    saved_count = 0
                    batch_size = 10  # Process in batches to avoid overwhelming the database
                    
                    for i in range(0, len(articles), batch_size):
                        batch = articles[i:i + batch_size]
                        tasks = [self._save_article(article) for article in batch]
                        results = await asyncio.gather(*tasks, return_exceptions=True)
                        
                        # Count successful saves
                        for result in results:
                            if isinstance(result, Exception):
                                errors += 1
                                logger.error(f"Error processing article: {str(result)}")
                            elif result:
                                saved_count += 1
                    
                    total_articles += saved_count
                    logger.info(
                        f"Page {page}: Processed {len(articles)} articles, "
                        f"saved {saved_count}, errors: {errors}"
                    )
                    
                    # Check if we've reached the maximum number of pages
                    if page >= NEWS_API_MAX_PAGES:
                        logger.info(f"Reached maximum number of pages ({NEWS_API_MAX_PAGES}) for {source_name}")
                        break
                        
                    page += 1
                    
                    # Small delay between pages to be nice to the API
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    errors += 1
                    self._update_metric('api_errors')
                    logger.error(f"Error on page {page} for {source_name}: {str(e)}")
                    
                    # If we get multiple errors in a row, give up
                    if errors >= 3:
                        logger.error("Too many errors, aborting collection")
                        break
                    
                    # Wait before retrying
                    await asyncio.sleep(5)
                
        except Exception as e:
            logger.error(f"Fatal error collecting from {source_name}: {str(e)}", exc_info=True)
            raise
            
        # Log collection summary
        logger.info(
            f"Finished collection from {source_name}. "
            f"Total articles processed: {total_articles}, errors: {errors}"
        )
            
        return total_articles
    
    async def collect_all_sources(self, max_sources: Optional[int] = None) -> int:
        """Collect articles from all available sources.
        
        Args:
            max_sources: Maximum number of sources to process (for testing)
            
        Returns:
            int: Total number of new articles collected
        """
        logger.info("Starting collection from all sources")
        total_articles = 0
        
        try:
            # Get all available sources
            sources_response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.newsapi.get_sources(language='en', country='us')
            )
            
            sources = sources_response.get('sources', [])
            if not sources:
                logger.warning("No sources found")
                return 0
                
            # Limit number of sources if specified
            if max_sources is not None and max_sources > 0:
                sources = sources[:max_sources]
                
            logger.info(f"Processing {len(sources)} sources")
            
            # Process sources with rate limiting
            for i, source in enumerate(sources, 1):
                source_id = source['id']
                try:
                    logger.info(f"Processing source {i}/{len(sources)}: {source_id} - {source.get('name', 'Unknown')}")
                    
                    count = await self.collect_from_source(source_id)
                    total_articles += count
                    
                    # Add a small delay between sources to avoid hitting rate limits
                    if i < len(sources):
                        await asyncio.sleep(RATE_LIMIT_DELAY)
                        
                except Exception as e:
                    logger.error(f"Error processing source {source_id}: {str(e)}", exc_info=True)
                    # Continue with next source even if one fails
                    continue
            
            logger.info(f"Collected {total_articles} new articles in total")
            return total_articles
            
        except Exception as e:
            logger.error(f"Error in collect_all_sources: {str(e)}", exc_info=True)
            return total_articles  # Return whatever we've collected so far
