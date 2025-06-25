import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta
from celery import shared_task
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from ..db.session import get_sessionmaker
from ..db.models import Article, Source
from ..core.news_collector import NewsCollector  # We'll implement this next
from ..core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

@shared_task(bind=True, max_retries=3)
def fetch_news(self, source_name: str = None):
    """
    Fetch news from all sources or a specific source.
    This is a synchronous wrapper around the async collector methods.
    """
    logger = self.get_logger()
    logger.info(f"Starting news fetch for source: {source_name or 'all'}")
    
    collector = NewsCollector()
    
    async def _fetch():
        try:
            if source_name:
                count = await collector.collect_from_source(source_name)
                return {
                    "status": "success",
                    "message": f"Successfully collected {count} new articles from {source_name}",
                    "source": source_name,
                    "articles_collected": count
                }
            else:
                count = await collector.collect_all_sources()
                return {
                    "status": "success",
                    "message": f"Successfully collected {count} new articles from all sources",
                    "source": "all",
                    "articles_collected": count
                }
        except Exception as e:
            logger.error(f"Error in _fetch: {str(e)}")
            raise
    
    try:
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run the async function and get the result
        result = loop.run_until_complete(_fetch())
        logger.info(f"Successfully completed news fetch: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error in fetch_news: {str(e)}")
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * 5)  # Retry after 5 minutes
        
    finally:
        # Clean up the event loop
        if 'loop' in locals() and loop is not None:
            loop.close()

@shared_task
def analyze_sentiment(article_id: int):
    """
    Analyze sentiment for a single article.
    This will be implemented after we set up the sentiment analysis component.
    """
    logger.info(f"Analyzing sentiment for article {article_id}")
    # TODO: Implement sentiment analysis
    return {"status": "pending", "message": "Sentiment analysis not yet implemented"}

@shared_task
def process_article(article_data: Dict[str, Any]):
    """
    Process a single article - save to DB and trigger sentiment analysis.
    """
    logger.info(f"Processing article: {article_data.get('title', 'Untitled')}")
    # TODO: Implement article processing
    return {"status": "pending", "message": "Article processing not yet implemented"}
