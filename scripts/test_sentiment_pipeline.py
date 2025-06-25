#!/usr/bin/env python3
"""
Test script to verify the integration between the news collector and sentiment analysis pipeline.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from sqlalchemy import select

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import after setting up logging
from crypto_news_aggregator.db.session import get_sessionmaker
from crypto_news_aggregator.db.models import Article, Sentiment, Source
from crypto_news_aggregator.tasks.news import fetch_news
from crypto_news_aggregator.tasks.process_article import process_article, process_new_articles

async def test_sentiment_pipeline(source_name: str = "bbc-news") -> Dict[str, Any]:
    """
    Test the full pipeline from news collection to sentiment analysis.
    
    Args:
        source_name: News source to test with (default: bbc-news)
        
    Returns:
        Dict with test results
    """
    from crypto_news_aggregator.core.news_collector import NewsCollector
    
    results = {
        "source": source_name,
        "articles_fetched": 0,
        "articles_processed": 0,
        "sentiment_scores": [],
        "errors": []
    }
    
    try:
        # Step 1: Fetch news articles using the NewsCollector directly
        logger.info(f"Fetching news from {source_name}...")
        collector = NewsCollector()
        await collector.initialize()  # Initialize the collector
        
        # Collect from the source
        articles_collected = await collector.collect_from_source(source_name)
        results["articles_fetched"] = articles_collected
        logger.info(f"Fetched {articles_collected} articles")
        
        if results["articles_fetched"] == 0:
            logger.warning("No new articles were fetched. Pipeline test may be incomplete.")
        
        # Step 2: Process articles through sentiment analysis
        logger.info("Processing articles through sentiment analysis...")
        
        # Get the session maker
        session_maker = get_sessionmaker()
        
        # Find unprocessed articles
        async with session_maker() as session:
            result = await session.execute(
                select(Article)
                .where(Article.sentiment_score.is_(None))
                .order_by(Article.published_at.desc())
            )
            unprocessed_articles = result.scalars().all()
            
            # Process each article directly
            processed_count = 0
            for article in unprocessed_articles:
                try:
                    # Call process_article directly for testing
                    from crypto_news_aggregator.tasks.process_article import process_article
                    await process_article(article.id)
                    processed_count += 1
                except Exception as e:
                    error_msg = f"Error processing article {article.id}: {str(e)}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
            
            results["articles_processed"] = processed_count
            logger.info(f"Processed {processed_count} articles for sentiment analysis")
        
        # Step 3: Verify results in the database
        logger.info("Verifying results in the database...")
        session_maker = get_sessionmaker()
        
        async with session_maker() as session:
            # Get the most recent article with sentiment analysis
            result = await session.execute(
                select(Article, Sentiment)
                .join(Sentiment, Article.id == Sentiment.article_id)
                .order_by(Article.published_at.desc())
                .limit(5)  # Check up to 5 most recent articles
            )
            
            for article, sentiment in result.all():
                results["sentiment_scores"].append({
                    "article_id": article.id,
                    "title": article.title,
                    "score": sentiment.score,
                    "label": sentiment.label,
                    "subjectivity": sentiment.subjectivity
                })
                
                logger.info(
                    f"Article: {article.title[:50]}... | "
                    f"Score: {sentiment.score:.2f} | "
                    f"Label: {sentiment.label} | "
                    f"Subjectivity: {sentiment.subjectivity:.2f}"
                )
        
        results["status"] = "success"
        logger.info("Sentiment pipeline test completed successfully")
        
    except Exception as e:
        error_msg = f"Error in sentiment pipeline test: {str(e)}"
        logger.error(error_msg, exc_info=True)
        results["errors"].append(error_msg)
        results["status"] = "error"
    
    return results

def print_results(results: Dict[str, Any]) -> None:
    """Print the test results in a readable format."""
    print("\n" + "="*50)
    print(f"Sentiment Pipeline Test Results - {datetime.now().isoformat()}")
    print("="*50)
    
    print(f"\nSource: {results.get('source', 'N/A')}")
    print(f"Status: {results.get('status', 'unknown').upper()}")
    print(f"\nArticles Fetched: {results.get('articles_fetched', 0)}")
    print(f"Articles Processed: {results.get('articles_processed', 0)}")
    
    if results.get('sentiment_scores'):
        print("\nRecent Sentiment Analysis Results:")
        print("-"*50)
        for sent in results['sentiment_scores']:
            print(f"ID: {sent['article_id']}")
            print(f"Title: {sent['title'][:60]}...")
            print(f"Score: {sent['score']:.2f} | Label: {sent['label']} | Subjectivity: {sent['subjectivity']:.2f}")
            print("-"*50)
    
    if results.get('errors'):
        print("\nErrors:")
        for error in results['errors']:
            print(f"- {error}")
    
    print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    import sys
    
    # Use command line argument for source if provided, otherwise default to bbc-news
    source = sys.argv[1] if len(sys.argv) > 1 else "bbc-news"
    
    # Set up asyncio event loop policy for Windows compatibility
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # Run the test
    results = asyncio.run(test_sentiment_pipeline(source))
    
    # Print the results
    print_results(results)
