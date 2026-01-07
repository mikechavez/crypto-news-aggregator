"""
Backfill narrative data for articles that don't have it yet.

Rate Limits (Anthropic Claude Haiku):
- 50 requests/minute (RPM)
- 25,000 input tokens/minute (TPM)
- 25,000 output tokens/minute (TPM)
- ~1,000 tokens per article (700 input + 300 output)

Conservative Strategy:
- Process in batches of 15 articles
- 1.0s delay between articles (14 delays for 15 articles) = 14s delay time
- 30s delay between batches
- Total: ~44s per batch = 20.5 articles/minute
- This leaves an 18% buffer under the 25 articles/min token limit
"""
import asyncio
import sys
import time
from pathlib import Path
import argparse
import logging
from datetime import datetime, timedelta, timezone

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from crypto_news_aggregator.services.narrative_themes import discover_narrative_from_article
from crypto_news_aggregator.db.mongodb import mongo_manager


async def backfill_with_rate_limiting(hours: int, limit: int, batch_size: int = 15, batch_delay: int = 30, article_delay: float = 1.0):
    """
    Backfill narrative data with conservative rate limiting.

    Target throughput: ~20 articles/minute (safe under 25 articles/min limit)
    Calculation:
    - 15 articles per batch
    - 1.0s delay between articles (14 delays for 15 articles) = 14s delay time
    - 30s delay between batches
    - Total: ~44s per batch = 20.5 articles/minute
    This leaves an 18% buffer under the 25 articles/min token limit.

    Args:
        hours: Look back this many hours
        limit: Maximum articles to process
        batch_size: Articles per batch (default: 15)
        batch_delay: Seconds to wait between batches (default: 30)
        article_delay: Seconds to wait between articles (default: 1.0)
    """
    # Calculate expected throughput
    # Note: We have (batch_size - 1) delays between articles, not batch_size
    time_per_batch = ((batch_size - 1) * article_delay) + batch_delay
    articles_per_minute = (batch_size / time_per_batch) * 60
    
    logger.info(f"📊 Rate limiting configuration:")
    logger.info(f"   Batch size: {batch_size} articles")
    logger.info(f"   Batch delay: {batch_delay}s")
    logger.info(f"   Article delay: {article_delay}s")
    logger.info(f"   Time per batch: {time_per_batch:.1f}s")
    logger.info(f"   Expected throughput: {articles_per_minute:.1f} articles/min")
    
    if articles_per_minute > 22:
        logger.warning(
            f"⚠️  WARNING: Expected throughput ({articles_per_minute:.1f}/min) "
            f"is close to safe limit (20/min). Consider increasing delays."
        )
    elif articles_per_minute > 20:
        logger.info(f"✓ Throughput within safe range (target: <20/min)")
    else:
        logger.info(f"✓ Throughput well under safe limit")
    
    logger.info("")
    
    db = await mongo_manager.get_async_database()
    articles_collection = db.articles
    
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    # Find articles needing narrative extraction
    # Only process if:
    # 1. Missing narrative_summary, OR
    # 2. Missing narrative_hash (old format), OR  
    # 3. Missing actors or nucleus_entity (incomplete data)
    cursor = articles_collection.find({
        "published_at": {"$gte": cutoff_time},
        "$or": [
            {"narrative_summary": {"$exists": False}},
            {"narrative_summary": None},
            {"actors": {"$exists": False}},
            {"actors": None},
            {"nucleus_entity": {"$exists": False}},
            {"nucleus_entity": None},
            {"narrative_hash": {"$exists": False}},  # Missing hash = needs processing
        ]
    }).limit(limit)
    
    articles = await cursor.to_list(length=None)
    total_articles = len(articles)
    
    if total_articles == 0:
        return 0
    
    print(f"📊 Found {total_articles} articles needing narrative data")
    print(f"⏱️  Processing in batches of {batch_size} with {batch_delay}s delays")
    print(f"⏱️  Estimated time: {(total_articles / batch_size) * batch_delay / 60:.1f} minutes\n")
    
    updated_count = 0
    failed_count = 0
    total_batches = (total_articles + batch_size - 1) // batch_size
    
    # Process in batches
    for batch_num, i in enumerate(range(0, total_articles, batch_size), 1):
        batch = articles[i:i + batch_size]
        batch_start_time = time.time()
        
        logger.info(f"📦 Batch {batch_num}/{total_batches}: Processing {len(batch)} articles...")
        
        for article_idx, article in enumerate(batch):
            article_id = str(article.get("_id"))
            
            # Extract narrative elements (now with caching)
            narrative_data = await discover_narrative_from_article(article)
            
            if narrative_data:
                # Update article with narrative data (including hash)
                await articles_collection.update_one(
                    {"_id": article["_id"]},
                    {"$set": {
                        "actors": narrative_data.get("actors", []),
                        "actor_salience": narrative_data.get("actor_salience", {}),
                        "nucleus_entity": narrative_data.get("nucleus_entity", ""),
                        "narrative_focus": narrative_data.get("narrative_focus", ""),
                        "actions": narrative_data.get("actions", []),
                        "tensions": narrative_data.get("tensions", []),
                        "implications": narrative_data.get("implications", ""),
                        "narrative_summary": narrative_data.get("narrative_summary", ""),
                        "narrative_hash": narrative_data.get("narrative_hash", ""),
                        "narrative_extracted_at": datetime.now(timezone.utc)
                    }}
                )
                updated_count += 1
            else:
                failed_count += 1
            
            # Delay between articles within batch for rate limiting
            # Don't delay after the last article in the batch
            if article_idx < len(batch) - 1:
                await asyncio.sleep(article_delay)
        
        # Calculate actual throughput
        batch_time = time.time() - batch_start_time
        actual_throughput = (len(batch) / batch_time) * 60
        
        logger.info(
            f"   ✅ Batch complete in {batch_time:.1f}s "
            f"- Throughput: {actual_throughput:.1f} articles/min "
            f"- Success: {updated_count}, Failed: {failed_count}"
        )
        
        # Warning if throughput too high
        if actual_throughput > 22:
            logger.warning(
                f"   ⚠️  Throughput ({actual_throughput:.1f}/min) exceeds safe limit! "
                f"Consider increasing --batch-delay or --article-delay"
            )
        
        # Wait between batches (except for last batch)
        if i + batch_size < total_articles:
            logger.info(f"   ⏸️  Waiting {batch_delay}s before next batch...\n")
            await asyncio.sleep(batch_delay)
    
    return updated_count


async def main(hours: int, limit: int, batch_size: int, batch_delay: int, article_delay: float):
    """Backfill narrative data for recent articles."""
    
    print(f"🔌 Connecting to MongoDB...")
    await mongo_manager.initialize()
    
    print(f"🔄 Backfilling narrative data for articles from last {hours}h (limit: {limit})...")
    updated_count = await backfill_with_rate_limiting(hours, limit, batch_size, batch_delay, article_delay)
    
    print(f"\n✅ Updated {updated_count} articles with narrative data")
    
    await mongo_manager.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill narrative data for articles")
    parser.add_argument("--hours", type=int, default=48, help="Look back this many hours")
    parser.add_argument("--limit", type=int, default=500, help="Maximum articles to process")
    parser.add_argument("--batch-size", type=int, default=15, help="Articles per batch (default: 15)")
    parser.add_argument("--batch-delay", type=int, default=30, help="Seconds between batches (default: 30)")
    parser.add_argument("--article-delay", type=float, default=1.0, help="Seconds between articles (default: 1.0)")
    
    args = parser.parse_args()
    
    asyncio.run(main(args.hours, args.limit, args.batch_size, args.batch_delay, args.article_delay))
