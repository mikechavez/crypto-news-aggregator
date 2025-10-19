#!/usr/bin/env python3
"""
Analyze temporal distribution of narratives - how long they stretch over time.

Shows:
- Time span of narratives (first article to last article)
- Age of narratives (created_at to now)
- Activity patterns over time
- Velocity and momentum metrics
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


async def get_narratives_with_articles() -> List[Dict[str, Any]]:
    """Get all narratives with their article dates."""
    db = await mongo_manager.get_async_database()
    narratives_collection = db.narratives
    articles_collection = db.articles
    
    cursor = narratives_collection.find({})
    narratives = []
    
    async for narrative in cursor:
        article_ids = narrative.get('article_ids', [])
        
        if article_ids:
            # Fetch article dates
            from bson import ObjectId
            object_ids = []
            for aid in article_ids:
                if isinstance(aid, str) and ObjectId.is_valid(aid):
                    object_ids.append(ObjectId(aid))
                elif isinstance(aid, ObjectId):
                    object_ids.append(aid)
            
            article_cursor = articles_collection.find(
                {'_id': {'$in': object_ids}},
                {'published_at': 1}
            )
            
            article_dates = []
            async for article in article_cursor:
                pub_date = article.get('published_at')
                if pub_date:
                    if pub_date.tzinfo is None:
                        pub_date = pub_date.replace(tzinfo=timezone.utc)
                    article_dates.append(pub_date)
            
            narrative['article_dates'] = sorted(article_dates)
        else:
            narrative['article_dates'] = []
        
        narratives.append(narrative)
    
    return narratives


def analyze_temporal_distribution(narratives: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze temporal patterns of narratives."""
    
    now = datetime.now(timezone.utc)
    
    # Time span analysis (first article to last article)
    time_spans = []
    narrative_ages = []
    velocities = []
    
    for narrative in narratives:
        article_dates = narrative.get('article_dates', [])
        created_at = narrative.get('created_at')
        
        if created_at and created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        
        if article_dates and len(article_dates) >= 2:
            # Time span: first article to last article
            first_article = min(article_dates)
            last_article = max(article_dates)
            span_days = (last_article - first_article).total_seconds() / 86400
            time_spans.append({
                'narrative': narrative,
                'span_days': span_days,
                'first_article': first_article,
                'last_article': last_article,
                'article_count': len(article_dates)
            })
            
            # Velocity: articles per day
            if span_days > 0:
                velocity = len(article_dates) / span_days
                velocities.append(velocity)
        
        # Narrative age: created_at to now
        if created_at:
            age_days = (now - created_at).total_seconds() / 86400
            narrative_ages.append({
                'narrative': narrative,
                'age_days': age_days,
                'created_at': created_at
            })
    
    # Recency analysis
    recency_buckets = {
        'Last 24h': [],
        'Last 3 days': [],
        'Last 7 days': [],
        'Last 14 days': [],
        'Last 30 days': [],
        'Older': []
    }
    
    for narrative in narratives:
        last_updated = narrative.get('last_updated')
        if last_updated:
            if last_updated.tzinfo is None:
                last_updated = last_updated.replace(tzinfo=timezone.utc)
            
            days_ago = (now - last_updated).total_seconds() / 86400
            
            if days_ago < 1:
                recency_buckets['Last 24h'].append(narrative)
            elif days_ago < 3:
                recency_buckets['Last 3 days'].append(narrative)
            elif days_ago < 7:
                recency_buckets['Last 7 days'].append(narrative)
            elif days_ago < 14:
                recency_buckets['Last 14 days'].append(narrative)
            elif days_ago < 30:
                recency_buckets['Last 30 days'].append(narrative)
            else:
                recency_buckets['Older'].append(narrative)
    
    return {
        'time_spans': sorted(time_spans, key=lambda x: x['span_days'], reverse=True),
        'narrative_ages': sorted(narrative_ages, key=lambda x: x['age_days'], reverse=True),
        'velocities': velocities,
        'recency_buckets': recency_buckets,
        'total_narratives': len(narratives)
    }


