"""
Database synchronization service to keep PostgreSQL and MongoDB in sync.
"""
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from bson import ObjectId

from ..db.session import get_session
from ..db.models import Article as PGArticle, Source as PGSource
from ..db.mongodb_models import ArticleInDB, ArticleCreate, ArticleUpdate
from .article_service import article_service
from ..core.config import get_settings

logger = logging.getLogger(__name__)
# settings = get_settings()  # Removed top-level settings; use lazy initialization in methods as needed.

class SyncService:
    """Service for synchronizing data between PostgreSQL and MongoDB."""
    
    def __init__(self, batch_size: int = 100):
        self.batch_size = batch_size
        self.last_sync_time = datetime.now(timezone.utc) - timedelta(minutes=5)  # Initial sync window
    
    async def _convert_pg_to_mongo_article(self, pg_article: PGArticle) -> Dict[str, Any]:
        """Convert a PostgreSQL article to MongoDB format."""
        source = await pg_article.awaitable_attrs.source if hasattr(pg_article, 'awaitable_attrs') else pg_article.source
        
        return {
            "title": pg_article.title,
            "description": pg_article.description,
            "content": pg_article.content,
            "url": pg_article.url,
            "url_to_image": pg_article.url_to_image,
            "author": pg_article.author,
            "published_at": pg_article.published_at,
            "source": {
                "id": str(source.id) if source else None,
                "name": source.name if source else "Unknown",
                "url": source.url if source else None,
                "type": getattr(source, 'type', None)
            },
            "keywords": pg_article.keywords or [],
            "sentiment": {
                "score": pg_article.sentiment_score or 0.0,
                "magnitude": 0.0,  # Will be updated by sentiment analysis
                "label": "neutral",  # Default, will be updated
                "subjectivity": 0.5  # Default, will be updated
            } if pg_article.sentiment_score is not None else None,
            "metadata": {
                "postgres_id": str(pg_article.id),
                "imported_at": datetime.now(timezone.utc)
            },
            "created_at": pg_article.created_at or datetime.now(timezone.utc),
            "updated_at": pg_article.updated_at or datetime.now(timezone.utc)
        }
    
    async def sync_articles_to_mongodb(self):
        """Sync articles from PostgreSQL to MongoDB."""
        logger.info("Starting article synchronization from PostgreSQL to MongoDB")
        
        # Get a new session
        session_gen = get_session()
        session = await session_gen.__anext__()
        try:
            # Get articles that have been created or updated since last sync
            query = select(PGArticle).where(
                and_(
                    PGArticle.updated_at >= self.last_sync_time,
                    PGArticle.url.isnot(None)
                )
            ).order_by(PGArticle.updated_at.asc())
            
            result = await session.execute(query)
            articles = result.scalars().all()
            
            if not articles:
                logger.info("No articles to sync")
                return 0
            
            logger.info(f"Found {len(articles)} articles to sync")
            
            # Process articles in batches
            synced_count = 0
            for i in range(0, len(articles), self.batch_size):
                batch = articles[i:i + self.batch_size]
                
                # Convert and sync each article in the batch
                for pg_article in batch:
                    try:
                        # Convert to MongoDB format
                        article_data = await self._convert_pg_to_mongo_article(pg_article)
                        
                        # Use the article service to handle deduplication
                        await article_service.create_article(article_data)
                        synced_count += 1
                        
                        # Log progress
                        if synced_count % 10 == 0:
                            logger.info(f"Synced {synced_count}/{len(articles)} articles")
                        
                    except Exception as e:
                        logger.error(f"Error syncing article {pg_article.id}: {str(e)}", exc_info=True)
                        continue
            
            # Update the last sync time
            self.last_sync_time = datetime.now(timezone.utc)
            logger.info(f"Successfully synced {synced_count} articles to MongoDB")
            return synced_count
            
        except Exception as e:
            logger.error(f"Error during article sync: {str(e)}", exc_info=True)
            raise
        finally:
            await session.close()
    
    async def sync_sources_to_mongodb(self):
        """Sync sources from PostgreSQL to MongoDB."""
        logger.info("Starting source synchronization from PostgreSQL to MongoDB")
        
        # Get a new session
        session_gen = get_session()
        session = await session_gen.__anext__()
        try:
            # Get all sources
            query = select(PGSource)
            result = await session.execute(query)
            sources = result.scalars().all()
            
            if not sources:
                logger.info("No sources to sync")
                return 0
                
            logger.info(f"Found {len(sources)} sources to sync")
            
            # Sync each source
            synced_count = 0
            for pg_source in sources:
                try:
                    # Convert to MongoDB format
                    source_data = {
                        "name": pg_source.name,
                        "description": pg_source.description,
                        "url": pg_source.url,
                        "category": pg_source.category,
                        "language": pg_source.language,
                        "country": pg_source.country,
                        "metadata": {
                            "postgres_id": str(pg_source.id),
                            "imported_at": datetime.now(timezone.utc)
                        },
                        "created_at": pg_source.created_at or datetime.now(timezone.utc),
                        "updated_at": pg_source.updated_at or datetime.now(timezone.utc)
                    }
                    
                    # Use the article service to handle deduplication
                    await article_service.create_source(source_data)
                    synced_count += 1
                    
                    # Log progress
                    if synced_count % 10 == 0:
                        logger.info(f"Synced {synced_count}/{len(sources)} sources")
                        
                except Exception as e:
                    logger.error(f"Error syncing source {pg_source.id}: {str(e)}", exc_info=True)
                    continue
            
            logger.info(f"Successfully synced {synced_count} sources to MongoDB")
            return synced_count
            
        except Exception as e:
            logger.error(f"Error during source synchronization: {str(e)}", exc_info=True)
            raise
        finally:
            await session.close()
    
    async def sync_all(self):
        """Run all synchronization tasks."""
        logger.info("Starting full database synchronization")
        
        try:
            # Sync sources first
            sources_synced = await self.sync_sources_to_mongodb()
            
            # Then sync articles
            articles_synced = await self.sync_articles_to_mongodb()
            
            logger.info(f"Synchronization complete. Synced {sources_synced} sources and {articles_synced} articles.")
            return {"sources_synced": sources_synced, "articles_synced": articles_synced}
            
        except Exception as e:
            logger.error(f"Error during synchronization: {str(e)}", exc_info=True)
            raise


# Create a singleton instance
sync_service = SyncService()
