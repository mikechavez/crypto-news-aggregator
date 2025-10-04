"""
Debug entity mention sources.
"""
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))
    db = client[os.getenv('MONGODB_DB_NAME')]
    
    # Check a few entity mentions
    print("Sample entity mentions:")
    cursor = db.entity_mentions.find({}).limit(5)
    async for mention in cursor:
        article_id = mention.get('article_id')
        mention_source = mention.get('source')
        
        article = await db.articles.find_one({'_id': article_id})
        article_source = article.get('source') if article else None
        
        print(f"\nMention ID: {mention['_id']}")
        print(f"  Entity: {mention.get('entity')}")
        print(f"  Mention source: {mention_source}")
        print(f"  Article ID: {article_id}")
        print(f"  Article source: {article_source}")
        print(f"  Match: {mention_source == article_source}")
    
    client.close()

asyncio.run(main())
