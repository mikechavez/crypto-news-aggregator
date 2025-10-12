"""
Backfill narrative data for articles that don't have it yet.

Rate Limits (Anthropic Claude):
- 50 requests/minute
- 30,000 input tokens/minute (Sonnet 4.x)
- ~1,300 tokens per article (prompt + response)

Strategy:
- Process in batches of 20 articles
- Wait 30 seconds between batches
- This gives us ~40 articles/minute, staying under limits
"""
import asyncio
import sys
from pathlib import Path
import argparse
from datetime import datetime, timedelta, timezone

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from crypto_news_aggregator.services.narrative_themes import discover_narrative_from_article
from crypto_news_aggregator.db.mongodb import mongo_manager


async def backfill_with_rate_limiting(hours: int, limit: int, batch_size: int = 20, batch_delay: int = 30):
    """
    Backfill narrative data with rate limiting.
    
    Args:
        hours: Look back this many hours
        limit: Maximum articles to process
        batch_size: Articles per batch (default: 20)
        batch_delay: Seconds to wait between batches (default: 30)
    """
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
    
    # Process in batches
    for batch_num, i in enumerate(range(0, total_articles, batch_size), 1):
        batch = articles[i:i + batch_size]
        batch_start = datetime.now()
        
        print(f"📦 Batch {batch_num}/{(total_articles + batch_size - 1) // batch_size}: Processing {len(batch)} articles...")
        
        for article in batch:
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
            
            # Small delay between articles within batch
            await asyncio.sleep(0.5)
        
        batch_duration = (datetime.now() - batch_start).total_seconds()
        print(f"   ✅ Batch complete in {batch_duration:.1f}s - Success: {updated_count}, Failed: {failed_count}")
        
        # Wait between batches (except for last batch)
        if i + batch_size < total_articles:
            print(f"   ⏸️  Waiting {batch_delay}s before next batch...\n")
            await asyncio.sleep(batch_delay)
    
    return updated_count


async def main(hours: int, limit: int, batch_size: int, batch_delay: int):
    """Backfill narrative data for recent articles."""
    
    print(f"🔌 Connecting to MongoDB...")
    await mongo_manager.initialize()
    
    print(f"🔄 Backfilling narrative data for articles from last {hours}h (limit: {limit})...")
    updated_count = await backfill_with_rate_limiting(hours, limit, batch_size, batch_delay)
    
    print(f"\n✅ Updated {updated_count} articles with narrative data")
    
    await mongo_manager.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill narrative data for articles")
    parser.add_argument("--hours", type=int, default=48, help="Look back this many hours")
    parser.add_argument("--limit", type=int, default=500, help="Maximum articles to process")
    parser.add_argument("--batch-size", type=int, default=20, help="Articles per batch")
    parser.add_argument("--batch-delay", type=int, default=30, help="Seconds between batches")
    
    args = parser.parse_args()
    
    asyncio.run(main(args.hours, args.limit, args.batch_size, args.batch_delay))
