"""
Reclassify government/regulatory entities from 'company' to 'organization'.
"""
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))
    db = client[os.getenv('MONGODB_DB_NAME')]
    
    # Known organizations to reclassify
    organizations = [
        'SEC', 'Federal Reserve', 'IMF', 'World Bank', 
        'CFTC', 'FinCEN', 'Treasury', 'Department of Justice',
        'FBI', 'IRS', 'European Central Bank', 'Bank of England',
        'Bank of Japan', 'People\'s Bank of China', 'US Treasury',
        'European Commission', 'Financial Action Task Force',
        'Basel Committee', 'G20', 'United Nations',
        'World Economic Forum', 'OECD', 'BIS',
        'SBI', 'Standard Chartered',  # These were showing as companies but are financial institutions
        'Morgan Stanley', 'Goldman Sachs', 'JPMorgan',
        'Fidelity', 'Vanguard', 'BlackRock',  # Investment firms
    ]
    
    print("=" * 70)
    print("RECLASSIFYING ENTITIES TO 'ORGANIZATION' TYPE")
    print("=" * 70)
    
    total_updated = 0
    
    for org_name in organizations:
        # Update entity mentions
        result = await db.entity_mentions.update_many(
            {
                'entity': org_name,
                'entity_type': 'company'
            },
            {
                '$set': {'entity_type': 'organization'}
            }
        )
        
        if result.modified_count > 0:
            print(f"✓ {org_name:30s}: {result.modified_count:4d} mentions updated")
            total_updated += result.modified_count
        else:
            # Check if it exists with different type
            count = await db.entity_mentions.count_documents({'entity': org_name})
            if count > 0:
                existing = await db.entity_mentions.find_one({'entity': org_name})
                print(f"  {org_name:30s}: Already {existing.get('entity_type')} ({count} mentions)")
    
    print("\n" + "=" * 70)
    print(f"✅ Total mentions reclassified: {total_updated}")
    
    # Update signal scores
    print("\nUpdating signal scores...")
    signal_result = await db.signal_scores.update_many(
        {
            'entity': {'$in': organizations},
            'entity_type': 'company'
        },
        {
            '$set': {'entity_type': 'organization'}
        }
    )
    
    print(f"✓ Signal scores updated: {signal_result.modified_count}")
    
    # Show summary of organizations
    print("\n" + "=" * 70)
    print("ORGANIZATION ENTITY SUMMARY")
    print("=" * 70)
    
    org_count = await db.entity_mentions.count_documents({
        'entity_type': 'organization',
        'is_primary': True
    })
    
    print(f"\nTotal primary organization mentions: {org_count}")
    
    # Get top organizations
    pipeline = [
        {'$match': {'entity_type': 'organization', 'is_primary': True}},
        {'$group': {'_id': '$entity', 'count': {'$sum': 1}}},
        {'$sort': {'count': -1}},
        {'$limit': 10}
    ]
    
    print("\nTop 10 organizations by mention count:")
    async for result in db.entity_mentions.aggregate(pipeline):
        print(f"  {result['_id']:30s}: {result['count']:4d} mentions")
    
    client.close()

asyncio.run(main())
