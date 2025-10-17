#!/usr/bin/env python3
"""
Script to investigate UI issues:
1. Find the old TradingView article
2. Check archived narratives lifecycle states
"""
import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.crypto_news_aggregator.db.session import get_sessionmaker
from src.crypto_news_aggregator.db.models import Article
from src.crypto_news_aggregator.db.mongodb import get_mongodb
from sqlalchemy import desc, select
from datetime import datetime, timedelta

async def main():
    # Get PostgreSQL session for articles
    SessionLocal = get_sessionmaker()
    
    # Get MongoDB for narratives
    mongodb = await get_mongodb()
    narratives_collection = mongodb.narratives
    
    async with SessionLocal() as session:
        try:
            print("=" * 80)
            print("1. SEARCHING FOR OLD TRADINGVIEW ARTICLE")
            print("=" * 80)
            
            # Find the TradingView article in PostgreSQL
            result = await session.execute(
                select(Article).filter(Article.title.like('%TradingView%Fibonacci%'))
            )
            pg_tradingview_articles = result.scalars().all()
            
            # Also check MongoDB articles collection
            articles_collection = mongodb.articles
            mongo_tradingview_articles = await articles_collection.find(
                {"title": {"$regex": "TradingView.*Fibonacci", "$options": "i"}}
            ).to_list(length=10)
            
            total_tradingview = len(pg_tradingview_articles) + len(mongo_tradingview_articles)
            
            print(f"\nFound {total_tradingview} TradingView/Fibonacci articles:")
            print(f"  - PostgreSQL: {len(pg_tradingview_articles)}")
            print(f"  - MongoDB: {len(mongo_tradingview_articles)}")
            
            for article in pg_tradingview_articles:
                print(f"\n[PostgreSQL] ID: {article.id}")
                print(f"Title: {article.title}")
                print(f"Source: {article.source_id if hasattr(article, 'source_id') else 'N/A'}")
                print(f"Published: {article.published_at}")
                print(f"URL: {article.url}")
            
            for article in mongo_tradingview_articles:
                print(f"\n[MongoDB] ID: {article.get('_id')}")
                print(f"Title: {article.get('title')}")
                source = article.get('source', {})
                if isinstance(source, dict):
                    print(f"Source: {source.get('name', 'N/A')}")
                else:
                    print(f"Source: {source}")
                print(f"Published: {article.get('published_at')}")
                print(f"URL: {article.get('url')}")
            
            print("\n" + "=" * 80)
            print("2. CHECKING ARCHIVED NARRATIVES (MongoDB)")
            print("=" * 80)
            
            # Get archived narratives (dormant or reactivated)
            archived_narratives = await narratives_collection.find(
                {"lifecycle_state": {"$in": ["dormant", "reactivated"]}}
            ).sort("last_updated", -1).limit(10).to_list(length=10)
            
            print(f"\nFound {len(archived_narratives)} archived narratives:")
            for narrative in archived_narratives:
                print(f"\n{'=' * 60}")
                print(f"ID: {narrative.get('_id')}")
                print(f"Title: {narrative.get('title')}")
                print(f"Lifecycle State: {narrative.get('lifecycle_state')}")
                print(f"Reawakening Count: {narrative.get('reawakening_count', 0)}")
                print(f"Last Updated: {narrative.get('last_updated')}")
                print(f"Article Count: {narrative.get('article_count', 0)}")
                
                # Check lifecycle history
                lifecycle_history = narrative.get('lifecycle_history', [])
                if lifecycle_history:
                    print(f"\nLifecycle History ({len(lifecycle_history)} entries):")
                    for entry in lifecycle_history[-5:]:  # Last 5 entries
                        print(f"  - {entry.get('timestamp')}: {entry.get('state')}")
            
            print("\n" + "=" * 80)
            print("3. SUMMARY")
            print("=" * 80)
            
            if total_tradingview > 0:
                print(f"\n⚠️  Found {total_tradingview} old TradingView article(s) to delete")
                if pg_tradingview_articles:
                    print("\nTo delete from PostgreSQL, run:")
                    for article in pg_tradingview_articles:
                        print(f"  DELETE FROM articles WHERE id = {article.id};")
                if mongo_tradingview_articles:
                    print("\nTo delete from MongoDB, run:")
                    for article in mongo_tradingview_articles:
                        print(f"  db.articles.deleteOne({{_id: ObjectId('{article.get('_id')}')}});")
            else:
                print("\n✓ No old TradingView articles found")
            
            dormant_count = sum(1 for n in archived_narratives if n.get('lifecycle_state') == 'dormant')
            reactivated_count = sum(1 for n in archived_narratives if n.get('lifecycle_state') == 'reactivated')
            
            print(f"\nArchived narratives breakdown:")
            print(f"  - Dormant: {dormant_count}")
            print(f"  - Reactivated: {reactivated_count}")
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
