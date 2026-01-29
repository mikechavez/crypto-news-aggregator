#!/usr/bin/env python3
"""
Delete recent Benzinga articles and their associated data.

This script:
1. Queries Benzinga articles from the last 24 hours
2. Deletes entity_mentions for each article
3. Deletes the articles from the articles collection
4. Clears the signals cache to force UI refresh

Usage:
    python scripts/delete_recent_benzinga.py --dry-run  # Preview what will be deleted
    python scripts/delete_recent_benzinga.py --confirm  # Actually delete the data
"""

import asyncio
import argparse
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.crypto_news_aggregator.db.mongodb import mongo_manager, initialize_mongodb
from src.crypto_news_aggregator.db.operations.entity_mentions import delete_entity_mentions_for_articles
from src.crypto_news_aggregator.core.redis_rest_client import redis_client


async def get_recent_benzinga_articles(hours: int = 24) -> List[Dict[str, Any]]:
    """
    Query Benzinga articles from the last N hours.
    
    Args:
        hours: Number of hours to look back (default 24)
    
    Returns:
        List of article documents
    """
    db = await mongo_manager.get_async_database()
    collection = db.articles
    
    # Calculate cutoff time
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    # Query for Benzinga articles published after cutoff
    # Note: source is stored as a string, not an object with .id
    query = {
        "source": "benzinga",
        "published_at": {"$gte": cutoff_time}
    }
    
    cursor = collection.find(query).sort("published_at", -1)
    
    articles = []
    async for article in cursor:
        articles.append(article)
    
    return articles


async def delete_benzinga_articles(articles: List[Dict[str, Any]], dry_run: bool = True) -> Dict[str, int]:
    """
    Delete Benzinga articles and their associated entity mentions.
    
    Args:
        articles: List of article documents to delete
        dry_run: If True, don't actually delete (default True)
    
    Returns:
        Dict with counts of deleted items
    """
    db = await mongo_manager.get_async_database()
    articles_collection = db.articles
    
    stats = {
        "articles_deleted": 0,
        "entity_mentions_deleted": 0,
    }
    
    if not articles:
        return stats
    
    # Extract article IDs (convert ObjectId to string)
    article_ids = [str(article["_id"]) for article in articles]
    
    print(f"\n{'DRY RUN: Would delete' if dry_run else 'Deleting'} {len(article_ids)} articles...")
    
    # Delete entity_mentions for all articles
    if not dry_run:
        mentions_deleted = await delete_entity_mentions_for_articles(article_ids)
        stats["entity_mentions_deleted"] = mentions_deleted
        print(f"✅ Deleted {mentions_deleted} entity_mentions")
    else:
        # Count entity_mentions that would be deleted
        entity_mentions_collection = db.entity_mentions
        mentions_count = await entity_mentions_collection.count_documents(
            {"article_id": {"$in": article_ids}}
        )
        stats["entity_mentions_deleted"] = mentions_count
        print(f"DRY RUN: Would delete {mentions_count} entity_mentions")
    
    # Delete articles
    if not dry_run:
        # Convert string IDs back to ObjectIds for deletion
        from bson import ObjectId
        object_ids = [ObjectId(aid) for aid in article_ids]
        result = await articles_collection.delete_many({"_id": {"$in": object_ids}})
        stats["articles_deleted"] = result.deleted_count
        print(f"✅ Deleted {result.deleted_count} articles")
    else:
        stats["articles_deleted"] = len(article_ids)
        print(f"DRY RUN: Would delete {len(article_ids)} articles")
    
    return stats


async def clear_signals_cache():
    """
    Clear the signals cache to force UI refresh.
    
    Clears both Redis cache and in-memory cache patterns.
    """
    print("\nClearing signals cache...")
    
    # Clear Redis cache if available
    if redis_client.enabled:
        try:
            # Delete all keys matching the signals pattern
            # Note: This uses a pattern match which may not work on all Redis versions
            # Alternative: Just set a short TTL or delete specific known keys
            pattern = "signals:trending:*"
            
            # Get all matching keys
            keys = redis_client.keys(pattern)
            if keys:
                deleted = redis_client.delete(*keys)
                print(f"✅ Cleared {deleted} Redis cache entries")
            else:
                print("No Redis cache entries found")
        except Exception as e:
            print(f"⚠️  Warning: Could not clear Redis cache: {e}")
    else:
        print("Redis not enabled, skipping Redis cache clear")
    
    print("✅ Cache cleared (in-memory cache will auto-expire)")


