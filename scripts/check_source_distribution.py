"""
Check source distribution across all data.
"""
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()
from motor.motor_asyncio import AsyncIOMotorClient
from collections import Counter

async def main():
    client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))
    db = client[os.getenv('MONGODB_DB_NAME')]
    
    print("=" * 60)
    print("SOURCE DISTRIBUTION ANALYSIS")
    print("=" * 60)
    
    # Check articles
    print("\nARTICLES:")
    article_sources = await db.articles.distinct('source')
    print(f"Unique sources: {sorted(article_sources)}")
    
    for source in sorted(article_sources):
        count = await db.articles.count_documents({'source': source})
        print(f"  {source:20s}: {count:4d} articles")
    
    # Check entity mentions
    print("\nENTITY MENTIONS:")
    mention_sources = await db.entity_mentions.distinct('source')
    print(f"Unique sources: {sorted(mention_sources)}")
    
    for source in sorted(mention_sources):
        count = await db.entity_mentions.count_documents({
            'source': source,
            'is_primary': True
        })
        print(f"  {source:20s}: {count:4d} primary mentions")
    
    # Check a sample entity to see source diversity
    print("\n" + "=" * 60)
    print("SAMPLE ENTITY: Bitcoin")
    print("=" * 60)
    
    bitcoin_sources = await db.entity_mentions.distinct('source', {
        'entity': 'Bitcoin',
        'is_primary': True
    })
    
    print(f"Sources mentioning Bitcoin: {bitcoin_sources}")
    
    for source in bitcoin_sources:
        count = await db.entity_mentions.count_documents({
            'entity': 'Bitcoin',
            'is_primary': True,
            'source': source
        })
        print(f"  {source:20s}: {count:4d} mentions")
    
    client.close()

asyncio.run(main())