def print_temporal_analysis(stats: Dict[str, Any]):
    """Print temporal distribution analysis."""
    
    print("=" * 80)
    print("NARRATIVE TEMPORAL DISTRIBUTION ANALYSIS")
    print("=" * 80)
    
    # Time span statistics
    time_spans = stats['time_spans']
    if time_spans:
        print(f"\n📏 TIME SPAN STATISTICS (First Article → Last Article)")
        print(f"{'─' * 80}")
        
        span_days = [ts['span_days'] for ts in time_spans]
        avg_span = sum(span_days) / len(span_days)
        max_span = max(span_days)
        min_span = min(span_days)
        
        print(f"Average time span:         {avg_span:.1f} days")
        print(f"Longest narrative:         {max_span:.1f} days")
        print(f"Shortest narrative:        {min_span:.1f} days")
        
        # Distribution buckets
        span_buckets = {
            '< 1 day': sum(1 for s in span_days if s < 1),
            '1-3 days': sum(1 for s in span_days if 1 <= s < 3),
            '3-7 days': sum(1 for s in span_days if 3 <= s < 7),
            '7-14 days': sum(1 for s in span_days if 7 <= s < 14),
            '14-30 days': sum(1 for s in span_days if 14 <= s < 30),
            '30+ days': sum(1 for s in span_days if s >= 30)
        }
        
        print(f"\nTime Span Distribution:")
        for bucket, count in span_buckets.items():
            percentage = (count / len(time_spans)) * 100
            bar = '█' * int(percentage / 2)
            print(f"  {bucket:12} {count:3} ({percentage:5.1f}%) {bar}")
        
        # Top 10 longest narratives
        print(f"\n🏆 TOP 10 LONGEST-RUNNING NARRATIVES")
        print(f"{'─' * 80}")
        for i, ts in enumerate(time_spans[:10], 1):
            narrative = ts['narrative']
            title = narrative.get('title', 'Unknown')[:50]
            span = ts['span_days']
            articles = ts['article_count']
            first = ts['first_article'].strftime('%Y-%m-%d')
            last = ts['last_article'].strftime('%Y-%m-%d')
            
            print(f"{i:2}. {title}...")
            print(f"    Span: {span:.1f} days ({first} → {last})")
            print(f"    Articles: {articles} ({articles/span:.2f} per day)")
    
    # Narrative age statistics
    narrative_ages = stats['narrative_ages']
    if narrative_ages:
        print(f"\n📅 NARRATIVE AGE STATISTICS (Created → Now)")
        print(f"{'─' * 80}")
        
        ages = [na['age_days'] for na in narrative_ages]
        avg_age = sum(ages) / len(ages)
        max_age = max(ages)
        min_age = min(ages)
        
        print(f"Average age:               {avg_age:.1f} days")
        print(f"Oldest narrative:          {max_age:.1f} days")
        print(f"Newest narrative:          {min_age:.1f} days")
        
        # Age distribution
        age_buckets = {
            '< 1 day': sum(1 for a in ages if a < 1),
            '1-3 days': sum(1 for a in ages if 1 <= a < 3),
            '3-7 days': sum(1 for a in ages if 3 <= a < 7),
            '7-14 days': sum(1 for a in ages if 7 <= a < 14),
            '14-30 days': sum(1 for a in ages if 14 <= a < 30),
            '30+ days': sum(1 for a in ages if a >= 30)
        }
        
        print(f"\nAge Distribution:")
        for bucket, count in age_buckets.items():
            percentage = (count / len(narrative_ages)) * 100
            bar = '█' * int(percentage / 2)
            print(f"  {bucket:12} {count:3} ({percentage:5.1f}%) {bar}")
    
    # Velocity statistics
    velocities = stats['velocities']
    if velocities:
        print(f"\n⚡ VELOCITY STATISTICS (Articles per Day)")
        print(f"{'─' * 80}")
        
        avg_velocity = sum(velocities) / len(velocities)
        max_velocity = max(velocities)
        min_velocity = min(velocities)
        
        print(f"Average velocity:          {avg_velocity:.2f} articles/day")
        print(f"Highest velocity:          {max_velocity:.2f} articles/day")
        print(f"Lowest velocity:           {min_velocity:.2f} articles/day")
        
        # Velocity buckets
        velocity_buckets = {
            '< 0.5/day (slow)': sum(1 for v in velocities if v < 0.5),
            '0.5-1/day (moderate)': sum(1 for v in velocities if 0.5 <= v < 1),
            '1-2/day (active)': sum(1 for v in velocities if 1 <= v < 2),
            '2-5/day (hot)': sum(1 for v in velocities if 2 <= v < 5),
            '5+/day (explosive)': sum(1 for v in velocities if v >= 5)
        }
        
        print(f"\nVelocity Distribution:")
        for bucket, count in velocity_buckets.items():
            percentage = (count / len(velocities)) * 100
            bar = '█' * int(percentage / 2)
            print(f"  {bucket:22} {count:3} ({percentage:5.1f}%) {bar}")
        
        # Top 10 fastest narratives
        print(f"\n🚀 TOP 10 FASTEST-MOVING NARRATIVES")
        print(f"{'─' * 80}")
        time_spans_with_velocity = [
            (ts, ts['article_count'] / ts['span_days'] if ts['span_days'] > 0 else 0)
            for ts in stats['time_spans']
        ]
        sorted_by_velocity = sorted(time_spans_with_velocity, key=lambda x: x[1], reverse=True)
        
        for i, (ts, velocity) in enumerate(sorted_by_velocity[:10], 1):
            narrative = ts['narrative']
            title = narrative.get('title', 'Unknown')[:50]
            articles = ts['article_count']
            span = ts['span_days']
            
            print(f"{i:2}. {title}...")
            print(f"    Velocity: {velocity:.2f} articles/day ({articles} articles over {span:.1f} days)")
    
    # Recency analysis
    recency_buckets = stats['recency_buckets']
    print(f"\n🕐 RECENCY ANALYSIS (Last Updated)")
    print(f"{'─' * 80}")
    
    total = stats['total_narratives']
    for bucket_name, narratives in recency_buckets.items():
        count = len(narratives)
        percentage = (count / total) * 100 if total > 0 else 0
        bar = '█' * int(percentage / 2)
        print(f"{bucket_name:15} {count:3} ({percentage:5.1f}%) {bar}")
    
    # Activity concentration
    print(f"\n📊 ACTIVITY CONCENTRATION")
    print(f"{'─' * 80}")
    recent_count = len(recency_buckets['Last 24h']) + len(recency_buckets['Last 3 days'])
    recent_pct = (recent_count / total) * 100 if total > 0 else 0
    print(f"Active in last 3 days:     {recent_count} ({recent_pct:.1f}%)")
    
    week_count = recent_count + len(recency_buckets['Last 7 days'])
    week_pct = (week_count / total) * 100 if total > 0 else 0
    print(f"Active in last 7 days:     {week_count} ({week_pct:.1f}%)")
    
    month_count = week_count + len(recency_buckets['Last 14 days']) + len(recency_buckets['Last 30 days'])
    month_pct = (month_count / total) * 100 if total > 0 else 0
    print(f"Active in last 30 days:    {month_count} ({month_pct:.1f}%)")
    
    stale_count = len(recency_buckets['Older'])
    stale_pct = (stale_count / total) * 100 if total > 0 else 0
    print(f"Stale (>30 days):          {stale_count} ({stale_pct:.1f}%)")
    
    print(f"\n{'=' * 80}")


async def main():
    """Main entry point."""
    try:
        print("🔌 Connecting to MongoDB...")
        await mongo_manager.initialize()
        
        print("📊 Fetching narratives with article dates...")
        narratives = await get_narratives_with_articles()
        
        if not narratives:
            print("✅ No narratives found.")
            return
        
        print(f"📊 Analyzing temporal distribution of {len(narratives)} narratives...\n")
        stats = analyze_temporal_distribution(narratives)
        
        print_temporal_analysis(stats)
        
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
