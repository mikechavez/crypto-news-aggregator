#!/usr/bin/env python3
"""
Test script to verify signals filtering by relevance tier.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient
from crypto_news_aggregator.core.config import settings


async def test_signals_filtering():
    """Test that signals are filtering by relevance tier correctly."""

    # Connect to MongoDB
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_NAME]

    print("=" * 80)
    print("SIGNALS RELEVANCE FILTERING TEST")
    print("=" * 80)
    print()

    # 1. Check article relevance tier distribution
    print("1. Article Relevance Tier Distribution")
    print("-" * 80)

    pipeline = [
        {
            "$group": {
                "_id": "$relevance_tier",
                "count": {"$sum": 1}
            }
        },
        {"$sort": {"_id": 1}}
    ]

    total_articles = 0
    tier_counts = {}
    async for doc in db.articles.aggregate(pipeline):
        tier = doc["_id"]
        count = doc["count"]
        tier_counts[tier] = count
        total_articles += count

        tier_label = f"Tier {tier}" if tier else "Unclassified"
        print(f"  {tier_label}: {count:,} articles")

    print(f"\n  Total: {total_articles:,} articles")

    if tier_counts:
        tier1_pct = (tier_counts.get(1, 0) / total_articles * 100) if total_articles > 0 else 0
        tier2_pct = (tier_counts.get(2, 0) / total_articles * 100) if total_articles > 0 else 0
        tier3_pct = (tier_counts.get(3, 0) / total_articles * 100) if total_articles > 0 else 0
        print(f"\n  Distribution:")
        print(f"    Tier 1 (High):   {tier1_pct:5.1f}%")
        print(f"    Tier 2 (Medium): {tier2_pct:5.1f}%")
        print(f"    Tier 3 (Low):    {tier3_pct:5.1f}%")

    print()

    # 2. Check entity mentions by tier
    print("2. Entity Mentions by Article Relevance Tier")
    print("-" * 80)

    # Get sample entity with mentions
    sample_entity = await db.entity_mentions.find_one(
        {"is_primary": True},
        sort=[("created_at", -1)]
    )

    if sample_entity:
        entity_name = sample_entity["entity"]
        print(f"  Testing with entity: {entity_name}")
        print()

        # Get all mentions for this entity
        mention_pipeline = [
            {"$match": {"entity": entity_name, "is_primary": True}},
            {
                "$lookup": {
                    "from": "articles",
                    "localField": "article_id",
                    "foreignField": "_id",
                    "as": "article"
                }
            },
            {"$unwind": "$article"},
            {
                "$group": {
                    "_id": "$article.relevance_tier",
                    "count": {"$sum": 1}
                }
            },
            {"$sort": {"_id": 1}}
        ]

        total_mentions = 0
        tier_mention_counts = {}
        async for doc in db.entity_mentions.aggregate(mention_pipeline):
            tier = doc["_id"]
            count = doc["count"]
            tier_mention_counts[tier] = count
            total_mentions += count

            tier_label = f"Tier {tier}" if tier else "Unclassified"
            print(f"    Mentions in {tier_label}: {count}")

        print(f"\n    Total mentions: {total_mentions}")

        # Calculate what should be filtered
        filtered_out = tier_mention_counts.get(3, 0)
        included = total_mentions - filtered_out

        print(f"\n    Included in signals (Tier 1-2): {included}")
        print(f"    Filtered out (Tier 3): {filtered_out}")

    print()

    # 3. Sample some Tier 3 articles to verify they're correctly classified
    print("3. Sample Tier 3 (Low Signal) Articles")
    print("-" * 80)

    tier3_cursor = db.articles.find(
        {"relevance_tier": 3},
        {"title": 1, "relevance_reason": 1}
    ).limit(5)

    tier3_count = 0
    async for article in tier3_cursor:
        tier3_count += 1
        print(f"  {tier3_count}. {article.get('title', 'No title')[:70]}")
        if article.get('relevance_reason'):
            print(f"     Reason: {article['relevance_reason']}")
        print()

    if tier3_count == 0:
        print("  No Tier 3 articles found")

    print()

    # 4. Check recent signal scores
    print("4. Recent Signal Scores (Top 10)")
    print("-" * 80)

    signal_cursor = db.signal_scores.find().sort([("score", -1)]).limit(10)

    signal_count = 0
    async for signal in signal_cursor:
        signal_count += 1
        entity = signal.get("entity", "Unknown")
        score = signal.get("signal_score", 0)
        mentions = signal.get("mention_count", 0)
        velocity = signal.get("velocity", 0)

        print(f"  {signal_count}. {entity}")
        print(f"     Score: {score:.1f}, Mentions: {mentions}, Velocity: {velocity:.1f}")

    if signal_count == 0:
        print("  No signal scores found")

    print()
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

    # Cleanup
    client.close()


if __name__ == "__main__":
    asyncio.run(test_signals_filtering())
