"""News collection module for fetching and processing cryptocurrency news."""
import logging
import asyncio
import time
import random
from typing import List, Dict, Any, Optional, Set, Tuple, cast
from datetime import datetime, timedelta, timezone
from functools import wraps

from newsapi import NewsApiClient
from newsapi.newsapi_client import NewsApiClient as NewsApiClientType
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import or_

# Use absolute imports to avoid duplicate model registration
from crypto_news_aggregator.db.session import get_sessionmaker
from crypto_news_aggregator.db.models import Article, Source
from crypto_news_aggregator.core.config import get_settings

# Configure logger
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Constants
DEFAULT_PAGE_SIZE = 100  # Max allowed by NewsAPI
MAX_RETRIES = 3
RATE_LIMIT_DELAY = 1.0  # Base delay between API calls in seconds
NEWS_API_MAX_PAGES = 5  # Maximum number of pages to fetch per source


def retry_with_backoff(retries: int = 3, backoff_in_seconds: float = 1.0):
    """Decorator to retry a function with exponential backoff.
    
    Args:
        retries: Number of retry attempts
        backoff_in_seconds: Initial backoff time in seconds
    """
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
                    
                    # Calculate backoff with jitter
                    backoff = min(
                        backoff_in_seconds * (2 ** attempt) + random.uniform(0, 1),
                        30.0  # Max 30 seconds
                    )
                    logger.warning(
                        f"Attempt {attempt + 1} failed. Retrying in {backoff:.2f} seconds. Error: {str(e)}"
                    )
                    await asyncio.sleep(backoff)
            
            # This should never be reached due to the raise in the loop
            raise last_exception  # type: ignore
        return wrapper
    return decorator

