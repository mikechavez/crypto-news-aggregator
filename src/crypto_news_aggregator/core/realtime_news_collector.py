"""News collection module using the self-hosted realtime-newsapi."""
import logging
import asyncio
from typing import List, Dict, Any, Optional, Set, Tuple, cast
from datetime import datetime, timedelta, timezone
from functools import wraps

from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import or_

from .realtime_news_client import RealtimeNewsClient
from ..db.session import get_sessionmaker
from ..db.models import Article, Source
from ..core.config import get_settings

# Configure logger
logger = logging.getLogger(__name__)

# Get settings
# settings = get_settings()  # Removed top-level settings; use lazy initialization in functions as needed.

# Constants
DEFAULT_PAGE_SIZE = 100
MAX_RETRIES = 3
RATE_LIMIT_DELAY = 0.5  # Reduced delay since we control the API
NEWS_API_MAX_PAGES = 5  # Maximum number of pages to fetch per source


def retry_with_backoff(retries: int = 3, backoff_in_seconds: float = 1.0):
    """Decorator to retry a function with exponential backoff."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt == retries - 1:  # Last attempt
                        raise
                    
                    # Exponential backoff with jitter
                    sleep_time = backoff_in_seconds * (2 ** attempt) + (random.uniform(0, 1) * 0.1)
                    logger.warning(
                        f"Attempt {attempt + 1} failed: {str(e)}. "
                        f"Retrying in {sleep_time:.2f}s..."
                    )
                    await asyncio.sleep(sleep_time)
            
            raise last_exception or Exception("Retry failed")
        return wrapper
    return decorator


class RealtimeNewsCollector:
    """Collects news using the self-hosted realtime-newsapi service.
    
    This is a drop-in replacement for the original NewsCollector that uses
    our self-hosted realtime-newsapi instead of the external NewsAPI service.
    """
    
    def __init__(self, newsapi_base_url: Optional[str] = None):
        """Initialize the RealtimeNewsCollector."""
        self.base_url = newsapi_base_url or settings.REALTIME_NEWSAPI_URL or "http://localhost:3000"
        self.session_maker = get_sessionmaker()
        self.processed_urls: Set[str] = set()
        self._last_request_time: float = 0
        self._initialized = False
    
    async def initialize(self):
        """Initialize the collector asynchronously."""
        if not self._initialized:
            await self._load_processed_urls()
            self._initialized = True
    
    async def _load_processed_urls(self):
        """Load already processed article URLs from the database to avoid duplicates."""
        async with self.session_maker() as session:
            result = await session.execute(select(Article.url))
            self.processed_urls = {url for (url,) in result.all()}
            logger.info(f"Loaded {len(self.processed_urls)} processed URLs from database")
    
    @retry_with_backoff(retries=MAX_RETRIES, backoff_in_seconds=RATE_LIMIT_DELAY)
    async def _fetch_articles_page(
        self, 
        source_id: str, 
        from_date: str, 
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Fetch a single page of articles from the realtime-newsapi.
        
        Args:
            source_id: ID of the news source
            from_date: Start date for articles in YYYY-MM-DD format
            page: Page number to fetch
            page_size: Number of articles per page
            
        Returns:
            Tuple of (articles, total_results)
        """
        async with RealtimeNewsClient(self.base_url) as client:
            # Check if the service is healthy
            if not await client.health_check():
                raise Exception("Realtime-newsapi service is not healthy")
            
            # Fetch articles
            response = await client.get_everything(
                sources=source_id,
                from_param=from_date,
                page=page,
                page_size=page_size,
                sort_by='publishedAt',
                language='en'
            )
            
            if response['status'] != 'ok':
                error_msg = response.get('message', 'Unknown error')
                raise Exception(f"Error from realtime-newsapi: {error_msg}")
            
            return response['articles'], response.get('totalResults', 0)
    
    async def collect_from_source(self, source_id: str) -> int:
        """
        Collect news articles from a specific source with pagination support.
        
        Args:
            source_id: The ID of the source to collect from
            
        Returns:
            int: Number of new articles collected
        """
        if not self._initialized:
            await self.initialize()
        
        logger.info(f"Collecting news from source: {source_id}")
        
        # Calculate date range (last 3 days by default)
        to_date = datetime.now(timezone.utc).date()
        from_date = (datetime.now(timezone.utc) - timedelta(days=3)).strftime('%Y-%m-%d')
        
        total_new_articles = 0
        page = 1
        
        try:
            while page <= NEWS_API_MAX_PAGES:
                articles, total_results = await self._fetch_articles_page(
                    source_id=source_id,
                    from_date=from_date,
                    page=page,
                    page_size=DEFAULT_PAGE_SIZE
                )
                
                if not articles:
                    break
                
                # Process the batch of articles
                new_count = await self._process_articles(articles, source_id)
                total_new_articles += new_count
                
                # Stop if we've processed all articles or reached the maximum pages
                if len(articles) < DEFAULT_PAGE_SIZE or page >= NEWS_API_MAX_PAGES:
                    break
                    
                page += 1
            
            logger.info(f"Collected {total_new_articles} new articles from {source_id}")
            return total_new_articles
            
        except Exception as e:
            logger.error(f"Error collecting from {source_id}: {str(e)}", exc_info=True)
            raise
    
    async def _process_articles(
        self, 
        articles: List[Dict[str, Any]], 
        source_id: str
    ) -> int:
        """
        Process and store articles in the database with deduplication.
        
        Args:
            articles: List of article dictionaries from the API
            source_id: ID of the source
            
        Returns:
            int: Number of new articles stored
        """
        new_articles = 0
        
        async with self.session_maker() as session:
            for article in articles:
                try:
                    url = article.get('url')
                    if not url or url in self.processed_urls:
                        continue
                    
                    # Create article object
                    published_at = datetime.fromisoformat(
                        article['publishedAt'].replace('Z', '+00:00')
                    ) if article.get('publishedAt') else datetime.now(timezone.utc)
                    
                    db_article = Article(
                        title=article.get('title', ''),
                        url=url,
                        source=source_id,
                        author=article.get('author'),
                        description=article.get('description'),
                        content=article.get('content'),
                        url_to_image=article.get('urlToImage'),
                        published_at=published_at,
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc)
                    )
                    
                    session.add(db_article)
                    self.processed_urls.add(url)
                    new_articles += 1
                    
                except Exception as e:
                    logger.error(f"Error processing article: {str(e)}", exc_info=True)
            
            try:
                await session.commit()
                logger.info(f"Processed {len(articles)} articles, {new_articles} were new")
            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Database error: {str(e)}")
                raise
        
        return new_articles
    
    async def collect_all_sources(self, max_sources: Optional[int] = None) -> int:
        """
        Collect news from all available sources with rate limiting.
        
        Args:
            max_sources: Maximum number of sources to process (None for all)
            
        Returns:
            int: Total number of new articles collected
        """
        if not self._initialized:
            await self.initialize()
        
        async with RealtimeNewsClient(self.base_url) as client:
            # Get all available sources
            try:
                response = await client.get_sources(language='en')
                if response['status'] != 'ok':
                    logger.error("Failed to fetch sources from realtime-newsapi")
                    return 0
                
                sources = response['sources']
                if max_sources:
                    sources = sources[:max_sources]
                
                logger.info(f"Found {len(sources)} sources to process")
                
                total_new_articles = 0
                for source in sources:
                    try:
                        new_articles = await self.collect_from_source(source['id'])
                        total_new_articles += new_articles
                    except Exception as e:
                        logger.error(f"Error processing source {source['id']}: {str(e)}")
                    
                    # Small delay between sources to be gentle on the API
                    await asyncio.sleep(1)
                
                return total_new_articles
                
            except Exception as e:
                logger.error(f"Error in collect_all_sources: {str(e)}", exc_info=True)
                raise
