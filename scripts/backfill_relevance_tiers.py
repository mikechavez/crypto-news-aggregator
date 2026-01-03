#!/usr/bin/env python3
"""
Backfill relevance_tier for existing articles.

This script classifies all articles that don't have a relevance_tier set.
It's safe to run multiple times - it only processes unclassified articles.

Usage:
    poetry run python scripts/backfill_relevance_tiers.py [--dry-run] [--limit N]

Options:
    --dry-run    Show what would be done without making changes
    --limit N    Only process N articles (useful for testing)
"""

import asyncio
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from motor.motor_asyncio import AsyncIOMotorClient
from src.crypto_news_aggregator.core.config import settings
from src.crypto_news_aggregator.services.relevance_classifier import classify_article


async def backfill_relevance_tiers(dry_run: bool = False, limit: int = None):
    """
    Backfill relevance_tier for all articles missing it.

    Args:
        dry_run: If True, don't actually update, just show what would happen
        limit: If set, only process this many articles
    """
    # Connect to MongoDB
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_NAME]
    collection = db.articles

    print(f"Connected to MongoDB: {settings.MONGODB_NAME}")

    # Query for articles without relevance_tier
    query = {
        "$or": [
            {"relevance_tier": {"$exists": False}},
            {"relevance_tier": None},
        ]
    }

    # Count total articles to process
    total_count = await collection.count_documents(query)
    print(f"\nFound {total_count} articles without relevance_tier")

    if limit:
        print(f"Limiting to {limit} articles")
        total_count = min(total_count, limit)

    if total_count == 0:
        print("Nothing to do!")
        return

    if dry_run:
        print("\n🔍 DRY RUN - No changes will be made\n")

    # Track tier distribution
    tier_counts = {1: 0, 2: 0, 3: 0}
    tier_examples = {1: [], 2: [], 3: []}  # Store example titles per tier
    processed = 0
    errors = 0

    # Process in batches to avoid cursor timeout (Atlas limitation)
    batch_size = 500
    remaining = limit if limit else total_count

    while remaining > 0:
        # Fetch a batch of articles
        fetch_size = min(batch_size, remaining)
        cursor = collection.find(query).limit(fetch_size)
        articles = await cursor.to_list(length=fetch_size)

        if not articles:
            break  # No more articles to process

        batch_updates = []

        for article in articles:
            article_id = article.get("_id")
            title = article.get("title", "")
            text = article.get("text") or article.get("content") or article.get("description") or ""
            source = article.get("source", "")

            try:
                # Classify the article
                classification = classify_article(
                    title=title,
                    text=text[:1000],  # First 1000 chars
                    source=source
                )

                tier = classification["tier"]
                reason = classification["reason"]

                tier_counts[tier] += 1

                # Store examples (first 3 per tier)
                if len(tier_examples[tier]) < 3:
                    tier_examples[tier].append({
                        "title": title[:60] + "..." if len(title) > 60 else title,
                        "reason": reason,
                    })

                if not dry_run:
                    batch_updates.append({
                        "filter": {"_id": article_id},
                        "update": {
                            "$set": {
                                "relevance_tier": tier,
                                "relevance_reason": reason,
                                "updated_at": datetime.now(timezone.utc),
                            }
                        }
                    })

                processed += 1

            except Exception as e:
                errors += 1
                print(f"  Error processing article {article_id}: {e}")

        # Execute batch updates
        if batch_updates and not dry_run:
            for update in batch_updates:
                await collection.update_one(update["filter"], update["update"])

        remaining -= len(articles)

        # Progress update
        pct = (processed / total_count) * 100
        print(f"  Processed {processed}/{total_count} ({pct:.1f}%)")

    # Print summary
    print("\n" + "=" * 60)
    print("BACKFILL SUMMARY")
    print("=" * 60)

    print(f"\nProcessed: {processed} articles")
    if errors:
        print(f"Errors: {errors}")

    print(f"\n📊 Tier Distribution:")
    print(f"  🔥 Tier 1 (High):   {tier_counts[1]:>5} ({tier_counts[1]/max(1,processed)*100:.1f}%)")
    print(f"  📰 Tier 2 (Medium): {tier_counts[2]:>5} ({tier_counts[2]/max(1,processed)*100:.1f}%)")
    print(f"  🔇 Tier 3 (Low):    {tier_counts[3]:>5} ({tier_counts[3]/max(1,processed)*100:.1f}%)")

    print("\n📝 Example Classifications:")
    for tier in [1, 2, 3]:
        tier_label = {1: "HIGH", 2: "MEDIUM", 3: "LOW"}[tier]
        print(f"\n  Tier {tier} ({tier_label}):")
        for ex in tier_examples[tier]:
            print(f"    - {ex['title']}")
            print(f"      Reason: {ex['reason']}")

    if dry_run:
        print("\n⚠️  DRY RUN - No changes were made")
        print("   Run without --dry-run to apply changes")
    else:
        print(f"\n✅ Updated {processed} articles in database")

    # Close connection
    client.close()


def main():
    parser = argparse.ArgumentParser(
        description="Backfill relevance_tier for existing articles"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only process N articles (useful for testing)"
    )

    args = parser.parse_args()

    asyncio.run(backfill_relevance_tiers(
        dry_run=args.dry_run,
        limit=args.limit
    ))


if __name__ == "__main__":
    main()
