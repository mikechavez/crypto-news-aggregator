"""
Check for orphaned entity mentions (mentions whose articles don't exist).
"""
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))
    db = client[os.getenv('MONGODB_DB_NAME')]
    
    # Get total mention count
    total_mentions = await db.entity_mentions.count_documents({})
    print(f"Total entity mentions: {total_mentions}")
    
    # Check how many have valid article references
    valid_count = 0
    orphaned_count = 0
    
    cursor = db.entity_mentions.find({})
    async for mention in cursor:
        article_id = mention.get('article_id')
        if not article_id:
            orphaned_count += 1
            continue
            
        article = await db.articles.find_one({'_id': article_id})
        if article:
            valid_count += 1
        else:
            orphaned_count += 1
    
    print(f"Valid mentions (article exists): {valid_count}")
    print(f"Orphaned mentions (article missing): {orphaned_count}")
    
    # Check if we have any mentions at all with proper sources
    mentions_with_sources = await db.entity_mentions.count_documents({
        'source': {'$ne': 'rss'}
    })
    print(f"\nMentions with non-'rss' source: {mentions_with_sources}")
    
    client.close()

asyncio.run(main())
