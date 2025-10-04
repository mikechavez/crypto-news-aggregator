"""
Update articles with source="rss" to have specific feed names based on URL patterns.
"""
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))
    db = client[os.getenv('MONGODB_DB_NAME')]
    
    # Map URL patterns to feed names
    patterns = {
        'cointelegraph.com': 'cointelegraph',
        'coindesk.com': 'coindesk',
        'decrypt.co': 'decrypt',
        'bitcoinmagazine.com': 'bitcoinmagazine',
        'chaingpt.org': 'chaingpt'
    }
    
    for pattern, feed_name in patterns.items():
        result = await db.articles.update_many(
            {'source': 'rss', 'url': {'$regex': pattern}},
            {'$set': {'source': feed_name}}
        )
        print(f'{feed_name}: {result.modified_count} articles updated')
    
    client.close()

asyncio.run(main())
