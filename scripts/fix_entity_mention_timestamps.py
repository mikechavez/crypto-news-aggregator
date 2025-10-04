"""
Update entity mention timestamps to match their article published_at dates.
"""
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))
    db = client[os.getenv('MONGODB_DB_NAME')]
    
    print("Updating entity mention timestamps...")
    
    # Get all entity mentions
    cursor = db.entity_mentions.find({})
    updated_count = 0
    
    async for mention in cursor:
        article_id = mention.get('article_id')
        if not article_id:
            continue
        
        # Get article's published_at
        article = await db.articles.find_one({'_id': article_id})
        if not article:
            continue
        
        published_at = article.get('published_at')
        if published_at:
            await db.entity_mentions.update_one(
                {'_id': mention['_id']},
                {'$set': {'created_at': published_at}}
            )
            updated_count += 1
            
            if updated_count % 50 == 0:
                print(f"Updated {updated_count} mentions...")
    
    print(f"\nTotal mentions updated: {updated_count}")
    
    # Show date range
    oldest = await db.entity_mentions.find_one({}, sort=[('created_at', 1)])
    newest = await db.entity_mentions.find_one({}, sort=[('created_at', -1)])
    
    if oldest and newest:
        print(f"\nDate range:")
        print(f"  Oldest: {oldest.get('created_at')}")
        print(f"  Newest: {newest.get('created_at')}")
    
    client.close()

asyncio.run(main())
