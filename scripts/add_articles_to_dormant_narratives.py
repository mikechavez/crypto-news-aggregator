#!/usr/bin/env python3
"""
Add recent articles to dormant narratives to trigger reactivation.

This script finds dormant narratives and adds recent articles with matching
nucleus entities to trigger the resurrection detection logic.
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from crypto_news_aggregator.db.mongodb import mongo_manager, initialize_mongodb


async def add_articles_to_dormant_narratives():
    """
    Add recent articles to dormant narratives to trigger reactivation.
    """
    print("=" * 80)
    print("ADD ARTICLES TO DORMANT NARRATIVES")
    print("=" * 80)
    print("Finding dormant narratives and matching recent articles...")
    print()
    
    await initialize_mongodb()
    db = await mongo_manager.get_async_database()
    
    # Find dormant narratives
    dormant_narratives = await db.narratives.find(
        {'lifecycle_state': 'dormant'}
    ).to_list(length=10)
    
    if not dormant_narratives:
        print('❌ No dormant narratives found')
        await mongo_manager.aclose()
        return
    
    print(f'Found {len(dormant_narratives)} dormant narratives')
    print()
    
    # Get recent articles (last 24 hours)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    recent_articles = await db.articles.find(
        {'published_at': {'$gte': cutoff}}
    ).to_list(length=1000)
    
    print(f'Found {len(recent_articles)} recent articles')
    print()
    
    updated_count = 0
    
    for narrative in dormant_narratives:
        fingerprint = narrative.get('fingerprint', {})
        nucleus_entity = fingerprint.get('nucleus_entity', '')
        
        if not nucleus_entity:
            continue
        
        # Find recent articles with matching nucleus entity
        matching_articles = [
            article for article in recent_articles
            if article.get('nucleus_entity') == nucleus_entity
        ]
        
        if not matching_articles:
            continue
        
        # Add articles to narrative
        existing_article_ids = set(narrative.get('article_ids', []))
        new_article_ids = [str(article['_id']) for article in matching_articles]
        combined_article_ids = list(existing_article_ids | set(new_article_ids))
        
        # Update narrative with new articles and set last_updated to now
        await db.narratives.update_one(
            {'_id': narrative['_id']},
            {
                '$set': {
                    'article_ids': combined_article_ids,
                    'article_count': len(combined_article_ids),
                    'last_updated': datetime.now(timezone.utc),
                    'needs_summary_update': True
                }
            }
        )
        
        title = narrative.get('title', 'N/A')
        print(f"✓ Updated: {title[:70]}")
        print(f"  Nucleus: {nucleus_entity}")
        print(f"  Added {len(new_article_ids)} new articles")
        print(f"  Total articles: {len(combined_article_ids)}")
        print()
        
        updated_count += 1
    
    print("=" * 80)
    print(f"✅ Updated {updated_count} dormant narratives with recent articles")
    print("=" * 80)
    print()
    print("Next step: Run narrative detection to trigger lifecycle state updates:")
    print("  poetry run python scripts/trigger_narrative_detection.py --hours 24")
    print()
    
    await mongo_manager.aclose()


async def main():
    """Main entry point."""
    await add_articles_to_dormant_narratives()


if __name__ == "__main__":
    asyncio.run(main())
