#!/usr/bin/env python3
"""
Count and categorize narratives as theme-based vs entity-based.

Theme-based narratives are identified by:
1. nucleus_entity contains underscores (e.g., nft_gaming, layer2_scaling)
2. nucleus_entity is a generic lowercase term without proper capitalization
   (e.g., regulatory, payments, security, infrastructure, stablecoin, etc.)

Entity-based narratives have proper capitalization (e.g., Bitcoin, Ethereum, Solana)
"""

import asyncio
import os
from dotenv import load_dotenv

# Add parent directory to path for imports
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from crypto_news_aggregator.db.mongodb import mongo_manager

# Load environment variables
load_dotenv()

# Known generic theme terms (lowercase, no proper capitalization)
GENERIC_THEME_TERMS = {
    'regulatory', 'payments', 'security', 'infrastructure', 'stablecoin',
    'technology', 'partnerships', 'defi', 'institutional_investment',
    'market_analysis', 'adoption', 'governance', 'scalability', 'privacy',
    'interoperability', 'tokenization', 'custody', 'compliance', 'mining',
    'staking', 'lending', 'trading', 'exchange', 'wallet', 'bridge',
    'oracle', 'dao', 'nft', 'metaverse', 'gaming', 'yield', 'liquidity',
    'derivatives', 'futures', 'options', 'spot', 'margin', 'leverage',
    'collateral', 'liquidation', 'slashing', 'validator', 'consensus',
    'protocol', 'network', 'blockchain', 'cryptocurrency', 'token',
    'coin', 'asset', 'market', 'price', 'volume', 'volatility',
    'bull', 'bear', 'trend', 'momentum', 'sentiment', 'analysis',
    'forecast', 'prediction', 'outlook', 'update', 'development',
    'upgrade', 'fork', 'merge', 'launch', 'release', 'announcement',
    'integration', 'partnership', 'collaboration', 'acquisition',
    'investment', 'funding', 'raise', 'round', 'valuation', 'ipo',
    'listing', 'delisting', 'suspension', 'halt', 'resume', 'restart',
    'hack', 'exploit', 'vulnerability', 'patch', 'fix', 'bug',
    'issue', 'problem', 'challenge', 'risk', 'threat', 'attack',
    'defense', 'protection', 'safety', 'audit', 'review', 'report'
}


def is_theme_based(nucleus_entity: str) -> bool:
    """
    Determine if a nucleus_entity represents a theme rather than a specific entity.
    
    Theme-based indicators:
    1. Contains underscores (compound themes like nft_gaming, layer2_scaling)
    2. Is a known generic lowercase term without proper capitalization
    3. Is all lowercase and not a known entity ticker/symbol
    """
    if not nucleus_entity:
        return False
    
    # Check for underscores (compound themes)
    if '_' in nucleus_entity:
        return True
    
    # Check if it's in our known generic theme terms
    if nucleus_entity.lower() in GENERIC_THEME_TERMS:
        return True
    
    # Check if it's all lowercase (likely a theme, not a proper entity name)
    # Exclude very short strings that might be tickers (e.g., btc, eth)
    if nucleus_entity.islower() and len(nucleus_entity) > 3:
        return True
    
    return False


