import asyncio
from ..services.rss_service import RSSService
from ..db.operations.articles import create_or_update_articles
from ..llm.factory import get_llm_provider
from ..db.mongodb import mongo_manager

async def fetch_and_process_rss_feeds():
    """Fetches RSS feeds, processes articles, and stores them."""
    rss_service = RSSService()
    articles = await rss_service.fetch_all_feeds()
    await create_or_update_articles(articles)
    
    # Run LLM analysis on the newly fetched articles
    await process_new_articles_from_mongodb()

async def process_new_articles_from_mongodb():
    """Analyzes new articles from MongoDB that haven't been processed yet."""
    db = await mongo_manager.get_async_database()
    collection = db.articles
    llm_client = get_llm_provider()

    # Find articles that need analysis
    new_articles = collection.find({"relevance_score": None})
    
    async for article in new_articles:
        # Perform relevance scoring and sentiment analysis
        combined_text = f"{article['title']}. {article['text']}"
        sentiment_score = llm_client.analyze_sentiment(combined_text)

        # Since analyze_sentiment only returns a float, we can't get relevance score here.
        # We'll just update the sentiment score for now.
        analysis = {
            'relevance_score': 0.5,  # Placeholder
            'sentiment': {'score': sentiment_score}
        }

        # Update the article in MongoDB
        await collection.update_one(
            {"_id": article["_id"]},
            {"$set": {
                "relevance_score": analysis['relevance_score'],
                "sentiment_score": analysis['sentiment']['score'],
                "sentiment_label": "",  # Placeholder
                "themes": [],  # Placeholder
            }}
        )
