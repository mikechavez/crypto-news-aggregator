#!/usr/bin/env python3
"""
Check narrative data coverage in MongoDB articles collection.
Shows counts and examples of articles with/without narrative assignments.
"""
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from pymongo import MongoClient, DESCENDING, ASCENDING
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_narrative_coverage():
    """Check how many articles have narrative data vs don't."""
    
    # Connect to MongoDB
    mongo_uri = os.getenv("MONGODB_URI")
    if not mongo_uri:
        print("ERROR: MONGODB_URI not found in environment variables")
        return
    
    client = MongoClient(mongo_uri)
    db = client["crypto_news"]
    articles_collection = db.articles
    
    print("=" * 80)
    print("NARRATIVE DATA COVERAGE ANALYSIS")
    print("=" * 80)
    print()
    
    # Total articles count
    total_count = articles_collection.count_documents({})
    print(f"📊 Total articles in database: {total_count:,}")
    print()
    
    # Count articles WITH narrative_summary (exists and not empty)
    with_narrative = articles_collection.count_documents({
        "narrative_summary": {"$exists": True, "$ne": None, "$ne": ""}
    })
    
    # Count articles WITHOUT narrative_summary (missing, null, or empty)
    without_narrative = articles_collection.count_documents({
        "$or": [
            {"narrative_summary": {"$exists": False}},
            {"narrative_summary": None},
            {"narrative_summary": ""}
        ]
    })
    
    print("-" * 80)
    print("COVERAGE SUMMARY")
    print("-" * 80)
    print(f"✅ Articles WITH narrative_summary: {with_narrative:,} ({with_narrative/total_count*100:.1f}%)")
    print(f"❌ Articles WITHOUT narrative_summary: {without_narrative:,} ({without_narrative/total_count*100:.1f}%)")
    print()
    
    # Get examples of articles WITH narrative_summary
    print("=" * 80)
    print("SAMPLE ARTICLES WITH NARRATIVE DATA (5 most recent)")
    print("=" * 80)
    with_examples = articles_collection.find(
        {"narrative_summary": {"$exists": True, "$ne": None, "$ne": ""}},
        {"title": 1, "published_at": 1, "narrative_summary": 1, "source": 1}
    ).sort("published_at", DESCENDING).limit(5)
    
    for i, article in enumerate(with_examples, 1):
        pub_date = article.get("published_at", "Unknown")
        if isinstance(pub_date, datetime):
            pub_date = pub_date.strftime("%Y-%m-%d %H:%M:%S")
        
        print(f"\n{i}. {article.get('title', 'No title')[:80]}")
        print(f"   📅 Published: {pub_date}")
        print(f"   🔗 Source: {article.get('source', 'Unknown')}")
        print(f"   📝 Narrative: {article.get('narrative_summary', '')[:100]}...")
    
    print()
    print()
    
    # Get examples of articles WITHOUT narrative_summary
    print("=" * 80)
    print("SAMPLE ARTICLES WITHOUT NARRATIVE DATA (5 most recent)")
    print("=" * 80)
    without_examples = articles_collection.find(
        {
            "$or": [
                {"narrative_summary": {"$exists": False}},
                {"narrative_summary": None},
                {"narrative_summary": ""}
            ]
        },
        {"title": 1, "published_at": 1, "source": 1}
    ).sort("published_at", DESCENDING).limit(5)
    
    for i, article in enumerate(without_examples, 1):
        pub_date = article.get("published_at", "Unknown")
        if isinstance(pub_date, datetime):
            pub_date = pub_date.strftime("%Y-%m-%d %H:%M:%S")
        
        print(f"\n{i}. {article.get('title', 'No title')[:80]}")
        print(f"   📅 Published: {pub_date}")
        print(f"   🔗 Source: {article.get('source', 'Unknown')}")
    
    print()
    print()
    
    # Date range analysis for articles WITHOUT narrative data
    print("=" * 80)
    print("DATE RANGE ANALYSIS - ARTICLES WITHOUT NARRATIVE DATA")
    print("=" * 80)
    
    # Get oldest and newest articles without narrative data
    oldest_without = articles_collection.find(
        {
            "$or": [
                {"narrative_summary": {"$exists": False}},
                {"narrative_summary": None},
                {"narrative_summary": ""}
            ]
        },
        {"title": 1, "published_at": 1}
    ).sort("published_at", ASCENDING).limit(1)
    oldest_without = list(oldest_without)[0] if oldest_without else None
    
    newest_without = articles_collection.find(
        {
            "$or": [
                {"narrative_summary": {"$exists": False}},
                {"narrative_summary": None},
                {"narrative_summary": ""}
            ]
        },
        {"title": 1, "published_at": 1}
    ).sort("published_at", DESCENDING).limit(1)
    newest_without = list(newest_without)[0] if newest_without else None
    
    if oldest_without:
        oldest_date = oldest_without.get("published_at", "Unknown")
        if isinstance(oldest_date, datetime):
            oldest_date = oldest_date.strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n📅 Oldest article without narrative: {oldest_date}")
        print(f"   Title: {oldest_without.get('title', 'No title')[:80]}")
    
    if newest_without:
        newest_date = newest_without.get("published_at", "Unknown")
        if isinstance(newest_date, datetime):
            newest_date = newest_date.strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n📅 Newest article without narrative: {newest_date}")
        print(f"   Title: {newest_without.get('title', 'No title')[:80]}")
    
    print()
    print()
    
    # Date range analysis for articles WITH narrative data
    print("=" * 80)
    print("DATE RANGE ANALYSIS - ARTICLES WITH NARRATIVE DATA")
    print("=" * 80)
    
    oldest_with = articles_collection.find(
        {"narrative_summary": {"$exists": True, "$ne": None, "$ne": ""}},
        {"title": 1, "published_at": 1}
    ).sort("published_at", ASCENDING).limit(1)
    oldest_with = list(oldest_with)[0] if oldest_with else None
    
    newest_with = articles_collection.find(
        {"narrative_summary": {"$exists": True, "$ne": None, "$ne": ""}},
        {"title": 1, "published_at": 1}
    ).sort("published_at", DESCENDING).limit(1)
    newest_with = list(newest_with)[0] if newest_with else None
    
    if oldest_with:
        oldest_date = oldest_with.get("published_at", "Unknown")
        if isinstance(oldest_date, datetime):
            oldest_date = oldest_date.strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n📅 Oldest article with narrative: {oldest_date}")
        print(f"   Title: {oldest_with.get('title', 'No title')[:80]}")
    
    if newest_with:
        newest_date = newest_with.get("published_at", "Unknown")
        if isinstance(newest_date, datetime):
            newest_date = newest_date.strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n📅 Newest article with narrative: {newest_date}")
        print(f"   Title: {newest_with.get('title', 'No title')[:80]}")
    
    print()
    print("=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    
    client.close()

if __name__ == "__main__":
    check_narrative_coverage()