async def count_narratives():
    """Query all narratives and categorize them."""
    
    # Initialize MongoDB connection
    await mongo_manager.initialize()
    
    try:
        # Get async database
        db = await mongo_manager.get_async_database()
        narratives_collection = db.narratives
        
        # Query all narratives, sorted by created_at descending
        cursor = narratives_collection.find({}).sort("created_at", -1)
        narratives = await cursor.to_list(length=None)
        
        # Categorize narratives
        theme_based = []
        entity_based = []
        
        for narrative in narratives:
            # Get nucleus_entity from fingerprint if available, otherwise use theme
            fingerprint = narrative.get('fingerprint', {})
            nucleus_entity = fingerprint.get('nucleus_entity', '') or narrative.get('theme', '')
            
            if is_theme_based(nucleus_entity):
                theme_based.append(narrative)
            else:
                entity_based.append(narrative)
        
        # Print results
        print("=" * 80)
        print("NARRATIVE CATEGORIZATION RESULTS")
        print("=" * 80)
        print()
        print(f"Total Narratives: {len(narratives)}")
        print(f"Theme-Based Narratives: {len(theme_based)} ({len(theme_based)/len(narratives)*100:.1f}%)")
        print(f"Entity-Based Narratives: {len(entity_based)} ({len(entity_based)/len(narratives)*100:.1f}%)")
        print()
        
        # Show examples of theme-based narratives
        print("=" * 80)
        print("THEME-BASED NARRATIVES (10 examples)")
        print("=" * 80)
        for i, narrative in enumerate(theme_based[:10], 1):
            fingerprint = narrative.get('fingerprint', {})
            nucleus_entity = fingerprint.get('nucleus_entity', '') or narrative.get('theme', '')
            print(f"{i}. ID: {narrative.get('_id')}")
            print(f"   Nucleus Entity: {nucleus_entity}")
            print(f"   Theme: {narrative.get('theme')}")
            print(f"   Title: {narrative.get('title')}")
            print(f"   State: {narrative.get('lifecycle_state')}")
            print(f"   Created: {narrative.get('first_seen')}")
            print(f"   Article Count: {len(narrative.get('article_ids', []))}")
            print()
        
        if len(theme_based) > 10:
            print(f"... and {len(theme_based) - 10} more theme-based narratives")
            print()
        
        # Show examples of entity-based narratives
        print("=" * 80)
        print("ENTITY-BASED NARRATIVES (10 examples)")
        print("=" * 80)
        for i, narrative in enumerate(entity_based[:10], 1):
            fingerprint = narrative.get('fingerprint', {})
            nucleus_entity = fingerprint.get('nucleus_entity', '') or narrative.get('theme', '')
            print(f"{i}. ID: {narrative.get('_id')}")
            print(f"   Nucleus Entity: {nucleus_entity}")
            print(f"   Theme: {narrative.get('theme')}")
            print(f"   Title: {narrative.get('title')}")
            print(f"   State: {narrative.get('lifecycle_state')}")
            print(f"   Created: {narrative.get('first_seen')}")
            print(f"   Article Count: {len(narrative.get('article_ids', []))}")
            print()
        
        if len(entity_based) > 10:
            print(f"... and {len(entity_based) - 10} more entity-based narratives")
            print()
        
        # Show breakdown by state for each category
        print("=" * 80)
        print("BREAKDOWN BY STATE")
        print("=" * 80)
        print()
        
        print("Theme-Based Narratives by State:")
        theme_states = {}
        for narrative in theme_based:
            state = narrative.get('lifecycle_state', 'unknown')
            theme_states[state] = theme_states.get(state, 0) + 1
        for state, count in sorted(theme_states.items(), key=lambda x: x[1], reverse=True):
            print(f"  {state}: {count}")
        print()
        
        print("Entity-Based Narratives by State:")
        entity_states = {}
        for narrative in entity_based:
            state = narrative.get('lifecycle_state', 'unknown')
            entity_states[state] = entity_states.get(state, 0) + 1
        for state, count in sorted(entity_states.items(), key=lambda x: x[1], reverse=True):
            print(f"  {state}: {count}")
        print()
        
        # Show nucleus_entity distribution for theme-based
        print("=" * 80)
        print("THEME-BASED NUCLEUS_ENTITY DISTRIBUTION (Top 20)")
        print("=" * 80)
        theme_entities = {}
        for narrative in theme_based:
            fingerprint = narrative.get('fingerprint', {})
            entity = fingerprint.get('nucleus_entity', '') or narrative.get('theme', 'unknown')
            theme_entities[entity] = theme_entities.get(entity, 0) + 1
        
        for entity, count in sorted(theme_entities.items(), key=lambda x: x[1], reverse=True)[:20]:
            print(f"  {entity}: {count} narratives")
        print()
        
        # Show nucleus_entity distribution for entity-based
        print("=" * 80)
        print("ENTITY-BASED NUCLEUS_ENTITY DISTRIBUTION (Top 20)")
        print("=" * 80)
        entity_entities = {}
        for narrative in entity_based:
            fingerprint = narrative.get('fingerprint', {})
            entity = fingerprint.get('nucleus_entity', '') or narrative.get('theme', 'unknown')
            entity_entities[entity] = entity_entities.get(entity, 0) + 1
        
        for entity, count in sorted(entity_entities.items(), key=lambda x: x[1], reverse=True)[:20]:
            print(f"  {entity}: {count} narratives")
        print()
        
        # Summary
        print("=" * 80)
        print("BACKFILL SCOPE SUMMARY")
        print("=" * 80)
        print(f"Narratives requiring theme-based fingerprint: {len(theme_based)}")
        print(f"Narratives with entity-based fingerprint (no change): {len(entity_based)}")
        print()
        print("Next Steps:")
        print("1. Review the theme-based examples to confirm categorization logic")
        print("2. Run backfill script to generate theme-based fingerprints")
        print("3. Verify fingerprint quality after backfill")
        print()
    
    finally:
        await mongo_manager.close()


if __name__ == '__main__':
    asyncio.run(count_narratives())
