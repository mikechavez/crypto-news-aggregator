#!/usr/bin/env python3
"""
Backfill script to extract entities from existing articles.

This script:
- Queries articles without entities field or with empty entities array
- Processes in batches using the existing extract_entities_batch()
- Updates articles with extracted entities
- Creates entity_mentions records
- Logs progress with running count and costs

Usage:
    # Test with dry run
    poetry run python scripts/backfill_entities.py --limit 10 --dry-run
    
    # Run with limit
    poetry run python scripts/backfill_entities.py --limit 10 --yes
    
    # Full backfill
    poetry run python scripts/backfill_entities.py --yes

See docs/BACKFILL_ENTITIES.md for complete documentation.
"""

import asyncio
import argparse
import sys
import os
from typing import List, Dict, Any
from datetime import datetime, timezone
from bson import ObjectId

# Add src to path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, os.path.join(project_root, "src"))

from crypto_news_aggregator.db.mongodb import mongo_manager
from crypto_news_aggregator.llm.factory import get_llm_provider
from crypto_news_aggregator.background.rss_fetcher import _process_entity_extraction_batch
from crypto_news_aggregator.db.operations.entity_mentions import create_entity_mentions_batch
from crypto_news_aggregator.core.config import settings


class BackfillStats:
    """Track backfill statistics."""
    
    def __init__(self):
        self.total_articles = 0
        self.processed_articles = 0
        self.failed_articles = 0
        self.total_entities = 0
        self.total_cost = 0.0
        self.consecutive_failures = 0
        self.failed_article_ids = []
    
    def reset_consecutive_failures(self):
        """Reset consecutive failure counter."""
        self.consecutive_failures = 0
    
    def add_failure(self, article_id: str):
        """Record a failure."""
        self.consecutive_failures += 1
        self.failed_articles += 1
        self.failed_article_ids.append(article_id)
    
    def add_success(self, entities_count: int, cost: float):
        """Record a success."""
        self.consecutive_failures = 0
        self.processed_articles += 1
        self.total_entities += entities_count
        self.total_cost += cost


async def get_articles_without_entities(limit: int = None) -> List[Dict[str, Any]]:
    """
    Query articles without entities field or with empty entities array.
    
    Args:
        limit: Maximum number of articles to return (None for all)
    
    Returns:
        List of article documents
    """
    db = await mongo_manager.get_async_database()
    collection = db.articles
    
    # Query for articles without entities or with empty entities
    query = {
        "$or": [
            {"entities": {"$exists": False}},
            {"entities": None},
            {"entities": []},
        ]
    }
    
    cursor = collection.find(query).sort("published_at", -1)
    
    if limit:
        cursor = cursor.limit(limit)
    
    articles = []
    async for article in cursor:
        articles.append(article)
    
    return articles


async def update_article_entities(
    article_id: str,
    entities: List[Dict[str, Any]],
    sentiment: str
) -> bool:
    """
    Update an article with extracted entities.
    
    Args:
        article_id: Article ID (string)
        entities: List of extracted entities
        sentiment: Overall sentiment
    
    Returns:
        True if successful, False otherwise
    """
    db = await mongo_manager.get_async_database()
    collection = db.articles
    
    try:
        # Convert string ID to ObjectId if needed
        if isinstance(article_id, str) and ObjectId.is_valid(article_id):
            query_id = ObjectId(article_id)
        else:
            query_id = article_id
        
        result = await collection.update_one(
            {"_id": query_id},
            {
                "$set": {
                    "entities": entities,
                    "updated_at": datetime.now(timezone.utc),
                }
            }
        )
        return result.modified_count > 0
    except Exception as e:
        print(f"Error updating article {article_id}: {e}")
        return False


async def create_entity_mentions(
    article_id: str,
    article_title: str,
    entities: List[Dict[str, Any]],
    sentiment: str
) -> int:
    """
    Create entity mention records for an article.
    
    Args:
        article_id: Article ID
        article_title: Article title
        entities: List of extracted entities
        sentiment: Overall sentiment
    
    Returns:
        Number of mentions created
    """
    mentions_to_create = []
    
    for entity in entities:
        mentions_to_create.append({
            "entity": entity.get("value"),
            "entity_type": entity.get("type"),
            "article_id": article_id,
            "sentiment": sentiment,
            "confidence": entity.get("confidence", 1.0),
            "metadata": {
                "article_title": article_title,
                "extraction_batch": True,
                "backfill": True,
            },
        })
    
    if mentions_to_create:
        try:
            mention_ids = await create_entity_mentions_batch(mentions_to_create)
            return len(mention_ids)
        except Exception as e:
            print(f"Error creating entity mentions for article {article_id}: {e}")
            return 0
    
    return 0