class NewsCollector:
    """Collects news from various sources using the NewsAPI.
    
    Handles rate limiting, retries, and deduplication of articles.
    """
    
    def __init__(self, newsapi_client: Optional[NewsApiClient] = None):
        """Initialize the NewsCollector with API clients and configuration."""
        if not settings.NEWS_API_KEY and newsapi_client is None:
            raise ValueError("NewsAPI key is not configured. Set NEWS_API_KEY in your environment.")
            
        self.newsapi = newsapi_client or NewsApiClient(api_key=settings.NEWS_API_KEY)
        self.session_maker = get_sessionmaker()
        self.processed_urls: Set[str] = set()
        self._last_request_time: float = 0
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the collector asynchronously."""
        if not self._initialized:
            await self._load_processed_urls()
            self._initialized = True
    
    async def _load_processed_urls(self) -> None:
        """Load already processed article URLs from the database to avoid duplicates."""
        try:
            async with self.session_maker() as session:
                result = await session.execute(select(Article.url))
                self.processed_urls = {row[0] for row in result.all()}
                logger.info(f"Loaded {len(self.processed_urls)} processed article URLs")
        except SQLAlchemyError as e:
            logger.error(f"Database error loading processed URLs: {str(e)}")
            self.processed_urls = set()
        except Exception as e:
            logger.error(f"Unexpected error loading processed URLs: {str(e)}")
            self.processed_urls = set()
    
    async def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting between API calls."""
        now = time.time()
        time_since_last = now - self._last_request_time
        
        if time_since_last < RATE_LIMIT_DELAY:
            sleep_time = RATE_LIMIT_DELAY - time_since_last
            await asyncio.sleep(sleep_time)
        
        self._last_request_time = time.time()
    
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
        await self._enforce_rate_limit()
        
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
        total_new_articles = 0
        
        try:
            # Get articles from the last 24 hours
            from_date = (datetime.now(timezone.utc) - timedelta(days=1)).strftime('%Y-%m-%d')
            
            # Fetch first page to get total results
            articles, total_results = await self._fetch_articles_page(
                source_id=source_id,
                from_date=from_date,
                page=1,
                page_size=10  # Small page size to quickly check if there are any results
            )
            
            if not articles:
                logger.info(f"No articles found for source {source_id}")
                return 0
                
            logger.info(f"Found {total_results} total articles from {source_id}")
            
            # Process first page
            new_articles = await self._process_articles(articles, source_id)
            total_new_articles += new_articles
            
            # Calculate total pages to fetch (capped at NEWS_API_MAX_PAGES)
            total_pages = min(
                (total_results + DEFAULT_PAGE_SIZE - 1) // DEFAULT_PAGE_SIZE,
                NEWS_API_MAX_PAGES
            )
            
            # Fetch remaining pages
            for page in range(2, total_pages + 1):
                try:
                    page_articles, _ = await self._fetch_articles_page(
                        source_id=source_id,
                        from_date=from_date,
                        page=page,
                        page_size=DEFAULT_PAGE_SIZE
                    )
                    
                    if not page_articles:
                        break
                        
                    new_articles = await self._process_articles(page_articles, source_id)
                    total_new_articles += new_articles
                    
                    # If we got fewer articles than requested, we've reached the end
                    if len(page_articles) < DEFAULT_PAGE_SIZE:
                        break
                        
                except Exception as e:
                    logger.error(f"Error processing page {page} for {source_id}: {str(e)}")
                    break
            
            logger.info(f"Collected {total_new_articles} new articles from {source_id}")
            return total_new_articles
            
        except Exception as e:
            logger.error(f"Error collecting from {source_id}: {str(e)}", exc_info=True)
            return total_new_articles  # Return whatever we've collected so far
    
    @retry_with_backoff()
    async def _fetch_available_sources(self) -> List[Dict[str, Any]]:
        """Fetch available news sources from NewsAPI."""
        await self._enforce_rate_limit()
        
        try:
            response = self.newsapi.get_sources(
                language='en',
                country='us'
            )
            
            if response['status'] != 'ok':
                raise Exception(f"Failed to fetch sources: {response.get('message')}")
                
            return response.get('sources', [])
            
        except Exception as e:
            logger.error(f"Error fetching sources: {str(e)}")
            raise
    
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
            
        logger.info("Collecting news from all available sources")
        total_articles = 0
        
        try:
            # Get all available sources
            sources = await self._fetch_available_sources()
            
            if not sources:
                logger.warning("No sources available to collect from")
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
        if not articles:
            return 0
            
        new_articles = 0
        
        try:
            async with self.session_maker() as session:
                # Get or create the source
                result = await session.execute(
                    select(Source).filter(Source.id == source_id)
                )
                source = result.scalar_one_or_none()
                
                # Create source if it doesn't exist
                if not source:
                    source = Source(
                        id=source_id,
                        name=source_id,
                        url=f"https://{source_id}.com",  # Default URL
                        type="news"  # Default type
                    )
                    session.add(source)
                    await session.commit()
                
                # Process articles in batches
                batch_size = 50
                for i in range(0, len(articles), batch_size):
                    batch = articles[i:i + batch_size]
                    batch_new_articles = 0
                    
                    for article_data in batch:
                        try:
                            url = article_data.get('url')
                            if not url or url in self.processed_urls:
                                continue
                            
                            # Parse published_at with timezone support
                            published_str = article_data.get('publishedAt')
                            if not published_str:
                                continue
                                
                            try:
                                # Handle different datetime formats
                                if 'Z' in published_str:
                                    published_str = published_str.replace('Z', '+00:00')
                                published_at = datetime.fromisoformat(published_str)
                                
                                # Ensure timezone-aware datetime
                                if published_at.tzinfo is None:
                                    published_at = published_at.replace(tzinfo=timezone.utc)
                                    
                            except (ValueError, TypeError) as e:
                                logger.warning(f"Invalid date format for article {url}: {published_str}")
                                published_at = datetime.now(timezone.utc)
                            
                            # Create article
                            article = Article(
                                title=article_data.get('title', 'No title'),
                                url=url,
                                description=article_data.get('description', ''),
                                content=article_data.get('content', ''),
                                published_at=published_at,
                                source_id=source_id,
                                author=article_data.get('author'),
                                url_to_image=article_data.get('urlToImage'),
                                raw_data=article_data  # Store the full raw data
                            )
                            
                            session.add(article)
                            self.processed_urls.add(url)
                            batch_new_articles += 1
                            
                        except Exception as e:
                            logger.error(f"Error processing article {url}: {str(e)}", exc_info=True)
                    
                    # Commit after each batch
                    try:
                        await session.commit()
                        new_articles += batch_new_articles
                        logger.debug(f"Committed batch of {batch_new_articles} new articles")
                    except SQLAlchemyError as e:
                        await session.rollback()
                        logger.error(f"Database error committing batch: {str(e)}")
                        # Continue with next batch even if one fails
                    
            return new_articles
            
        except Exception as e:
            logger.error(f"Error in _process_articles: {str(e)}", exc_info=True)
            return new_articles  # Return whatever we've processed so far
