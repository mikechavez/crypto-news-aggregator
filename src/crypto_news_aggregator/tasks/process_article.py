import logging
from typing import Dict, Any, Optional
from celery import shared_task
from sqlalchemy.future import select

from ..db.session import get_sessionmaker
from ..db.models import Article, Sentiment
from ..core.sentiment_analyzer import SentimentAnalyzer

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_article(self, article_id: int) -> Dict[str, Any]:
    """
    Process a single article through the sentiment analysis pipeline.
    
    Args:
        article_id: ID of the article to process
        
    Returns:
        Dict containing processing status and results
    """
    logger.info(f"Processing article ID: {article_id}")
    
    session_maker = get_sessionmaker()
    
    try:
        async def _process():
            async with session_maker() as session:
                # Get the article
                result = await session.execute(
                    select(Article).where(Article.id == article_id)
                )
                article = result.scalar_one_or_none()
                
                if not article:
                    logger.error(f"Article {article_id} not found")
                    return {"status": "error", "message": "Article not found"}
                
                # Check if sentiment analysis was already performed
                if article.sentiment_score is not None:
                    logger.info(f"Article {article_id} already has sentiment analysis")
                    return {"status": "skipped", "message": "Sentiment analysis already performed"}
                
                # Analyze sentiment
                sentiment = SentimentAnalyzer.analyze_article(
                    article_text=article.content or "",
                    title=article.title
                )
                
                # Update article with sentiment score
                article.sentiment_score = sentiment["polarity"]
                
                # Create sentiment record
                sentiment_record = Sentiment(
                    article_id=article.id,
                    score=sentiment["polarity"],
                    label=sentiment["label"],
                    subjectivity=sentiment["subjectivity"],
                    raw_data=sentiment
                )
                
                session.add(sentiment_record)
                await session.commit()
                
                logger.info(f"Processed article {article_id} - Score: {sentiment['polarity']}, Label: {sentiment['label']}")
                return {
                    "status": "success",
                    "article_id": article_id,
                    "sentiment": sentiment
                }
        
        # Run the async function
        import asyncio
        return asyncio.run(_process())
        
    except Exception as e:
        logger.error(f"Error processing article {article_id}: {str(e)}", exc_info=True)
        # Retry on error
        raise self.retry(exc=e)

@shared_task
def process_new_articles() -> Dict[str, Any]:
    """
    Find and process all articles that haven't been analyzed yet.
    
    Returns:
        Dict with processing statistics
    """
    logger.info("Starting to process new articles for sentiment analysis")
    
    session_maker = get_sessionmaker()
    
    async def _process():
        async with session_maker() as session:
            # Find articles without sentiment analysis
            result = await session.execute(
                select(Article)
                .where(Article.sentiment_score.is_(None))
                .order_by(Article.published_at.desc())
                .limit(100)  # Process up to 100 articles at a time
            )
            
            articles = result.scalars().all()
            logger.info(f"Found {len(articles)} articles to process")
            
            # Process each article
            processed = 0
            for article in articles:
                try:
                    process_article.delay(article.id)
                    processed += 1
                except Exception as e:
                    logger.error(f"Error queuing article {article.id} for processing: {str(e)}")
            
            return {
                "status": "success",
                "articles_queued": processed,
                "total_articles": len(articles)
            }
    
    # Run the async function
    import asyncio
    return asyncio.run(_process())
