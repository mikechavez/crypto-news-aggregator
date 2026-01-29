#!/usr/bin/env python3
"""
Comprehensive analysis of the archive tab issue.

This script combines database queries and API tests to pinpoint the exact issue.
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from crypto_news_aggregator.db.mongodb import mongo_manager
import httpx
import json


async def analyze_archive_issue():
    """Comprehensive analysis of archive tab issue."""
    
    print("=" * 80)
    print("ARCHIVE TAB ISSUE ANALYSIS")
    print("=" * 80)
    print()
    
    # Part 1: Database Analysis
    print("PART 1: DATABASE ANALYSIS")
    print("-" * 80)
    
    try:
        db = await mongo_manager.get_async_database()
        collection = db.narratives
        
        # Total narratives
        total = await collection.count_documents({})
        print(f"Total narratives: {total}")
        
        # Lifecycle state distribution
        pipeline = [
            {"$group": {"_id": "$lifecycle_state", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        
        print("\nLifecycle state distribution:")
        lifecycle_dist = {}
        async for doc in collection.aggregate(pipeline):
            state = doc['_id'] if doc['_id'] is not None else 'null/missing'
            count = doc['count']
            lifecycle_dist[state] = count
            print(f"  {state}: {count}")
        
        # Dormant narratives
        dormant_count = await collection.count_documents({"lifecycle_state": "dormant"})
        print(f"\nDormant narratives: {dormant_count}")
        
        # Dormant narratives in last 30 days
        cutoff_30 = datetime.now(timezone.utc) - timedelta(days=30)
        recent_dormant = await collection.count_documents({
            "lifecycle_state": "dormant",
            "last_updated": {"$gte": cutoff_30}
        })
        print(f"Dormant narratives (last 30 days): {recent_dormant}")
        
        # Narratives with exactly 2 articles
        two_articles = await collection.count_documents({"article_count": 2})
        print(f"\nNarratives with 2 articles: {two_articles}")
        
        if two_articles > 0:
            print("\nNarratives with 2 articles (details):")
            cursor = collection.find({"article_count": 2}).limit(5)
            i = 1
            async for n in cursor:
                title = n.get('title') or n.get('theme', 'N/A')
                state = n.get('lifecycle_state', 'N/A')
                last_updated = n.get('last_updated')
                print(f"  {i}. {title}")
                print(f"     State: {state}, Last Updated: {last_updated}")
                i += 1
        
        print()
        
    except Exception as e:
        print(f"✗ Database error: {e}")
        import traceback
        traceback.print_exc()
    
    # Part 2: API Test
    print("\nPART 2: API ENDPOINT TEST")
    print("-" * 80)
    
    api_url = os.getenv("API_URL", "http://localhost:8000")
    endpoint = f"{api_url}/api/v1/narratives/archived"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            params = {"limit": 50, "days": 30}
            response = await client.get(endpoint, params=params)
            
            if response.status_code == 200:
                narratives = response.json()
                print(f"API returned: {len(narratives)} narratives")
                
                if narratives:
                    # Count total articles
                    total_articles = sum(n.get('article_count', 0) for n in narratives)
                    print(f"Total articles across all narratives: {total_articles}")
                    
                    # Show first few narratives
                    print("\nFirst 3 narratives:")
                    for i, n in enumerate(narratives[:3], 1):
                        print(f"  {i}. {n.get('title', 'N/A')}")
                        print(f"     Articles: {n.get('article_count', 0)}")
                        print(f"     State: {n.get('lifecycle_state', 'N/A')}")
                else:
                    print("⚠ API returned 0 narratives")
            else:
                print(f"✗ API error: {response.status_code}")
                print(f"Response: {response.text}")
    
    except Exception as e:
        print(f"✗ API test error: {e}")
        import traceback
        traceback.print_exc()
    
    # Part 3: Diagnosis
    print("\n" + "=" * 80)
    print("DIAGNOSIS")
    print("=" * 80)
    
    # Determine the issue
    if dormant_count == 0:
        print("\n❌ ISSUE IDENTIFIED: No dormant narratives in database")
        print("\nPossible causes:")
        print("  1. Lifecycle system not marking narratives as dormant")
        print("  2. All narratives are in other states (emerging, rising, etc.)")
        print("\nSolution:")
        print("  - Check lifecycle transition logic")
        print("  - Run lifecycle state backfill if needed")
        
    elif recent_dormant == 0:
        print("\n❌ ISSUE IDENTIFIED: Dormant narratives exist but none in last 30 days")
        print(f"\nTotal dormant: {dormant_count}")
        print(f"Recent dormant: {recent_dormant}")
        print("\nSolution:")
        print("  - Increase the 'days' parameter in the frontend")
        print("  - Or check why dormant narratives aren't being updated")
        
    elif 'null/missing' in lifecycle_dist and lifecycle_dist['null/missing'] > 0:
        print("\n⚠ WARNING: Some narratives missing lifecycle_state field")
        print(f"\nNarratives without lifecycle_state: {lifecycle_dist['null/missing']}")
        print("\nThese narratives won't appear in archive tab.")
        print("\nSolution:")
        print("  - Run migration to add lifecycle_state to old narratives")
        
    else:
        print("\n✓ Database has dormant narratives")
        print(f"  Dormant: {dormant_count}")
        print(f"  Recent (30d): {recent_dormant}")
        print("\nIf archive tab is still empty, check:")
        print("  1. Frontend console logs")
        print("  2. Network tab for API response")
        print("  3. Frontend rendering logic")
    
    # Check for the "2 articles" mystery
    if two_articles > 0:
        print("\n" + "=" * 80)
        print("'2 ARTICLES' INVESTIGATION")
        print("=" * 80)
        
        # Check if any of the 2-article narratives are dormant
        two_article_dormant = await collection.count_documents({
            "article_count": 2,
            "lifecycle_state": "dormant"
        })
        
        print(f"\nNarratives with 2 articles AND dormant state: {two_article_dormant}")
        
        if two_article_dormant > 0:
            print("\n✓ Found dormant narrative(s) with 2 articles!")
            print("This could be what's showing '2 articles' in the UI.")
            
            cursor = collection.find({
                "article_count": 2,
                "lifecycle_state": "dormant"
            }).limit(1)
            
            async for n in cursor:
                title = n.get('title') or n.get('theme', 'N/A')
                last_updated = n.get('last_updated')
                
                print(f"\nNarrative: {title}")
                print(f"Last Updated: {last_updated}")
                
                # Check if it's in the 30-day window
                if last_updated:
                    if last_updated.tzinfo is None:
                        last_updated = last_updated.replace(tzinfo=timezone.utc)
                    days_ago = (datetime.now(timezone.utc) - last_updated).days
                    
                    if days_ago <= 30:
                        print(f"✓ Within 30-day window (updated {days_ago} days ago)")
                        print("\nThis narrative SHOULD appear in archive tab.")
                        print("If it's not showing, check frontend rendering.")
                    else:
                        print(f"✗ Outside 30-day window (updated {days_ago} days ago)")
                        print("\nThis narrative won't appear in archive tab.")
                        print("Increase 'days' parameter to see it.")
        else:
            print("\n⚠ No dormant narratives with 2 articles")
            print("The '2 articles' count might be from:")
            print("  - A non-dormant narrative")
            print("  - The resurrection summary card")
            print("  - A different UI element")
    
    print("\n" + "=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print("\n1. Review the diagnosis above")
    print("2. Check browser console for frontend logs")
    print("3. Check Railway logs for backend logs")
    print("4. See ARCHIVE_TAB_DEBUG_SUMMARY.md for detailed guide")
    print()


if __name__ == "__main__":
    asyncio.run(analyze_archive_issue())
