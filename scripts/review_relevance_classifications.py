#!/usr/bin/env python3
"""
Review and analyze relevance classifications of articles.

This script helps identify patterns in article classifications to tune the
relevance classifier. It queries articles by tier and displays them in a
human-readable format for review.

Usage:
    poetry run python scripts/review_relevance_classifications.py [options]

Options:
    --tier {1,2,3}  Filter by specific tier (default: all)
    --limit N       Number of articles to review (default: 50)
    --offset N      Skip first N articles (default: 0)
    --reason REASON Filter by classification reason
    --no-pattern    Show only articles with no matched pattern
    --export FILE   Export results to JSON file
"""

import asyncio
import json
import argparse
from typing import Optional, List
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from crypto_news_aggregator.db.mongodb import mongo_manager
from crypto_news_aggregator.services.relevance_classifier import get_classifier
from loguru import logger


async def query_articles_by_tier(
    tier: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
    reason: Optional[str] = None,
    days_back: int = 30,
) -> List[dict]:
    """
    Query articles from MongoDB filtered by tier and other criteria.

    Args:
        tier: Filter by relevance_tier (1, 2, or 3), or None for all
        limit: Maximum number of articles to return
        offset: Number of articles to skip
        reason: Filter by relevance_reason
        days_back: Only include articles from last N days

    Returns:
        List of article documents
    """
    db = await mongo_manager.get_async_database()
    collection = db.articles

    # Build query filter
    query = {}

    # Filter by date
    cutoff_date = datetime.utcnow() - timedelta(days=days_back)
    query["published_at"] = {"$gte": cutoff_date}

    # Filter by tier if specified
    if tier is not None:
        query["relevance_tier"] = tier

    # Filter by reason if specified
    if reason is not None:
        query["relevance_reason"] = reason

    # Query articles
    logger.info(f"Querying articles with filter: {query}")
    articles = await collection.find(query)\
        .sort("published_at", -1)\
        .skip(offset)\
        .limit(limit)\
        .to_list(limit)

    logger.info(f"Found {len(articles)} articles")
    return articles


async def analyze_article_classifications(articles: List[dict]) -> dict:
    """
    Analyze classification distribution and identify patterns.

    Args:
        articles: List of article documents

    Returns:
        Dictionary with analysis results
    """
    stats = {
        "total": len(articles),
        "by_tier": {1: 0, 2: 0, 3: 0},
        "by_reason": {},
        "patterns": {},
        "unclassified": 0,
    }

    for article in articles:
        tier = article.get("relevance_tier")
        reason = article.get("relevance_reason", "unknown")
        pattern = article.get("relevance_reason")

        if tier:
            stats["by_tier"][tier] = stats["by_tier"].get(tier, 0) + 1
        else:
            stats["unclassified"] += 1

        stats["by_reason"][reason] = stats["by_reason"].get(reason, 0) + 1

    return stats


def display_article(
    article: dict,
    index: int,
    show_metadata: bool = False
) -> None:
    """
    Display an article in human-readable format.

    Args:
        article: Article document
        index: Article index in current batch
        show_metadata: Whether to show additional metadata
    """
    title = article.get("title", "N/A")
    source = article.get("source", "N/A")
    tier = article.get("relevance_tier", "?")
    reason = article.get("relevance_reason", "unknown")
    url = article.get("url", "")

    # Color codes for tiers (ANSI)
    tier_colors = {
        1: "\033[92m",  # Green
        2: "\033[94m",  # Blue
        3: "\033[93m",  # Yellow
    }
    reset = "\033[0m"

    color = tier_colors.get(tier, "")

    print(f"\n{index + 1}. [{color}Tier {tier}{reset}] {reason}")
    print(f"   Title: {title}")
    print(f"   Source: {source}")
    if show_metadata:
        published = article.get("published_at", "N/A")
        print(f"   Published: {published}")
        print(f"   URL: {url}")


async def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Review and analyze article relevance classifications"
    )
    parser.add_argument(
        "--tier",
        type=int,
        choices=[1, 2, 3],
        help="Filter by specific relevance tier"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Number of articles to review (default: 50)"
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Skip first N articles (default: 0)"
    )
    parser.add_argument(
        "--reason",
        type=str,
        help="Filter by classification reason"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Only include articles from last N days (default: 30)"
    )
    parser.add_argument(
        "--export",
        type=str,
        help="Export results to JSON file"
    )
    parser.add_argument(
        "--metadata",
        action="store_true",
        help="Show additional metadata for each article"
    )
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Only show statistics, don't display articles"
    )

    args = parser.parse_args()

    # Query articles
    logger.info(f"Querying articles (limit={args.limit}, offset={args.offset})")
    articles = await query_articles_by_tier(
        tier=args.tier,
        limit=args.limit,
        offset=args.offset,
        reason=args.reason,
        days_back=args.days,
    )

    # Analyze classifications
    stats = await analyze_article_classifications(articles)

    # Display statistics
    print(f"\n{'='*70}")
    print(f"Article Classification Review")
    print(f"{'='*70}")
    print(f"\nTotal articles: {stats['total']}")
    print(f"Unclassified: {stats['unclassified']}")
    print(f"\nBy Tier:")
    for tier in [1, 2, 3]:
        count = stats["by_tier"][tier]
        pct = (count / stats["total"] * 100) if stats["total"] > 0 else 0
        print(f"  Tier {tier}: {count:3d} ({pct:5.1f}%)")

    print(f"\nBy Reason:")
    for reason, count in sorted(stats["by_reason"].items(), key=lambda x: -x[1]):
        pct = (count / stats["total"] * 100) if stats["total"] > 0 else 0
        print(f"  {reason:25s}: {count:3d} ({pct:5.1f}%)")

    # Display articles unless stats-only
    if not args.stats_only:
        print(f"\n{'='*70}")
        print(f"Articles (Tier: {args.tier or 'All'}, Reason: {args.reason or 'All'})")
        print(f"{'='*70}")

        for i, article in enumerate(articles):
            display_article(article, i, show_metadata=args.metadata)

    # Export if requested
    if args.export:
        export_path = Path(args.export)
        export_data = {
            "metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "total": stats["total"],
                "tier_filter": args.tier,
                "reason_filter": args.reason,
            },
            "statistics": stats,
            "articles": [
                {
                    "title": a.get("title"),
                    "source": a.get("source"),
                    "tier": a.get("relevance_tier"),
                    "reason": a.get("relevance_reason"),
                    "url": a.get("url"),
                    "published_at": str(a.get("published_at")),
                }
                for a in articles
            ]
        }
        export_path.write_text(json.dumps(export_data, indent=2))
        logger.info(f"Exported results to {export_path}")

    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    asyncio.run(main())