async def process_batch(
    batch: List[Dict[str, Any]],
    batch_num: int,
    total_batches: int,
    stats: BackfillStats,
    dry_run: bool = False
) -> None:
    """
    Process a batch of articles for entity extraction.
    
    Args:
        batch: List of article documents
        batch_num: Current batch number (1-indexed)
        total_batches: Total number of batches
        stats: Statistics tracker
        dry_run: If True, don't save changes
    """
    print(f"\nProcessing batch {batch_num}/{total_batches} ({len(batch)} articles)")
    
    # Get LLM client
    llm_client = get_llm_provider()
    
    # Extract entities
    try:
        result = await _process_entity_extraction_batch(batch, llm_client)
        
        # Process results
        batch_cost = result.get("usage", {}).get("total_cost", 0.0)
        
        for article_result in result.get("results", []):
            article_id = article_result.get("article_id")
            entities = article_result.get("entities", [])
            sentiment = article_result.get("sentiment", "neutral")
            
            # Find the original article
            article = next((a for a in batch if str(a.get("_id")) == article_id), None)
            if not article:
                print(f"  - Article {article_id}: NOT FOUND in batch")
                stats.add_failure(article_id)
                continue
            
            article_title = article.get("title", "")
            
            # Log extraction
            print(f"  - Article {article_id[:8]}...: {len(entities)} entities extracted")
            
            if not dry_run:
                # Update article
                updated = await update_article_entities(article_id, entities, sentiment)
                
                if updated:
                    # Create entity mentions
                    mentions_created = await create_entity_mentions(
                        article_id, article_title, entities, sentiment
                    )
                    stats.add_success(len(entities), batch_cost / len(result.get("results", [])))
                else:
                    print(f"    WARNING: Failed to update article {article_id}")
                    stats.add_failure(article_id)
            else:
                # Dry run - just count
                stats.add_success(len(entities), batch_cost / len(result.get("results", [])))
        
        # Log batch summary
        print(f"Batch cost: ${batch_cost:.6f}, Total: ${stats.total_cost:.6f}")
        
        # Reset consecutive failures on successful batch
        if result.get("results"):
            stats.reset_consecutive_failures()
        
    except Exception as e:
        print(f"ERROR processing batch: {e}")
        # Mark all articles in batch as failed
        for article in batch:
            article_id = str(article.get("_id"))
            stats.add_failure(article_id)


async def backfill_entities(
    limit: int = None,
    dry_run: bool = False,
    max_consecutive_failures: int = 3
) -> BackfillStats:
    """
    Main backfill function.
    
    Args:
        limit: Maximum number of articles to process (None for all)
        dry_run: If True, don't save changes
        max_consecutive_failures: Stop if this many consecutive failures occur
    
    Returns:
        Statistics about the backfill operation
    """
    stats = BackfillStats()
    
    # Get articles
    print("Querying articles without entities...")
    articles = await get_articles_without_entities(limit)
    stats.total_articles = len(articles)
    
    if not articles:
        print("No articles found without entities.")
        return stats
    
    print(f"Found {len(articles)} articles to process")
    
    if dry_run:
        print("\n⚠️  DRY RUN MODE - No changes will be saved\n")
    
    # Process in batches
    batch_size = settings.ENTITY_EXTRACTION_BATCH_SIZE
    total_batches = (len(articles) + batch_size - 1) // batch_size
    
    for i in range(0, len(articles), batch_size):
        batch = articles[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        
        await process_batch(batch, batch_num, total_batches, stats, dry_run)
        
        # Check for consecutive failures
        if stats.consecutive_failures >= max_consecutive_failures:
            print(f"\n❌ STOPPING: {max_consecutive_failures} consecutive failures detected")
            break
    
    return stats


def print_summary(stats: BackfillStats, dry_run: bool = False):
    """Print summary of backfill operation."""
    print("\n" + "="*60)
    print("BACKFILL SUMMARY")
    print("="*60)
    print(f"Total articles found:     {stats.total_articles}")
    print(f"Successfully processed:   {stats.processed_articles}")
    print(f"Failed:                   {stats.failed_articles}")
    print(f"Total entities extracted: {stats.total_entities}")
    print(f"Total cost:               ${stats.total_cost:.6f}")
    
    if stats.processed_articles > 0:
        avg_entities = stats.total_entities / stats.processed_articles
        avg_cost = stats.total_cost / stats.processed_articles
        print(f"Average entities/article: {avg_entities:.1f}")
        print(f"Average cost/article:     ${avg_cost:.6f}")
    
    if stats.failed_article_ids:
        print(f"\nFailed article IDs ({len(stats.failed_article_ids)}):")
        for article_id in stats.failed_article_ids[:10]:
            print(f"  - {article_id}")
        if len(stats.failed_article_ids) > 10:
            print(f"  ... and {len(stats.failed_article_ids) - 10} more")
    
    if dry_run:
        print("\n⚠️  This was a DRY RUN - no changes were saved")
    
    print("="*60)


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Backfill entity extraction for existing articles"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process only N articles (for testing)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without making changes"
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt"
    )
    parser.add_argument(
        "--max-failures",
        type=int,
        default=3,
        help="Stop after N consecutive failures (default: 3)"
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize MongoDB connection
        await mongo_manager.initialize()
        
        # Get article count
        articles = await get_articles_without_entities(args.limit)
        article_count = len(articles)
        
        if article_count == 0:
            print("No articles found without entities.")
            return
        
        # Show preview
        print(f"\nFound {article_count} articles without entities")
        if args.limit:
            print(f"Will process up to {args.limit} articles")
        else:
            print("Will process ALL articles")
        
        if args.dry_run:
            print("Mode: DRY RUN (no changes will be saved)")
        else:
            print("Mode: LIVE (changes will be saved)")
        
        # Confirmation prompt (unless --yes or --dry-run)
        if not args.yes and not args.dry_run:
            response = input(f"\nProceed with backfill of {article_count} articles? [y/N]: ")
            if response.lower() != 'y':
                print("Aborted.")
                return
        
        # Run backfill
        print("\nStarting backfill...")
        stats = await backfill_entities(
            limit=args.limit,
            dry_run=args.dry_run,
            max_consecutive_failures=args.max_failures
        )
        
        # Print summary
        print_summary(stats, args.dry_run)
        
    except KeyboardInterrupt:
        print("\n\nBackfill interrupted by user")
    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Close MongoDB connection
        await mongo_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
