"""
Migrate entities with old types (project/ticker/event) to new classification system.
Uses simple mapping rules instead of Claude API.
"""
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))
    db = client[os.getenv('MONGODB_DB_NAME')]
    
    # Simple mapping rules
    # ticker -> cryptocurrency (most tickers are crypto)
    # project -> check if it's a known protocol, otherwise mark as company
    # event -> concept
    
    print("Migrating old entity types...")
    
    # Migrate tickers to cryptocurrency
    result1 = await db.entity_mentions.update_many(
        {'entity_type': 'ticker'},
        {'$set': {'entity_type': 'cryptocurrency', 'is_primary': True}}
    )
    print(f'  Migrated {result1.modified_count} tickers -> cryptocurrency')
    
    # Migrate events to concept (context entities)
    result2 = await db.entity_mentions.update_many(
        {'entity_type': 'event'},
        {'$set': {'entity_type': 'concept', 'is_primary': False}}
    )
    print(f'  Migrated {result2.modified_count} events -> concept')
    
    # For projects, we need to be more careful
    # Get unique project entities
    projects = await db.entity_mentions.distinct('entity', {'entity_type': 'project'})
    
    # Known concepts/locations to filter out
    concepts = ['Pilot Program', 'Ai', 'Web3', 'DeFi', 'NFT']
    locations = ['New York', 'Abu Dhabi', 'Dubai', 'Hong Kong']
    
    for entity in projects:
        lower = entity.lower()
        
        if entity in concepts or any(c.lower() in lower for c in ['program', 'initiative']):
            # It's a concept
            await db.entity_mentions.update_many(
                {'entity': entity, 'entity_type': 'project'},
                {'$set': {'entity_type': 'concept', 'is_primary': False}}
            )
            print(f'    {entity} -> concept')
        
        elif entity in locations:
            # It's a location
            await db.entity_mentions.update_many(
                {'entity': entity, 'entity_type': 'project'},
                {'$set': {'entity_type': 'location', 'is_primary': False}}
            )
            print(f'    {entity} -> location')
        
        else:
            # Assume it's a protocol or company (primary entity)
            await db.entity_mentions.update_many(
                {'entity': entity, 'entity_type': 'project'},
                {'$set': {'entity_type': 'protocol', 'is_primary': True}}
            )
            print(f'    {entity} -> protocol')
    
    print("\n✅ Migration complete!")
    
    # Verify
    old_count = await db.entity_mentions.count_documents({'entity_type': {'$in': ['project', 'ticker', 'event']}})
    print(f'\nRemaining old types: {old_count} (should be 0)')
    
    client.close()

asyncio.run(main())
