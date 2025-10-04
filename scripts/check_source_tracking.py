"""
Check how sources are being tracked in entity mentions.
"""
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))
    db = client[os.getenv('MONGODB_DB_NAME')]
    
    print("=" * 70)
    print("SOURCE TRACKING ANALYSIS")
    print("=" * 70)
    
    # Check all unique sources in entity mentions
    sources = await db.entity_mentions.distinct('source')
    print(f"\nUnique sources in entity_mentions: {sources}")
    
    # Check sample entity mentions
    print("\nSample entity mentions:")
    mentions = await db.entity_mentions.find({'is_primary': True}).limit(5).to_list(5)
    for m in mentions:
        print(f"  Entity: {m.get('entity')}")
        print(f"  Source: {m.get('source')}")
        print(f"  Article ID: {m.get('article_id')}")
        print()
    
    # Check articles to see what sources they have
    print("Checking articles collection for source diversity...")
    article_sources = await db.articles.distinct('source')
    print(f"Unique sources in articles: {article_sources}")
    
    # Check sample articles
    print("\nSample articles:")
    articles = await db.articles.find({}).limit(5).to_list(5)
    for a in articles:
        print(f"  Title: {a.get('title', 'N/A')[:50]}...")
        print(f"  Source: {a.get('source', 'N/A')}")
        print(f"  ID: {a.get('_id')}")
        print()
    
    # Check if we can link entity mentions to article sources
    print("Checking entity mention -> article source linkage...")
    sample_mention = await db.entity_mentions.find_one({'is_primary': True})
    if sample_mention:
        article_id = sample_mention.get('article_id')
        article = await db.articles.find_one({'_id': article_id})
        if article:
            print(f"✅ Entity mention links to article:")
            print(f"   Entity: {sample_mention.get('entity')}")
            print(f"   Mention source: {sample_mention.get('source')}")
            print(f"   Article source: {article.get('source')}")
            print(f"   Article title: {article.get('title', 'N/A')[:60]}...")
        else:
            print(f"❌ Article not found for article_id: {article_id}")
    
    client.close()

asyncio.run(main())
