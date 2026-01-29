#!/usr/bin/env python3
"""
Check what types of nucleus entities exist in the database.
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from collections import Counter

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from crypto_news_aggregator.db.mongodb import mongo_manager


async def check_nucleus_types():
    """Check nucleus entity types in existing narratives."""
    print("=" * 80)
    print("NUCLEUS ENTITY TYPE ANALYSIS")
    print("=" * 80)
    print()
    
    db = await mongo_manager.get_async_database()
    narratives_collection = db.narratives
    
    # Get all narratives
    cursor = narratives_collection.find({})
    narratives = await cursor.to_list(length=None)
    
    print(f"Total narratives: {len(narratives)}")
    print()
    
    # Categorize by nucleus entity type
    theme_based = []  # Contains underscores (e.g., nft_gaming, layer2_scaling)
    entity_based = []  # Actual entity names (e.g., Bitcoin, Ethereum)
    missing = []  # No fingerprint or nucleus
    
    for narrative in narratives:
        fingerprint = narrative.get('fingerprint')
        if not fingerprint:
            missing.append(narrative)
            continue
        
        nucleus = fingerprint.get('nucleus_entity', '')
        if not nucleus:
            missing.append(narrative)
            continue
        
        # Check if it's theme-based (contains underscore) or entity-based
        if '_' in nucleus:
            theme_based.append((narrative, nucleus))
        else:
            entity_based.append((narrative, nucleus))
    
    print("CATEGORIZATION:")
    print(f"  Theme-based nucleus (with underscores): {len(theme_based)}")
    print(f"  Entity-based nucleus (actual names): {len(entity_based)}")
    print(f"  Missing fingerprint/nucleus: {len(missing)}")
    print()
    
    print("=" * 80)
    print("THEME-BASED NARRATIVES (Sample)")
    print("=" * 80)
    for narrative, nucleus in theme_based[:10]:
        print(f"- {narrative.get('title')}")
        print(f"  Nucleus: {nucleus}")
        print(f"  Last updated: {narrative.get('last_updated')}")
        print()
    
    print("=" * 80)
    print("ENTITY-BASED NARRATIVES (Sample)")
    print("=" * 80)
    for narrative, nucleus in entity_based[:10]:
        print(f"- {narrative.get('title')}")
        print(f"  Nucleus: {nucleus}")
        print(f"  Last updated: {narrative.get('last_updated')}")
        print()
    
    # Check recent narratives specifically
    cutoff = datetime.now(timezone.utc) - timedelta(days=3)
    recent_narratives = [n for n in narratives if n.get('last_updated', datetime.min.replace(tzinfo=timezone.utc)) >= cutoff]
    
    print("=" * 80)
    print(f"RECENT NARRATIVES (Last 3 days): {len(recent_narratives)}")
    print("=" * 80)
    
    recent_theme = 0
    recent_entity = 0
    
    for narrative in recent_narratives:
        fingerprint = narrative.get('fingerprint')
        if fingerprint:
            nucleus = fingerprint.get('nucleus_entity', '')
            if '_' in nucleus:
                recent_theme += 1
            else:
                recent_entity += 1
    
    print(f"  Theme-based: {recent_theme}")
    print(f"  Entity-based: {recent_entity}")
    print()
    
    if recent_theme > 0:
        print("⚠️  WARNING: Recent narratives still using theme-based nucleus!")
        print("   This explains why matching is failing.")


if __name__ == "__main__":
    asyncio.run(check_nucleus_types())
