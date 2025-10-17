#!/usr/bin/env python3
"""
Delete the old 2019 TradingView article from MongoDB
"""
import sys
import asyncio
from pathlib import Path
from bson import ObjectId

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.crypto_news_aggregator.db.mongodb import get_mongodb

async def main():
    mongodb = await get_mongodb()
    articles_collection = mongodb.articles
    
    article_id = "68d4b36b30d27b58f9dcd56c"
    
    # First, verify the article exists
    article = await articles_collection.find_one({"_id": ObjectId(article_id)})
    
    if not article:
        print(f"Article {article_id} not found")
        return
    
    print(f"Found article to delete:")
    print(f"  ID: {article_id}")
    print(f"  Title: {article.get('title')}")
    print(f"  Published: {article.get('published_at')}")
    
    # Delete the article
    result = await articles_collection.delete_one({"_id": ObjectId(article_id)})
    
    if result.deleted_count > 0:
        print(f"\n✓ Successfully deleted article {article_id}")
    else:
        print(f"\n✗ Failed to delete article {article_id}")

if __name__ == "__main__":
    asyncio.run(main())
