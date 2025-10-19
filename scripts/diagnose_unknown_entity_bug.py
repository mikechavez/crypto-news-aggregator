#!/usr/bin/env python3
"""
Diagnostic script to investigate the "Unknown" nucleus_entity bug.

This script queries narratives from the database and analyzes:
1. How many have empty/missing nucleus_entity vs actual values
2. What their fingerprints show
3. What their article data shows
4. When and how they were created
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from collections import Counter
from dotenv import load_dotenv

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.crypto_news_aggregator.db.mongodb import mongo_manager

# Load environment variables
load_dotenv()


async def diagnose_unknown_entity_bug():
    """Run diagnostic analysis on nucleus_entity field."""
    
    print("=" * 80)
    print("🔍 DIAGNOSING 'Unknown' NUCLEUS_ENTITY BUG")
    print("=" * 80)
    
    try:
        await mongo_manager.initialize()
        db = await mongo_manager.get_async_database()
        narratives_collection = db.narratives
        articles_collection = db.articles
        
        # Count narratives by nucleus_entity status
        total_narratives = await narratives_collection.count_documents({})
        empty_string = await narratives_collection.count_documents({'nucleus_entity': ''})
        missing_field = await narratives_collection.count_documents({'nucleus_entity': {'$exists': False}})
        null_value = await narratives_collection.count_documents({'nucleus_entity': None})
        actual_values = await narratives_collection.count_documents({
            'nucleus_entity': {'$ne': '', '$ne': None, '$exists': True}
        })
        
        print(f"\n📊 NUCLEUS_ENTITY STATISTICS:")
        print(f"  Total narratives: {total_narratives}")
        print(f"  Empty string (''): {empty_string}")
        print(f"  Missing field: {missing_field}")
        print(f"  Null value: {null_value}")
        print(f"  Actual values: {actual_values}")
        print(f"  Empty/Missing/Null total: {empty_string + missing_field + null_value}")
        
        # Query 5 narratives with empty/missing nucleus_entity
        print(f"\n" + "=" * 80)
        print("🔴 SAMPLE NARRATIVES WITH EMPTY/MISSING NUCLEUS_ENTITY:")
        print("=" * 80)
        
        empty_narratives = await narratives_collection.find({
            '$or': [
                {'nucleus_entity': ''},
                {'nucleus_entity': {'$exists': False}},
                {'nucleus_entity': None}
            ]
        }).limit(5).to_list(length=5)
        
        for i, narrative in enumerate(empty_narratives, 1):
            print(f"\n--- Narrative {i} ---")
            print(f"ID: {narrative['_id']}")
            print(f"Title: {narrative.get('title', 'N/A')}")
            print(f"nucleus_entity field: {repr(narrative.get('nucleus_entity', 'FIELD_MISSING'))}")
            print(f"Actors: {narrative.get('actors', [])[:5]}")  # First 5 actors
            print(f"Article Count: {narrative.get('article_count', 0)}")
            print(f"Created: {narrative.get('first_seen', 'N/A')}")
            
            # Check fingerprint
            fingerprint = narrative.get('fingerprint', {})
            if fingerprint:
                print(f"\n  Fingerprint:")
                print(f"    nucleus_entity: {repr(fingerprint.get('nucleus_entity', 'FIELD_MISSING'))}")
                print(f"    top_actors: {fingerprint.get('top_actors', [])}")
                print(f"    key_actions: {fingerprint.get('key_actions', [])}")
            else:
                print(f"  Fingerprint: MISSING")
            
            # Check one of the articles in this narrative
            article_ids = narrative.get('article_ids', [])
            if article_ids:
                from bson import ObjectId
                try:
                    article = await articles_collection.find_one({'_id': ObjectId(article_ids[0])})
                    if article:
                        print(f"\n  Sample Article (ID: {article_ids[0]}):")
                        print(f"    Title: {article.get('title', 'N/A')[:80]}")
                        print(f"    nucleus_entity: {repr(article.get('nucleus_entity', 'FIELD_MISSING'))}")
                        print(f"    actors: {article.get('actors', [])[:5]}")
                        print(f"    entities: {article.get('entities', [])[:5]}")
                except Exception as e:
                    print(f"  Could not fetch article: {e}")
        
        # Query 5 narratives with actual nucleus_entity values
        print(f"\n" + "=" * 80)
        print("🟢 SAMPLE NARRATIVES WITH ACTUAL NUCLEUS_ENTITY:")
        print("=" * 80)
        
        actual_narratives = await narratives_collection.find({
            'nucleus_entity': {'$ne': '', '$ne': None, '$exists': True}
        }).limit(5).to_list(length=5)
        
        for i, narrative in enumerate(actual_narratives, 1):
            print(f"\n--- Narrative {i} ---")
            print(f"ID: {narrative['_id']}")
            print(f"Title: {narrative.get('title', 'N/A')}")
            print(f"nucleus_entity field: {repr(narrative.get('nucleus_entity', 'FIELD_MISSING'))}")
            print(f"Actors: {narrative.get('actors', [])[:5]}")
            print(f"Article Count: {narrative.get('article_count', 0)}")
            print(f"Created: {narrative.get('first_seen', 'N/A')}")
            
            # Check fingerprint
            fingerprint = narrative.get('fingerprint', {})
            if fingerprint:
                print(f"\n  Fingerprint:")
                print(f"    nucleus_entity: {repr(fingerprint.get('nucleus_entity', 'FIELD_MISSING'))}")
                print(f"    top_actors: {fingerprint.get('top_actors', [])}")
                print(f"    key_actions: {fingerprint.get('key_actions', [])}")
            else:
                print(f"  Fingerprint: MISSING")
            
            # Check one of the articles in this narrative
            article_ids = narrative.get('article_ids', [])
            if article_ids:
                from bson import ObjectId
                try:
                    article = await articles_collection.find_one({'_id': ObjectId(article_ids[0])})
                    if article:
                        print(f"\n  Sample Article (ID: {article_ids[0]}):")
                        print(f"    Title: {article.get('title', 'N/A')[:80]}")
                        print(f"    nucleus_entity: {repr(article.get('nucleus_entity', 'FIELD_MISSING'))}")
                        print(f"    actors: {article.get('actors', [])[:5]}")
                        print(f"    entities: {article.get('entities', [])[:5]}")
                except Exception as e:
                    print(f"  Could not fetch article: {e}")
        
        # Analyze creation patterns
        print(f"\n" + "=" * 80)
        print("📅 CREATION TIMELINE ANALYSIS:")
        print("=" * 80)
        
        # Get all narratives sorted by creation date
        all_narratives = await narratives_collection.find({}).sort('first_seen', 1).to_list(length=None)
        
        if all_narratives:
            # Group by date and nucleus_entity status
            by_date = {}
            for n in all_narratives:
                created = n.get('first_seen')
                if created:
                    date_key = created.strftime('%Y-%m-%d')
                    if date_key not in by_date:
                        by_date[date_key] = {'empty': 0, 'actual': 0}
                    
                    nucleus = n.get('nucleus_entity', '')
                    if nucleus:
                        by_date[date_key]['actual'] += 1
                    else:
                        by_date[date_key]['empty'] += 1
            
            print(f"\nNarratives created by date:")
            for date_key in sorted(by_date.keys())[-10:]:  # Last 10 days
                stats = by_date[date_key]
                total = stats['empty'] + stats['actual']
                empty_pct = (stats['empty'] / total * 100) if total > 0 else 0
                print(f"  {date_key}: {total} total ({stats['empty']} empty [{empty_pct:.0f}%], {stats['actual']} actual)")
        
        # Check if there's a code change correlation
        print(f"\n" + "=" * 80)
        print("🔍 ROOT CAUSE ANALYSIS:")
        print("=" * 80)
        
        # Check a few narratives to see if nucleus_entity is in articles but not being propagated
        print("\nChecking if articles have nucleus_entity but narratives don't...")
        
        sample_empty = await narratives_collection.find_one({
            '$or': [
                {'nucleus_entity': ''},
                {'nucleus_entity': {'$exists': False}},
                {'nucleus_entity': None}
            ]
        })
        
        if sample_empty and sample_empty.get('article_ids'):
            from bson import ObjectId
            article_id = sample_empty['article_ids'][0]
            article = await articles_collection.find_one({'_id': ObjectId(article_id)})
            
            if article:
                article_nucleus = article.get('nucleus_entity', '')
                print(f"\nSample empty narrative: {sample_empty.get('title', 'N/A')}")
                print(f"  Narrative nucleus_entity: {repr(sample_empty.get('nucleus_entity', 'FIELD_MISSING'))}")
                print(f"  Article nucleus_entity: {repr(article_nucleus)}")
                
                if article_nucleus:
                    print(f"\n⚠️  FOUND THE BUG: Articles have nucleus_entity but it's not being set on narratives!")
                else:
                    print(f"\n  Both article and narrative are missing nucleus_entity")
        
        print(f"\n" + "=" * 80)
        print("💡 DIAGNOSIS SUMMARY:")
        print("=" * 80)
        
        if empty_string + missing_field + null_value > actual_values:
            print("\n🔴 CONFIRMED: Most narratives have empty/missing nucleus_entity")
            print("\nPossible causes:")
            print("  1. Articles don't have nucleus_entity set during entity extraction")
            print("  2. Narrative generation isn't reading nucleus_entity from articles")
            print("  3. compute_narrative_fingerprint is receiving empty cluster data")
            print("  4. Database update is overwriting nucleus_entity with empty value")
            print("\nNext steps:")
            print("  1. Check entity extraction in articles (nucleus_entity field)")
            print("  2. Verify cluster_by_narrative_salience aggregates nucleus_entity correctly")
            print("  3. Verify generate_narrative_from_cluster sets nucleus_entity from cluster")
            print("  4. Check if database updates preserve nucleus_entity")
        else:
            print("\n🟢 Most narratives have actual nucleus_entity values")
            print("The 'Unknown' count in the audit may be a display artifact")
        
    except Exception as e:
        print(f"\n❌ Error during diagnosis: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await mongo_manager.close()


if __name__ == '__main__':
    asyncio.run(diagnose_unknown_entity_bug())
