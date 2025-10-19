#!/usr/bin/env python3
"""
Analyze narrative distribution and show helpful statistics.

Shows:
- Total narrative count
- Distribution by nucleus_entity
- Distribution by lifecycle_state
- Article count statistics
- Top narratives by article count
- Recent activity patterns
"""

import asyncio
import sys
import os
from typing import List, Dict, Any
from datetime import datetime, timezone, timedelta
from collections import Counter, defaultdict

# Add src to path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, os.path.join(project_root, "src"))

from crypto_news_aggregator.db.mongodb import mongo_manager


async def get_all_narratives() -> List[Dict[str, Any]]:
    """Get all narratives from database."""
    db = await mongo_manager.get_async_database()
    narratives_collection = db.narratives
    
    cursor = narratives_collection.find({})
    narratives = []
    async for narrative in cursor:
        narratives.append(narrative)
    
    return narratives


def analyze_narratives(narratives: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze narrative distribution and statistics."""
    
    # Basic counts
    total_count = len(narratives)
    
    # Extract nucleus entities
    nucleus_entities = []
    for narrative in narratives:
        fingerprint = narrative.get('narrative_fingerprint') or narrative.get('fingerprint')
        if fingerprint:
            nucleus = fingerprint.get('nucleus_entity')
            if nucleus:
                nucleus_entities.append(nucleus)
    
    # Lifecycle states
    lifecycle_states = [n.get('lifecycle_state', 'unknown') for n in narratives]
    
    # Article counts
    article_counts = [len(n.get('article_ids', [])) for n in narratives]
    
    # Merged narratives
    merged_count = sum(1 for n in narratives if n.get('merged_at'))
    backfilled_count = sum(1 for n in narratives if n.get('fingerprint_backfilled_at'))
    
    # Recent activity (last 7 days)
    now = datetime.now(timezone.utc)
    recent_cutoff = now - timedelta(days=7)
    recent_narratives = []
    for n in narratives:
        last_updated = n.get('last_updated')
        if last_updated:
            if last_updated.tzinfo is None:
                last_updated = last_updated.replace(tzinfo=timezone.utc)
            if last_updated >= recent_cutoff:
                recent_narratives.append(n)
    
    # Top narratives by article count
    narratives_with_counts = [
        (n.get('title', 'Unknown'), len(n.get('article_ids', [])), n.get('lifecycle_state', 'unknown'))
        for n in narratives
    ]
    top_narratives = sorted(narratives_with_counts, key=lambda x: x[1], reverse=True)[:10]
    
    return {
        'total_count': total_count,
        'nucleus_entities': nucleus_entities,
        'lifecycle_states': lifecycle_states,
        'article_counts': article_counts,
        'merged_count': merged_count,
        'backfilled_count': backfilled_count,
        'recent_narratives': recent_narratives,
        'top_narratives': top_narratives
    }


def print_distribution(stats: Dict[str, Any]):
    """Print narrative distribution and statistics."""
    
    print("=" * 70)
    print("NARRATIVE DISTRIBUTION ANALYSIS")
    print("=" * 70)
    
    # Overall statistics
    print(f"\n📊 OVERALL STATISTICS")
    print(f"{'─' * 70}")
    print(f"Total narratives:              {stats['total_count']}")
    print(f"Narratives with fingerprints:  {len(stats['nucleus_entities'])}")
    print(f"Backfilled narratives:         {stats['backfilled_count']}")
    print(f"Merged narratives:             {stats['merged_count']}")
    print(f"Active (last 7 days):          {len(stats['recent_narratives'])}")
    
    # Nucleus entity distribution
    print(f"\n🎯 TOP 20 NUCLEUS ENTITIES")
    print(f"{'─' * 70}")
    nucleus_counter = Counter(stats['nucleus_entities'])
    for i, (nucleus, count) in enumerate(nucleus_counter.most_common(20), 1):
        bar = '█' * min(count, 50)
        print(f"{i:2}. {nucleus[:30]:30} {count:3} {bar}")
    
    if len(nucleus_counter) > 20:
        print(f"\n    ... and {len(nucleus_counter) - 20} more nucleus entities")
    
    # Lifecycle state distribution
    print(f"\n🔄 LIFECYCLE STATE DISTRIBUTION")
    print(f"{'─' * 70}")
    lifecycle_counter = Counter(stats['lifecycle_states'])
    lifecycle_order = ['emerging', 'rising', 'hot', 'cooling', 'dormant', 'echo', 'reactivated', 'unknown']
    
    for state in lifecycle_order:
        count = lifecycle_counter.get(state, 0)
        if count > 0:
            percentage = (count / stats['total_count']) * 100
            bar = '█' * int(percentage / 2)
            print(f"{state:12} {count:3} ({percentage:5.1f}%) {bar}")
    
    # Article count statistics
    print(f"\n📰 ARTICLE COUNT STATISTICS")
    print(f"{'─' * 70}")
    article_counts = stats['article_counts']
    if article_counts:
        total_articles = sum(article_counts)
        avg_articles = total_articles / len(article_counts)
        min_articles = min(article_counts)
        max_articles = max(article_counts)
        
        print(f"Total articles:                {total_articles:,}")
        print(f"Average per narrative:         {avg_articles:.1f}")
        print(f"Min articles:                  {min_articles}")
        print(f"Max articles:                  {max_articles}")
        
        # Distribution buckets
        buckets = {
            '1-3 articles': sum(1 for c in article_counts if 1 <= c <= 3),
            '4-6 articles': sum(1 for c in article_counts if 4 <= c <= 6),
            '7-10 articles': sum(1 for c in article_counts if 7 <= c <= 10),
            '11-20 articles': sum(1 for c in article_counts if 11 <= c <= 20),
            '21+ articles': sum(1 for c in article_counts if c >= 21)
        }
        
        print(f"\nDistribution:")
        for bucket, count in buckets.items():
            percentage = (count / stats['total_count']) * 100
            bar = '█' * int(percentage / 2)
            print(f"  {bucket:15} {count:3} ({percentage:5.1f}%) {bar}")
    
    # Top narratives
    print(f"\n🏆 TOP 10 NARRATIVES BY ARTICLE COUNT")
    print(f"{'─' * 70}")
    for i, (title, count, state) in enumerate(stats['top_narratives'], 1):
        title_short = title[:50] + '...' if len(title) > 50 else title
        print(f"{i:2}. [{count:3} articles] {title_short}")
        print(f"    State: {state}")
    
    # Recent activity
    print(f"\n⚡ RECENT ACTIVITY (LAST 7 DAYS)")
    print(f"{'─' * 70}")
    recent = stats['recent_narratives']
    if recent:
        recent_lifecycle = Counter([n.get('lifecycle_state', 'unknown') for n in recent])
        print(f"Active narratives:             {len(recent)}")
        print(f"Percentage of total:           {(len(recent) / stats['total_count']) * 100:.1f}%")
        print(f"\nRecent by lifecycle state:")
        for state, count in recent_lifecycle.most_common():
            print(f"  {state:12} {count:3}")
    else:
        print("No recent activity in last 7 days")
    
    # Nucleus entity diversity
    print(f"\n🌈 NUCLEUS ENTITY DIVERSITY")
    print(f"{'─' * 70}")
    unique_nucleus = len(nucleus_counter)
    print(f"Unique nucleus entities:       {unique_nucleus}")
    print(f"Average narratives per entity: {stats['total_count'] / unique_nucleus:.1f}")
    
    # Concentration analysis
    top_10_count = sum(count for _, count in nucleus_counter.most_common(10))
    top_10_pct = (top_10_count / stats['total_count']) * 100
    print(f"Top 10 entities represent:     {top_10_pct:.1f}% of narratives")
    
    # Duplicates check
    duplicates = [(nucleus, count) for nucleus, count in nucleus_counter.items() if count > 1]
    if duplicates:
        print(f"\n⚠️  POTENTIAL DUPLICATES")
        print(f"{'─' * 70}")
        print(f"Nucleus entities with 2+ narratives: {len(duplicates)}")
        print(f"\nTop duplicates:")
        for nucleus, count in sorted(duplicates, key=lambda x: x[1], reverse=True)[:5]:
            print(f"  {nucleus[:40]:40} {count} narratives")
    
    print(f"\n{'=' * 70}")


async def main():
    """Main entry point."""
    try:
        print("🔌 Connecting to MongoDB...")
        await mongo_manager.initialize()
        
        print("📊 Fetching narratives...")
        narratives = await get_all_narratives()
        
        if not narratives:
            print("✅ No narratives found.")
            return
        
        print(f"📊 Analyzing {len(narratives)} narratives...\n")
        stats = analyze_narratives(narratives)
        
        print_distribution(stats)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        print("\n🔌 Closing MongoDB connection...")
        await mongo_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
