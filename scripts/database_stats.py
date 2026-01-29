#!/usr/bin/env python3
"""
Generate comprehensive statistics about narratives and entities in the database.

Shows:
- Narrative counts by lifecycle state
- Entity distribution and frequency
- Article coverage statistics
- Top narratives by article count
- Entity co-occurrence patterns
"""

import asyncio
import sys
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from crypto_news_aggregator.db.mongodb import mongo_manager


async def get_database_stats():
    """Generate comprehensive database statistics."""
    
    print("=" * 80)
    print("DATABASE STATISTICS - NARRATIVES & ENTITIES")
    print("=" * 80)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        db = await mongo_manager.get_async_database()
        narratives_collection = db.narratives
        articles_collection = db.articles
        
        # =====================================================================
        # NARRATIVE STATISTICS
        # =====================================================================
        
        print("=" * 80)
        print("📊 NARRATIVE STATISTICS")
        print("=" * 80)
        print()
        
        # Total narratives
        total_narratives = await narratives_collection.count_documents({})
        print(f"Total Narratives: {total_narratives}")
        print()
        
        # Lifecycle state distribution
        print("-" * 80)
        print("Lifecycle State Distribution")
        print("-" * 80)
        
        pipeline = [
            {"$group": {"_id": "$lifecycle_state", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        
        lifecycle_stats = []
        total_with_state = 0
        async for doc in narratives_collection.aggregate(pipeline):
            state = doc['_id'] if doc['_id'] is not None else 'null/missing'
            count = doc['count']
            lifecycle_stats.append((state, count))
            if doc['_id'] is not None:
                total_with_state += count
            percentage = (count / total_narratives * 100) if total_narratives > 0 else 0
            print(f"  {state:15s}: {count:4d} ({percentage:5.1f}%)")
        
        print()
        
        # Article count distribution
        print("-" * 80)
        print("Article Count Distribution")
        print("-" * 80)
        
        pipeline = [
            {"$group": {
                "_id": "$article_count",
                "count": {"$sum": 1}
            }},
            {"$sort": {"_id": 1}}
        ]
        
        article_count_stats = []
        async for doc in narratives_collection.aggregate(pipeline):
            articles = doc['_id'] if doc['_id'] is not None else 0
            count = doc['count']
            article_count_stats.append((articles, count))
        
        # Group into ranges
        ranges = {
            '1 article': 0,
            '2-5 articles': 0,
            '6-10 articles': 0,
            '11-20 articles': 0,
            '21-50 articles': 0,
            '51+ articles': 0
        }
        
        for articles, count in article_count_stats:
            if articles == 1:
                ranges['1 article'] += count
            elif 2 <= articles <= 5:
                ranges['2-5 articles'] += count
            elif 6 <= articles <= 10:
                ranges['6-10 articles'] += count
            elif 11 <= articles <= 20:
                ranges['11-20 articles'] += count
            elif 21 <= articles <= 50:
                ranges['21-50 articles'] += count
            else:
                ranges['51+ articles'] += count
        
        for range_name, count in ranges.items():
            percentage = (count / total_narratives * 100) if total_narratives > 0 else 0
            print(f"  {range_name:20s}: {count:4d} ({percentage:5.1f}%)")
        
        print()
        
        # Top narratives by article count
        print("-" * 80)
        print("Top 10 Narratives by Article Count")
        print("-" * 80)
        
        cursor = narratives_collection.find().sort("article_count", -1).limit(10)
        top_narratives = await cursor.to_list(length=10)
        
        for i, narrative in enumerate(top_narratives, 1):
            title = narrative.get('title') or narrative.get('theme') or narrative.get('nucleus_entity', 'N/A')
            article_count = narrative.get('article_count', 0)
            lifecycle = narrative.get('lifecycle_state', 'N/A')
            entities = narrative.get('entities', [])
            entity_str = ', '.join(entities[:3]) if entities else 'N/A'
            
            print(f"{i:2d}. {title[:50]:50s} | {article_count:3d} articles | {lifecycle:10s}")
            print(f"    Entities: {entity_str}")
        
        print()
        
        # Recent activity
        print("-" * 80)
        print("Recent Activity (Last 7 Days)")
        print("-" * 80)
        
        cutoff_7d = datetime.now(timezone.utc) - timedelta(days=7)
        recent_narratives = await narratives_collection.count_documents({
            "last_updated": {"$gte": cutoff_7d}
        })
        
        percentage = (recent_narratives / total_narratives * 100) if total_narratives > 0 else 0
        print(f"  Narratives updated in last 7 days: {recent_narratives} ({percentage:.1f}%)")
        
        # New narratives
        new_narratives = await narratives_collection.count_documents({
            "created_at": {"$gte": cutoff_7d}
        })
        print(f"  New narratives created in last 7 days: {new_narratives}")
        
        print()
        
        # =====================================================================
        # ENTITY STATISTICS
        # =====================================================================
        
        print("=" * 80)
        print("🏷️  ENTITY STATISTICS")
        print("=" * 80)
        print()
        
        # Collect all entities from narratives
        all_entities = []
        entity_narrative_map = defaultdict(list)
        
        cursor = narratives_collection.find({}, {"entities": 1, "title": 1, "theme": 1, "nucleus_entity": 1, "article_count": 1})
        async for narrative in cursor:
            entities = narrative.get('entities', [])
            narrative_title = narrative.get('title') or narrative.get('theme') or narrative.get('nucleus_entity', 'Unknown')
            
            for entity in entities:
                all_entities.append(entity)
                entity_narrative_map[entity].append({
                    'title': narrative_title,
                    'article_count': narrative.get('article_count', 0)
                })
        
        entity_counter = Counter(all_entities)
        total_entities = len(entity_counter)
        total_entity_mentions = sum(entity_counter.values())
        
        print(f"Total Unique Entities: {total_entities}")
        print(f"Total Entity Mentions: {total_entity_mentions}")
        print(f"Average Mentions per Entity: {total_entity_mentions / total_entities:.1f}" if total_entities > 0 else "N/A")
        print()
        
        # Top entities
        print("-" * 80)
        print("Top 20 Entities by Narrative Mentions")
        print("-" * 80)
        
        for i, (entity, count) in enumerate(entity_counter.most_common(20), 1):
            # Calculate total articles across all narratives for this entity
            total_articles = sum(n['article_count'] for n in entity_narrative_map[entity])
            print(f"{i:2d}. {entity:20s} | {count:3d} narratives | {total_articles:4d} total articles")
        
        print()
        
        # Entity distribution
        print("-" * 80)
        print("Entity Mention Distribution")
        print("-" * 80)
        
        mention_ranges = {
            '1 narrative': 0,
            '2-5 narratives': 0,
            '6-10 narratives': 0,
            '11-20 narratives': 0,
            '21+ narratives': 0
        }
        
        for entity, count in entity_counter.items():
            if count == 1:
                mention_ranges['1 narrative'] += 1
            elif 2 <= count <= 5:
                mention_ranges['2-5 narratives'] += 1
            elif 6 <= count <= 10:
                mention_ranges['6-10 narratives'] += 1
            elif 11 <= count <= 20:
                mention_ranges['11-20 narratives'] += 1
            else:
                mention_ranges['21+ narratives'] += 1
        
        for range_name, count in mention_ranges.items():
            percentage = (count / total_entities * 100) if total_entities > 0 else 0
            print(f"  {range_name:20s}: {count:4d} entities ({percentage:5.1f}%)")
        
        print()
        
        # =====================================================================
        # ARTICLE STATISTICS
        # =====================================================================
        
        print("=" * 80)
        print("📰 ARTICLE STATISTICS")
        print("=" * 80)
        print()
        
        total_articles = await articles_collection.count_documents({})
        print(f"Total Articles: {total_articles}")
        
        # Articles with narratives
        articles_with_narratives = await articles_collection.count_documents({
            "narrative_id": {"$exists": True, "$ne": None}
        })
        
        articles_without_narratives = total_articles - articles_with_narratives
        coverage_percentage = (articles_with_narratives / total_articles * 100) if total_articles > 0 else 0
        
        print(f"Articles in Narratives: {articles_with_narratives} ({coverage_percentage:.1f}%)")
        print(f"Articles Not in Narratives: {articles_without_narratives} ({100 - coverage_percentage:.1f}%)")
        print()
        
        # Recent articles
        recent_articles = await articles_collection.count_documents({
            "published_at": {"$gte": cutoff_7d}
        })
        print(f"Articles Published in Last 7 Days: {recent_articles}")
        
        # Source distribution
        print()
        print("-" * 80)
        print("Top 10 Sources by Article Count")
        print("-" * 80)
        
        pipeline = [
            {"$group": {"_id": "$source", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        
        async for doc in articles_collection.aggregate(pipeline):
            source = doc['_id'] if doc['_id'] else 'Unknown'
            count = doc['count']
            percentage = (count / total_articles * 100) if total_articles > 0 else 0
            print(f"  {source:30s}: {count:5d} ({percentage:5.1f}%)")
        
        print()
        
        # =====================================================================
        # ENTITY CO-OCCURRENCE
        # =====================================================================
        
        print("=" * 80)
        print("🔗 ENTITY CO-OCCURRENCE (Top Pairs)")
        print("=" * 80)
        print()
        
        # Find entities that frequently appear together
        co_occurrence = Counter()
        
        cursor = narratives_collection.find({}, {"entities": 1})
        async for narrative in cursor:
            entities = narrative.get('entities', [])
            # Create pairs
            for i in range(len(entities)):
                for j in range(i + 1, len(entities)):
                    pair = tuple(sorted([entities[i], entities[j]]))
                    co_occurrence[pair] += 1
        
        print("Top 15 Entity Pairs (appearing together in narratives)")
        print("-" * 80)
        
        for i, (pair, count) in enumerate(co_occurrence.most_common(15), 1):
            print(f"{i:2d}. {pair[0]:15s} + {pair[1]:15s} | {count:3d} narratives")
        
        print()
        
        # =====================================================================
        # SUMMARY
        # =====================================================================
        
        print("=" * 80)
        print("📈 SUMMARY")
        print("=" * 80)
        print()
        print(f"  Total Narratives:        {total_narratives:6d}")
        print(f"  Total Unique Entities:   {total_entities:6d}")
        print(f"  Total Articles:          {total_articles:6d}")
        print(f"  Article Coverage:        {coverage_percentage:6.1f}%")
        print(f"  Active (7d):             {recent_narratives:6d} narratives")
        print(f"  New (7d):                {new_narratives:6d} narratives")
        print()
        
        # Health indicators
        print("Health Indicators:")
        if coverage_percentage > 80:
            print("  ✅ Excellent article coverage (>80%)")
        elif coverage_percentage > 60:
            print("  ✓ Good article coverage (>60%)")
        else:
            print("  ⚠ Low article coverage (<60%) - consider running narrative detection")
        
        if recent_narratives / total_narratives > 0.3:
            print("  ✅ High recent activity (>30% updated in 7d)")
        elif recent_narratives / total_narratives > 0.1:
            print("  ✓ Moderate recent activity (>10% updated in 7d)")
        else:
            print("  ⚠ Low recent activity (<10% updated in 7d)")
        
        print()
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(get_database_stats())
