"""
Check entity extraction status.
"""
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))
    db = client[os.getenv('MONGODB_DB_NAME')]
    
    # Count articles with/without entities
    total_articles = await db.articles.count_documents({})
    articles_with_entities = await db.articles.count_documents({
        'entities': {'$exists': True, '$ne': None, '$ne': []}
    })
    articles_without_entities = total_articles - articles_with_entities
    
    print(f"Total articles: {total_articles}")
    print(f"Articles with entities: {articles_with_entities}")
    print(f"Articles without entities: {articles_without_entities}")
    
    # Count entity mentions
    total_mentions = await db.entity_mentions.count_documents({})
    print(f"\nTotal entity mentions: {total_mentions}")
    
    # Check if background worker is extracting entities
    if articles_with_entities > 0:
        print("\n✓ Entity extraction is working")
        
        # Show sample
        sample = await db.articles.find_one({'entities': {'$exists': True, '$ne': []}})
        if sample:
            print(f"\nSample article with entities:")
            print(f"  Title: {sample.get('title', 'N/A')[:60]}")
            print(f"  Entities: {len(sample.get('entities', []))} extracted")
            print(f"  Source: {sample.get('source')}")
    else:
        print("\n✗ No entities extracted yet")
    
    client.close()

asyncio.run(main())
