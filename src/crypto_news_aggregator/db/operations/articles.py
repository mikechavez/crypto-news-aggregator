from typing import List
from motor.motor_asyncio import AsyncIOMotorClient
from crypto_news_aggregator.models.article import ArticleCreate, ArticleInDB
from crypto_news_aggregator.db.mongodb import mongo_manager

async def create_or_update_articles(articles: List[ArticleCreate]):
    """Creates new articles or updates existing ones in the database."""
    db = await mongo_manager.get_async_database()
    collection = db.articles

    for article in articles:
        # Ensure URL is a string before database operations
        if hasattr(article, 'url') and not isinstance(article.url, str):
            article.url = str(article.url)
        existing_article = await collection.find_one({"source_id": article.source_id})
        if existing_article:
            # Update metrics if the article already exists
            await collection.update_one(
                {"_id": existing_article["_id"]},
                {"$set": {"metrics": article.metrics.model_dump()}}
            )
        else:
            # Insert new article
            # Exclude '_id' to let MongoDB generate it
            article_data = article.model_dump()
            article_in_db = ArticleInDB(**article_data)
            await collection.insert_one(article_data)
