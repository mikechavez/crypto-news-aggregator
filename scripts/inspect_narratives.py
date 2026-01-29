"""
Inspect existing narratives to determine if they should be cleared.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))

from crypto_news_aggregator.db.mongodb import mongo_manager

async def inspect_narratives():
    """Inspect existing narratives collection."""
    
    print("=" * 80)
    print("NARRATIVE INSPECTION")
    print("=" * 80)
    print()
    
    await mongo_manager.initialize()
    
    db = await mongo_manager.get_async_database()
    narratives_collection = db.narratives
    
    # Count total narratives
    total_narratives = await narratives_collection.count_documents({})
    
    print(f"📊 Total narratives: {total_narratives}")
    print()
    
    if total_narratives == 0:
        print("✅ No narratives exist - fresh start after backfill")
        await mongo_manager.close()
        return
    
    # Get sample narratives
    narratives = await narratives_collection.find({}).limit(10).to_list(length=10)
    
    print("📋 Sample Narratives:")
    print()
    
    for i, narrative in enumerate(narratives, 1):
        title = narrative.get('title', 'Unknown')
        theme = narrative.get('theme', 'Unknown')
        article_count = narrative.get('article_count', 0)
        entities = narrative.get('entities', [])
        lifecycle = narrative.get('lifecycle', 'Unknown')
        created_at = narrative.get('created_at', datetime.now(timezone.utc))
        
        # Detect if theme-based or salience-based
        # Theme-based: generic themes like "regulatory", "defi"
        # Salience-based: specific entities like "SEC", "Binance"
        is_theme_based = theme.lower() in [
            'regulatory', 'defi', 'nft', 'institutional', 
            'technology', 'market', 'security', 'adoption',
            'infrastructure', 'governance', 'payments', 'scaling'
        ]
        
        narrative_type = "Theme-based" if is_theme_based else "Entity-based"
        
        print(f"{i}. {title}")
        print(f"   Theme: {theme}")
        print(f"   Type: {narrative_type}")
        print(f"   Articles: {article_count}")
        print(f"   Entities: {', '.join(entities[:5])}")
        print(f"   Lifecycle: {lifecycle}")
        print(f"   Age: {(datetime.now(timezone.utc) - created_at).days} days old")
        print()
    
    # Analyze narrative types
    all_narratives = await narratives_collection.find({}).to_list(length=None)
    
    theme_based_count = 0
    entity_based_count = 0
    
    for narrative in all_narratives:
        theme = narrative.get('theme', '').lower()
        if theme in ['regulatory', 'defi', 'nft', 'institutional', 
                     'technology', 'market', 'security', 'adoption',
                     'infrastructure', 'governance', 'payments', 'scaling']:
            theme_based_count += 1
        else:
            entity_based_count += 1
    
    print("=" * 80)
    print("ANALYSIS")
    print("=" * 80)
    print(f"Total narratives: {total_narratives}")
    print(f"Theme-based (old system): {theme_based_count} ({theme_based_count/total_narratives*100:.0f}%)")
    print(f"Entity-based (new system): {entity_based_count} ({entity_based_count/total_narratives*100:.0f}%)")
    print()
    
    # Recommendation
    if theme_based_count > entity_based_count:
        print("⚠️  RECOMMENDATION: Clear old theme-based narratives")
        print()
        print("Old theme-based narratives dominate. After backfill completes:")
        print("1. Run backfill to extract article-level data")
        print("2. Generate new salience-based narratives")
        print("3. Clear old narratives with: poetry run python scripts/clean_narratives.py --confirm")
        print()
    else:
        print("✅ RECOMMENDATION: Keep existing narratives")
        print()
        print("Most narratives are entity-based (new system).")
        print("Let new narratives merge with existing ones naturally.")
        print()
    
    await mongo_manager.close()

if __name__ == "__main__":
    asyncio.run(inspect_narratives())
