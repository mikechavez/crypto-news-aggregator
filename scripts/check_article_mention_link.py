"""
Check if entity mentions are getting the correct source from articles.
"""
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone, timedelta

async def main():
    client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))
    db = client[os.getenv('MONGODB_DB_NAME')]
    
    # Get a recent mention
    recent_mention = await db.entity_mentions.find_one(
        {},
        sort=[('created_at', -1)]
    )
    
    if recent_mention:
        print("Most recent entity mention:")
        print(f"  Entity: {recent_mention.get('entity')}")
        print(f"  Source: {recent_mention.get('source')}")
        print(f"  Article ID: {recent_mention.get('article_id')}")
        print(f"  Created: {recent_mention.get('created_at')}")
        
        # Look up the article
        article_id = recent_mention.get('article_id')
        article = await db.articles.find_one({'_id': article_id})
        
        if article:
            print(f"\nLinked article:")
            print(f"  Title: {article.get('title', 'N/A')[:60]}...")
            print(f"  Source: {article.get('source')}")
            print(f"  Created: {article.get('created_at')}")
            
            if article.get('source') != recent_mention.get('source'):
                print(f"\n❌ MISMATCH!")
                print(f"   Article source: {article.get('source')}")
                print(f"   Mention source: {recent_mention.get('source')}")
            else:
                print(f"\n✅ Sources match!")
        else:
            print(f"\n❌ Article not found for ID: {article_id}")
    
    # Check if we have any mentions with non-"rss" sources
    print("\n" + "="*60)
    non_rss_mentions = await db.entity_mentions.count_documents({
        'source': {'$nin': ['rss', 'unknown']}
    })
    print(f"Entity mentions with specific sources (not 'rss'): {non_rss_mentions}")
    
    if non_rss_mentions > 0:
        sample = await db.entity_mentions.find_one({
            'source': {'$nin': ['rss', 'unknown']}
        })
        print(f"Sample: {sample.get('entity')} from {sample.get('source')}")
    
    client.close()

asyncio.run(main())
