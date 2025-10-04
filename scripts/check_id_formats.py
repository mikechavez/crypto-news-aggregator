#!/usr/bin/env python3
"""Check article ID formats in articles and entity_mentions collections."""

import asyncio
from crypto_news_aggregator.db.mongodb import mongo_manager


async def check_id_formats():
    """Check the ID formats in both collections."""
    db = await mongo_manager.get_async_database()
    
    # Check articles
    article = await db.articles.find_one({})
    if article:
        print(f"Article _id type: {type(article['_id'])}")
        print(f"Article _id value: {article['_id']}")
        print(f"Article has 'source': {article.get('source')}")
        print(f"Article has 'source_id': {article.get('source_id')}")
    else:
        print("No articles found")
    
    print()
    
    # Check entity mentions
    mention = await db.entity_mentions.find_one({})
    if mention:
        print(f"Mention article_id type: {type(mention['article_id'])}")
        print(f"Mention article_id value: {mention['article_id']}")
        print(f"Mention has 'source': {mention.get('source')}")
    else:
        print("No entity mentions found")
    
    await mongo_manager.close()


if __name__ == "__main__":
    asyncio.run(check_id_formats())
