#!/usr/bin/env python3
"""
Safe Backfill Script for Context Owl

Safely processes backlog of articles with comprehensive cost controls:
- Estimates cost before processing
- Uses optimized LLM (Haiku + caching + selective processing)
- Monitors costs in real-time
- Automatic safety stops
- Marks processed articles to avoid reprocessing

Usage:
    # Estimate only (no processing)
    poetry run python scripts/safe_backfill.py --estimate-only
    
    # Process last 7 days, premium sources only
    poetry run python scripts/safe_backfill.py --days 7 --premium-only
    
    # Process last 30 days with selective filtering
    poetry run python scripts/safe_backfill.py --days 30
    
    # Custom batch size
    poetry run python scripts/safe_backfill.py --days 30 --batch-size 100
"""

import asyncio
import argparse
from datetime import datetime, timedelta, timezone
from motor.motor_asyncio import AsyncIOMotorClient
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
except ImportError:
    pass  # dotenv not installed, rely on environment variables

from crypto_news_aggregator.llm.optimized_anthropic import create_optimized_llm
from crypto_news_aggregator.services.selective_processor import create_processor


class SafeBackfill:
    """Safe backfill with cost controls"""
    
    PREMIUM_SOURCES = ['coindesk', 'cointelegraph', 'decrypt', 'theblock', 'bloomberg', 'reuters', 'cnbc']
    
    def __init__(self, days: int = 30, premium_only: bool = False, batch_size: int = 50):
        self.days = days
        self.premium_only = premium_only
        self.batch_size = batch_size
        self.total_cost = 0.0
        self.max_safe_cost = 5.0  # Safety stop at $5
    
    async def run(self, estimate_only: bool = False):
        """Execute backfill with optional estimation mode"""
        
        print("=" * 60)
        print("🔄 Context Owl Safe Backfill")
        print("=" * 60)
        print(f"Days to backfill: {self.days}")
        print(f"Premium sources only: {self.premium_only}")
        print(f"Batch size: {self.batch_size}")
        print(f"Mode: {'ESTIMATE ONLY' if estimate_only else 'FULL PROCESSING'}")
        print("=" * 60)
        print()
        
        # Connect to database
        mongodb_uri = os.getenv("MONGODB_URI")
        if not mongodb_uri:
            print("❌ Error: MONGODB_URI not set")
            return
        
        # Get database name from env or default
        db_name = os.getenv("MONGODB_NAME", "crypto_news")
        
        print("📡 Connecting to MongoDB...")
        try:
            client = AsyncIOMotorClient(mongodb_uri, serverSelectionTimeoutMS=10000)
            db = client[db_name]
            # Test connection
            await db.command('ping')
            print(f"✅ Connected to database: {db_name}\n")
        except Exception as e:
            print(f"❌ Error connecting to MongoDB: {e}")
            return
        
        # Find articles to process
        print("📊 Analyzing articles...")
        articles = await self._find_articles_to_process(db)
        
        if len(articles) == 0:
            print("✅ No articles need processing!")
            client.close()
            return
        
        print(f"Found {len(articles)} articles to process\n")
        
        # Estimate costs
        processor = create_processor(db)
        estimate = await self._estimate_costs(articles, processor)
        
        # Display estimate
        self._display_estimate(estimate)
        
        if estimate_only:
            print("\n📋 Estimate mode - stopping here")
            client.close()
            return
        
        # Confirm if cost is high
        if estimate['total_cost'] > 15:
            print(f"\n⚠️  WARNING: Estimated cost (${estimate['total_cost']:.2f}) exceeds $15")
            response = input("Continue? (yes/no): ")
            if response.lower() != 'yes':
                print("❌ Aborted by user")
                client.close()
                return
        
        # Check for API key
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            print("❌ Error: ANTHROPIC_API_KEY not set")
            client.close()
            return
        
        # Initialize optimized LLM
        print("\n🚀 Initializing optimized LLM client...")
        llm = await create_optimized_llm(db, api_key)
        print("✅ LLM initialized with caching and cost tracking\n")
        
        # Process in batches
        await self._process_batches(db, articles, llm, processor)
        
        # Final summary
        print("\n" + "=" * 60)
        print("✅ Backfill Complete!")
        print("=" * 60)
        print(f"Total articles processed: {len(articles)}")
        print(f"Total cost: ${self.total_cost:.2f}")
        
        # Get final cache stats
        cache_stats = await llm.get_cache_stats()
        print(f"Cache hit rate: {cache_stats['hit_rate_percent']:.1f}%")
        print("=" * 60)
        
        client.close()
    
    async def _find_articles_to_process(self, db, max_articles: int = 10000):
        """Find articles that need entity extraction"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.days)
        
        query = {
            "published_at": {"$gte": cutoff_date}
        }
        
        # Add source filter if premium only
        if self.premium_only:
            query["source"] = {"$in": self.PREMIUM_SOURCES}
        
        # Find articles that haven't been processed yet
        query["entities_extracted"] = {"$ne": True}
        
        # Skip count for speed - just fetch with limit
        print("   Fetching articles (limit: {})...".format(max_articles))
        
        # Only fetch needed fields to speed up query
        projection = {
            "_id": 1,
            "title": 1,
            "text": 1,
            "source": 1,
            "published_at": 1
        }
        
        articles = []
        cursor = db.articles.find(query, projection).sort("published_at", -1).limit(max_articles)
        
        async for article in cursor:
            articles.append(article)
            if len(articles) % 500 == 0:
                print(f"   ... loaded {len(articles)} articles")
        
        return articles
    
    async def _estimate_costs(self, articles, processor):
        """Estimate processing costs"""
        llm_count = 0
        regex_count = 0
        
        for article in articles:
            if processor.should_use_llm(article):
                llm_count += 1
            else:
                regex_count += 1
        
        # Cost per LLM call (Haiku) - based on average token usage
        # ~500 input tokens, ~200 output tokens per call
        # Haiku pricing: $0.25/1M input, $1.25/1M output
        input_cost = (500 / 1_000_000) * 0.25
        output_cost = (200 / 1_000_000) * 1.25
        cost_per_llm = input_cost + output_cost  # ~$0.000375 per call
        
        # Assume 20% cache hit rate for backfill (conservative)
        cache_rate = 0.20
        
        # Calculate estimated cost
        estimated_cost = llm_count * cost_per_llm * (1 - cache_rate)
        
        return {
            'total_articles': len(articles),
            'llm_articles': llm_count,
            'regex_articles': regex_count,
            'cache_rate': cache_rate,
            'cost_per_llm': cost_per_llm,
            'total_cost': estimated_cost
        }
    
    def _display_estimate(self, estimate):
        """Display cost estimate"""
        print("💰 Cost Estimate:")
        print("-" * 60)
        print(f"Total articles: {estimate['total_articles']}")
        print(f"  ├─ LLM processing (Haiku): {estimate['llm_articles']} articles")
        print(f"  └─ Regex extraction (FREE): {estimate['regex_articles']} articles")
        print()
        print(f"Cost breakdown:")
        print(f"  ├─ Cost per LLM call: ${estimate['cost_per_llm']:.6f}")
        print(f"  ├─ Expected cache savings: ~{estimate['cache_rate']*100:.0f}%")
        print(f"  └─ Estimated total cost: ${estimate['total_cost']:.2f}")
        print("-" * 60)
        
        if estimate['total_cost'] < 5:
            print("✅ Cost is reasonable (<$5)")
        elif estimate['total_cost'] < 10:
            print("⚠️  Cost is moderate ($5-10)")
        else:
            print("⚠️  Cost is high (>$10) - consider --premium-only or fewer --days")
    
    async def _process_batches(self, db, articles, llm, processor):
        """Process articles in batches with cost monitoring"""
        num_batches = (len(articles) - 1) // self.batch_size + 1
        processed_count = 0
        
        for i in range(0, len(articles), self.batch_size):
            batch = articles[i:i+self.batch_size]
            batch_num = i // self.batch_size + 1
            
            print(f"\n📦 Batch {batch_num}/{num_batches}")
            print(f"   Articles: {i+1} to {min(i+self.batch_size, len(articles))}")
            
            # Get cost before batch
            cost_before = await llm.get_cost_summary()
            cost_before_value = cost_before.get('month_to_date', 0)
            
            # Process batch
            result = await processor.batch_process_articles(batch, llm)
            
            # Get cost after batch
            cost_after = await llm.get_cost_summary()
            cost_after_value = cost_after.get('month_to_date', 0)
            batch_cost = cost_after_value - cost_before_value
            self.total_cost = cost_after_value
            
            # Mark articles as processed
            article_ids = [a['_id'] for a in batch]
            await db.articles.update_many(
                {"_id": {"$in": article_ids}},
                {"$set": {
                    "entities_extracted": True,
                    "extracted_at": datetime.now(timezone.utc)
                }}
            )
            
            processed_count += len(batch)
            
            # Display results
            print(f"   ✓ Processed: {len(batch)} articles")
            print(f"     ├─ LLM: {result['llm_processed']}")
            print(f"     ├─ Regex: {result['simple_processed']}")
            print(f"     ├─ Entities: {len(result['entity_mentions'])}")
            print(f"     ├─ Batch cost: ${batch_cost:.4f}")
            print(f"     └─ Total cost: ${self.total_cost:.2f}")
            
            # Safety check
            if self.total_cost > self.max_safe_cost:
                print(f"\n⚠️  SAFETY STOP: Cost exceeded ${self.max_safe_cost}")
                print(f"   Processed {processed_count}/{len(articles)} articles")
                print(f"   You can resume by running the script again")
                print(f"   (Processed articles won't be reprocessed)")
                break
            
            # Delay between batches to avoid connection exhaustion
            if batch_num < num_batches:
                await asyncio.sleep(2)


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Safe backfill for Context Owl with cost controls',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Estimate cost only
  %(prog)s --estimate-only
  
  # Process last 7 days, premium sources only
  %(prog)s --days 7 --premium-only
  
  # Process last 30 days with selective filtering  
  %(prog)s --days 30
  
  # Process with larger batches
  %(prog)s --days 14 --batch-size 100
        """
    )
    
    parser.add_argument(
        '--days',
        type=int,
        default=30,
        help='Number of days to backfill (default: 30)'
    )
    
    parser.add_argument(
        '--premium-only',
        action='store_true',
        help='Only process premium sources (coindesk, cointelegraph, decrypt, etc.)'
    )
    
    parser.add_argument(
        '--estimate-only',
        action='store_true',
        help='Only estimate cost without processing'
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        default=50,
        help='Number of articles per batch (default: 50)'
    )
    
    args = parser.parse_args()
    
    backfill = SafeBackfill(
        days=args.days,
        premium_only=args.premium_only,
        batch_size=args.batch_size
    )
    
    await backfill.run(estimate_only=args.estimate_only)


if __name__ == "__main__":
    asyncio.run(main())
