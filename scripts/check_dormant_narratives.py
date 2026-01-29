#!/usr/bin/env python3
"""
Direct MongoDB query to check for dormant narratives.

Queries the database directly to verify what narratives exist and their lifecycle states.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from crypto_news_aggregator.db.mongodb import mongo_manager


async def check_dormant_narratives():
    """Query MongoDB directly for dormant narratives."""
    
    print("=" * 80)
    print("DIRECT MONGODB QUERY FOR DORMANT NARRATIVES")
    print("=" * 80)
    print()
    
    try:
        # Get database connection
        db = await mongo_manager.get_async_database()
        collection = db.narratives
        
        # 1. Total narratives count
        total_count = await collection.count_documents({})
        print(f"Total narratives in database: {total_count}")
        print()
        
        # 2. Check lifecycle_state field existence
        with_lifecycle_state = await collection.count_documents({"lifecycle_state": {"$exists": True}})
        without_lifecycle_state = total_count - with_lifecycle_state
        
        print(f"Narratives with lifecycle_state field: {with_lifecycle_state}")
        print(f"Narratives without lifecycle_state field: {without_lifecycle_state}")
        print()
        
        # 3. Lifecycle state distribution
        print("=" * 80)
        print("LIFECYCLE STATE DISTRIBUTION")
        print("=" * 80)
        
        pipeline = [
            {"$group": {"_id": "$lifecycle_state", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        
        async for doc in collection.aggregate(pipeline):
            state = doc['_id'] if doc['_id'] is not None else 'null/missing'
            count = doc['count']
            print(f"  {state}: {count}")
        
        print()
        
        # 4. Query for dormant narratives
        print("=" * 80)
        print("DORMANT NARRATIVES (lifecycle_state='dormant')")
        print("=" * 80)
        print()
        
        dormant_count = await collection.count_documents({"lifecycle_state": "dormant"})
        print(f"Total dormant narratives: {dormant_count}")
        print()
        
        if dormant_count > 0:
            # Get dormant narratives with details
            cursor = collection.find({"lifecycle_state": "dormant"}).sort("last_updated", -1).limit(10)
            
            print("Top 10 most recently updated dormant narratives:")
            print()
            
            async for i, narrative in enumerate(cursor, 1):
                title = narrative.get('title') or narrative.get('theme', 'N/A')
                article_count = narrative.get('article_count', 0)
                last_updated = narrative.get('last_updated')
                first_seen = narrative.get('first_seen')
                entities = narrative.get('entities', [])
                reawakening_count = narrative.get('reawakening_count', 0)
                
                print(f"{i}. {title}")
                print(f"   Article Count: {article_count}")
                print(f"   Entities: {', '.join(entities[:5])}")
                print(f"   First Seen: {first_seen}")
                print(f"   Last Updated: {last_updated}")
                print(f"   Reawakening Count: {reawakening_count}")
                
                # Calculate days since last update
                if last_updated:
                    if last_updated.tzinfo is None:
                        last_updated = last_updated.replace(tzinfo=timezone.utc)
                    days_ago = (datetime.now(timezone.utc) - last_updated).days
                    print(f"   Days Since Update: {days_ago}")
                
                print()
        
        # 5. Check narratives within 30-day lookback window
        print("=" * 80)
        print("DORMANT NARRATIVES IN LAST 30 DAYS")
        print("=" * 80)
        print()
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
        query = {
            "lifecycle_state": "dormant",
            "last_updated": {"$gte": cutoff_date}
        }
        
        recent_dormant_count = await collection.count_documents(query)
        print(f"Dormant narratives updated in last 30 days: {recent_dormant_count}")
        print(f"Cutoff date: {cutoff_date}")
        print()
        
        if recent_dormant_count > 0:
            cursor = collection.find(query).sort("last_updated", -1).limit(5)
            
            print("Most recent dormant narratives (last 30 days):")
            print()
            
            async for i, narrative in enumerate(cursor, 1):
                title = narrative.get('title') or narrative.get('theme', 'N/A')
                article_count = narrative.get('article_count', 0)
                last_updated = narrative.get('last_updated')
                
                print(f"{i}. {title}")
                print(f"   Article Count: {article_count}")
                print(f"   Last Updated: {last_updated}")
                print()
        
        # 6. Check for the specific narrative with 2 articles
        print("=" * 80)
        print("NARRATIVES WITH EXACTLY 2 ARTICLES")
        print("=" * 80)
        print()
        
        two_article_narratives = await collection.count_documents({"article_count": 2})
        print(f"Total narratives with 2 articles: {two_article_narratives}")
        print()
        
        if two_article_narratives > 0:
            cursor = collection.find({"article_count": 2}).limit(5)
            
            async for i, narrative in enumerate(cursor, 1):
                title = narrative.get('title') or narrative.get('theme', 'N/A')
                lifecycle_state = narrative.get('lifecycle_state', 'N/A')
                last_updated = narrative.get('last_updated')
                
                print(f"{i}. {title}")
                print(f"   Lifecycle State: {lifecycle_state}")
                print(f"   Last Updated: {last_updated}")
                print()
        
        # 7. Check old schema narratives (without lifecycle_state)
        print("=" * 80)
        print("OLD SCHEMA NARRATIVES (no lifecycle_state field)")
        print("=" * 80)
        print()
        
        old_schema_count = await collection.count_documents({"lifecycle_state": {"$exists": False}})
        print(f"Total old schema narratives: {old_schema_count}")
        
        if old_schema_count > 0:
            cursor = collection.find({"lifecycle_state": {"$exists": False}}).limit(3)
            
            print("\nSample old schema narratives:")
            print()
            
            async for i, narrative in enumerate(cursor, 1):
                title = narrative.get('title') or narrative.get('theme', 'N/A')
                article_count = narrative.get('article_count', 0)
                lifecycle = narrative.get('lifecycle', 'N/A')
                
                print(f"{i}. {title}")
                print(f"   Article Count: {article_count}")
                print(f"   Old Lifecycle Field: {lifecycle}")
                print(f"   Has lifecycle_state: {narrative.get('lifecycle_state') is not None}")
                print()
    
    except Exception as e:
        print(f"✗ Error querying database: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(check_dormant_narratives())
