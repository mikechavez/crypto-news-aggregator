"""
Update entity_mentions.source to match their corresponding article.source.
"""
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))
    db = client[os.getenv('MONGODB_DB_NAME')]
    
    # Get all entity mentions
    cursor = db.entity_mentions.find({})
    updated_count = 0
    
    async for mention in cursor:
        article_id = mention.get('article_id')
        if not article_id:
            continue
            
        # Find the corresponding article
        article = await db.articles.find_one({'_id': article_id})
        if not article:
            continue
            
        article_source = article.get('source')
        mention_source = mention.get('source')
        
        # Update if sources don't match
        if article_source and article_source != mention_source:
            await db.entity_mentions.update_one(
                {'_id': mention['_id']},
                {'$set': {'source': article_source}}
            )
            updated_count += 1
            
            if updated_count % 100 == 0:
                print(f"Updated {updated_count} mentions...")
    
    print(f"\nTotal entity mentions updated: {updated_count}")
    client.close()

asyncio.run(main())
