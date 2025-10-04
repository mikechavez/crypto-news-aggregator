"""
Check article sources and URLs.
"""
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))
    db = client[os.getenv('MONGODB_DB_NAME')]
    
    # Count articles by source
    print("Article counts by source:")
    pipeline = [
        {'$group': {'_id': '$source', 'count': {'$sum': 1}}},
        {'$sort': {'count': -1}}
    ]
    async for doc in db.articles.aggregate(pipeline):
        print(f"  {doc['_id']}: {doc['count']}")
    
    # Sample articles with None source
    print("\nSample articles with source=None:")
    cursor = db.articles.find({'source': None}).limit(5)
    async for article in cursor:
        print(f"\n  Title: {article.get('title', 'N/A')[:60]}")
        print(f"  URL: {article.get('url', 'N/A')}")
        print(f"  Source: {article.get('source')}")
    
    # Sample articles with 'rss' source
    print("\n\nSample articles with source='rss':")
    cursor = db.articles.find({'source': 'rss'}).limit(5)
    async for article in cursor:
        print(f"\n  Title: {article.get('title', 'N/A')[:60]}")
        print(f"  URL: {article.get('url', 'N/A')}")
        print(f"  Source: {article.get('source')}")
    
    client.close()

asyncio.run(main())
