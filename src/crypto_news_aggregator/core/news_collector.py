import logging
import asyncio
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta, timezone

from newsapi import NewsApiClient
from sqlalchemy.future import select
from sqlalchemy import or_

# Use absolute imports to avoid duplicate model registration
from crypto_news_aggregator.db.session import get_sessionmaker
from crypto_news_aggregator.db.models import Article, Source
from crypto_news_aggregator.core.config import get_settings

# Configure logger
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

class NewsCollector:
    """Collects news from various sources using the NewsAPI."""
    
    def __init__(self):
        """Initialize the NewsCollector with API clients and configuration."""
        self.newsapi = NewsApiClient(api_key=settings.NEWS_API_KEY)
        self.session_maker = get_sessionmaker()
        self.processed_urls: Set[str] = set()
        # Don't load processed URLs in __init__ to avoid async issues
        self._initialized = False
    
    async def initialize(self):
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
        except Exception as e:
            logger.error(f"Error loading processed URLs: {str(e)}")
            self.processed_urls = set()
    
    async def collect_from_source(self, source_id: str) -> int:
        """
        Collect news articles from a specific source.
        
        Args:
            source_id: The ID of the source to collect from
            
        Returns:
            int: Number of new articles collected
        """
        logger.info(f"Collecting news from source: {source_id}")
        
        try:
            # Get articles from the last 24 hours
            from_date = (datetime.now(timezone.utc) - timedelta(days=1)).strftime('%Y-%m-%d')
            
            # Fetch articles from NewsAPI
            response = self.newsapi.get_everything(
                sources=source_id,
                from_param=from_date,
                language='en',
                sort_by='publishedAt',
                page_size=100  # Maximum allowed by the API
            )
            
            if response['status'] != 'ok':
                logger.error(f"Failed to fetch articles from {source_id}: {response.get('message')}")
                return 0
                
            articles = response.get('articles', [])
            logger.info(f"Found {len(articles)} articles from {source_id}")
            
            # Process and store articles
            new_articles = await self._process_articles(articles, source_id)
            logger.info(f"Stored {new_articles} new articles from {source_id}")
            
            return new_articles
            
        except Exception as e:
            logger.error(f"Error collecting from {source_id}: {str(e)}", exc_info=True)
            return 0
    
    async def collect_all_sources(self) -> int:
        """
        Collect news from all available sources.
        
        Returns:
            int: Total number of new articles collected
        """
        logger.info("Collecting news from all available sources")
        
        try:
            # Get all available sources
            sources = self.newsapi.get_sources(language='en', country='us')
            
            if sources['status'] != 'ok':
                logger.error(f"Failed to fetch sources: {sources.get('message')}")
                return 0
                
            source_ids = [source['id'] for source in sources['sources']]
            logger.info(f"Found {len(source_ids)} available sources")
            
            # Collect from each source
            total_articles = 0
            for source_id in source_ids:
                try:
                    count = await self.collect_from_source(source_id)
                    total_articles += count
                    # Be nice to the API
                    await asyncio.sleep(1)
                except Exception as e:
                    logger.error(f"Error processing source {source_id}: {str(e)}")
            
            logger.info(f"Collected {total_articles} new articles in total")
            return total_articles
            
        except Exception as e:
            logger.error(f"Error in collect_all_sources: {str(e)}", exc_info=True)
            return 0
    
    async def _process_articles(self, articles: List[Dict[str, Any]], source_id: str) -> int:
        """
        Process and store articles in the database.
        
        Args:
            articles: List of article dictionaries from the API
            source_id: ID of the source
            
        Returns:
            int: Number of new articles stored
        """
        if not articles:
            return 0
            
        new_articles = 0
        
        async with self.session_maker() as session:
            # Get or create the source
            result = await session.execute(select(Source).filter(Source.id == source_id))
            source = result.scalar_one_or_none()
            
            if not source:
                # Create a new source record if it doesn't exist
                source = Source(id=source_id, name=source_id)  # Name will be updated if we get more info
                session.add(source)
                await session.commit()
            
            # Process each article
            for article_data in articles:
                try:
                    url = article_data.get('url')
                    if not url or url in self.processed_urls:
                        continue
                        
                    # Create article
                    published_at = datetime.fromisoformat(article_data['publishedAt'].replace('Z', '+00:00'))
                    
                    article = Article(
                        title=article_data['title'],
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
                    new_articles += 1
                    
                except Exception as e:
                    logger.error(f"Error processing article: {str(e)}")
            
            await session.commit()
            
        return new_articles
