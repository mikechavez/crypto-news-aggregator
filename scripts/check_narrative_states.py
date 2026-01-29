#!/usr/bin/env python3
"""
Analyze narrative lifecycle states and date ranges in MongoDB.
Investigate why UI only shows 13 narratives when there should be 157 total.
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

def analyze_narrative_states():
    """Analyze narratives by lifecycle state and date ranges."""
    
    # Connect to MongoDB
    mongo_uri = os.getenv("MONGODB_URI")
    if not mongo_uri:
        print("ERROR: MONGODB_URI not found in environment variables")
        return
    
    client = MongoClient(mongo_uri)
    db = client["crypto_news"]
    narratives_collection = db.narratives
    
    print("=" * 80)
    print("NARRATIVE LIFECYCLE STATE ANALYSIS")
    print("=" * 80)
    print()
    
    # Total narratives count
    total_count = narratives_collection.count_documents({})
    print(f"📊 Total narratives in database: {total_count:,}")
    print()
    
    # Get all unique lifecycle states
    lifecycle_states = narratives_collection.distinct("lifecycle_state")
    print(f"🔄 Unique lifecycle states found: {lifecycle_states}")
    print()
    
    # Count narratives by lifecycle state
    print("=" * 80)
    print("NARRATIVES BY LIFECYCLE STATE")
    print("=" * 80)
    
    state_counts = {}
    for state in lifecycle_states:
        count = narratives_collection.count_documents({"lifecycle_state": state})
        state_counts[state] = count
        print(f"\n📌 {state or 'NULL/MISSING'}: {count:,} narratives")
    
    # Also check for narratives with no lifecycle_state field
    no_state_count = narratives_collection.count_documents({
        "lifecycle_state": {"$exists": False}
    })
    if no_state_count > 0:
        print(f"\n⚠️  No lifecycle_state field: {no_state_count:,} narratives")
        state_counts["NO_FIELD"] = no_state_count
    
    print()
    print()
    
    # Analyze each state in detail
    for state in lifecycle_states:
        if state is None:
            state_query = {"lifecycle_state": None}
            state_label = "NULL"
        else:
            state_query = {"lifecycle_state": state}
            state_label = state
        
        print("=" * 80)
        print(f"STATE: {state_label}")
        print("=" * 80)
        
        # Get date range for this state
        oldest = narratives_collection.find(
            state_query,
            {"title": 1, "first_seen": 1, "last_updated": 1}
        ).sort("first_seen", ASCENDING).limit(1)
        oldest = list(oldest)[0] if oldest else None
        
        newest = narratives_collection.find(
            state_query,
            {"title": 1, "first_seen": 1, "last_updated": 1}
        ).sort("last_updated", DESCENDING).limit(1)
        newest = list(newest)[0] if newest else None
        
        if oldest:
            first_seen = oldest.get("first_seen", "Unknown")
            if isinstance(first_seen, datetime):
                first_seen = first_seen.strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n📅 Oldest first_seen: {first_seen}")
            print(f"   Title: {oldest.get('title', 'No title')[:70]}")
        
        if newest:
            last_updated = newest.get("last_updated", "Unknown")
            if isinstance(last_updated, datetime):
                last_updated = last_updated.strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n📅 Most recent last_updated: {last_updated}")
            print(f"   Title: {newest.get('title', 'No title')[:70]}")
        
        # Get 3 example narratives from this state
        print(f"\n📋 Sample narratives (3 examples):")
        examples = narratives_collection.find(
            state_query,
            {"title": 1, "first_seen": 1, "last_updated": 1, "article_count": 1}
        ).sort("last_updated", DESCENDING).limit(3)
        
        for i, narrative in enumerate(examples, 1):
            last_updated = narrative.get("last_updated", "Unknown")
            if isinstance(last_updated, datetime):
                last_updated = last_updated.strftime("%Y-%m-%d %H:%M:%S")
            
            first_seen = narrative.get("first_seen", "Unknown")
            if isinstance(first_seen, datetime):
                first_seen = first_seen.strftime("%Y-%m-%d %H:%M:%S")
            
            article_count = narrative.get("article_count", 0)
            
            print(f"\n   {i}. {narrative.get('title', 'No title')[:70]}")
            print(f"      First seen: {first_seen}")
            print(f"      Last updated: {last_updated}")
            print(f"      Articles: {article_count}")
        
        print()
    
    # Check for narratives with no lifecycle_state field
    if no_state_count > 0:
        print("=" * 80)
        print("STATE: NO LIFECYCLE_STATE FIELD")
        print("=" * 80)
        
        examples = narratives_collection.find(
            {"lifecycle_state": {"$exists": False}},
            {"title": 1, "first_seen": 1, "last_updated": 1, "article_count": 1}
        ).sort("last_updated", DESCENDING).limit(5)
        
        print(f"\n⚠️  Found {no_state_count} narratives without lifecycle_state field")
        print("\n📋 Sample narratives:")
        
        for i, narrative in enumerate(examples, 1):
            last_updated = narrative.get("last_updated", "Unknown")
            if isinstance(last_updated, datetime):
                last_updated = last_updated.strftime("%Y-%m-%d %H:%M:%S")
            
            print(f"\n   {i}. {narrative.get('title', 'No title')[:70]}")
            print(f"      Last updated: {last_updated}")
            print(f"      Articles: {narrative.get('article_count', 0)}")
        
        print()
    
    print()
    print("=" * 80)
    print("DATE FILTERING ANALYSIS")
    print("=" * 80)
    print()
    
    # Check how many narratives were updated in the last 7 days
    from datetime import timedelta
    now = datetime.utcnow()
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)
    
    recent_7d = narratives_collection.count_documents({
        "last_updated": {"$gte": seven_days_ago}
    })
    recent_30d = narratives_collection.count_documents({
        "last_updated": {"$gte": thirty_days_ago}
    })
    
    print(f"📅 Narratives updated in last 7 days: {recent_7d:,}")
    print(f"📅 Narratives updated in last 30 days: {recent_30d:,}")
    print(f"📅 Narratives older than 30 days: {total_count - recent_30d:,}")
    print()
    
    # Check if there are narratives with very old last_updated dates
    very_old = narratives_collection.find(
        {},
        {"title": 1, "last_updated": 1, "lifecycle_state": 1}
    ).sort("last_updated", ASCENDING).limit(5)
    
    print("🕰️  Oldest narratives by last_updated:")
    for i, narrative in enumerate(very_old, 1):
        last_updated = narrative.get("last_updated", "Unknown")
        if isinstance(last_updated, datetime):
            last_updated = last_updated.strftime("%Y-%m-%d %H:%M:%S")
        
        print(f"\n   {i}. {narrative.get('title', 'No title')[:70]}")
        print(f"      Last updated: {last_updated}")
        print(f"      State: {narrative.get('lifecycle_state', 'N/A')}")
    
    print()
    print("=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    
    client.close()

if __name__ == "__main__":
    analyze_narrative_states()