async def recalculate_signal_scores(dry_run: bool = True):
    """
    Trigger signal score recalculation or cleanup.
    
    Note: This is a placeholder. In production, you would either:
    1. Run the cleanup_stale_signals.py script
    2. Trigger the signal calculation worker
    3. Wait for the next scheduled recalculation
    
    Args:
        dry_run: If True, just show what would happen
    """
    print("\n" + "="*70)
    print("SIGNAL SCORES UPDATE")
    print("="*70)
    
    if dry_run:
        print("\nDRY RUN: Signal scores would need to be recalculated.")
        print("Options after running with --confirm:")
        print("  1. Run: python scripts/cleanup_stale_signals.py --execute")
        print("  2. Wait for next scheduled signal calculation")
        print("  3. Manually trigger the signal calculation worker")
    else:
        print("\n⚠️  IMPORTANT: Signal scores need to be updated!")
        print("\nRecommended next steps:")
        print("  1. Run: python scripts/cleanup_stale_signals.py --execute")
        print("     This will remove stale signal_scores for deleted entities")
        print("  2. Or wait for the next scheduled signal calculation")


async def main():
    parser = argparse.ArgumentParser(
        description="Delete recent Benzinga articles and associated data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview what will be deleted (default)
  python scripts/delete_recent_benzinga.py --dry-run
  
  # Delete articles from last 24 hours
  python scripts/delete_recent_benzinga.py --confirm
  
  # Delete articles from last 48 hours
  python scripts/delete_recent_benzinga.py --confirm --hours 48
        """
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Show what would be deleted without actually deleting (default)"
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Actually delete the data (overrides --dry-run)"
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        help="Number of hours to look back (default: 24)"
    )
    
    args = parser.parse_args()
    
    # If --confirm is specified, turn off dry_run
    dry_run = not args.confirm
    
    # Initialize MongoDB
    await initialize_mongodb()
    
    try:
        print("="*70)
        print("DELETE RECENT BENZINGA ARTICLES")
        print("="*70)
        print(f"\nLooking for Benzinga articles from the last {args.hours} hours...")
        
        if dry_run:
            print("\n🔍 DRY RUN MODE - No data will be deleted\n")
        else:
            print("\n⚠️  LIVE MODE - Data will be permanently deleted\n")
            response = input("Are you sure you want to delete Benzinga articles? (yes/no): ")
            if response.lower() != "yes":
                print("Aborted")
                return
        
        # Get recent Benzinga articles
        articles = await get_recent_benzinga_articles(hours=args.hours)
        
        if not articles:
            print(f"\n✅ No Benzinga articles found in the last {args.hours} hours")
            return
        
        # Display article details
        print(f"\nFound {len(articles)} Benzinga articles:")
        print("-" * 70)
        for i, article in enumerate(articles, 1):
            title = article.get("title", "No title")
            published = article.get("published_at", "Unknown date")
            if isinstance(published, datetime):
                published = published.strftime("%Y-%m-%d %H:%M:%S UTC")
            print(f"{i}. {title}")
            print(f"   Published: {published}")
            print(f"   URL: {article.get('url', 'No URL')}")
        print("-" * 70)
        
        # Delete articles and entity_mentions
        stats = await delete_benzinga_articles(articles, dry_run=dry_run)
        
        # Clear signals cache
        if not dry_run:
            await clear_signals_cache()
        else:
            print("\nDRY RUN: Would clear signals cache")
        
        # Show summary
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        print(f"Articles {'that would be deleted' if dry_run else 'deleted'}: {stats['articles_deleted']}")
        print(f"Entity mentions {'that would be deleted' if dry_run else 'deleted'}: {stats['entity_mentions_deleted']}")
        
        # Suggest signal score cleanup
        await recalculate_signal_scores(dry_run=dry_run)
        
        if dry_run:
            print("\n" + "="*70)
            print("To actually delete the data, run with --confirm flag:")
            print(f"  python scripts/delete_recent_benzinga.py --confirm --hours {args.hours}")
            print("="*70)
        else:
            print("\n✅ Deletion complete!")
        
    finally:
        await mongo_manager.aclose()


if __name__ == "__main__":
    asyncio.run(main())
