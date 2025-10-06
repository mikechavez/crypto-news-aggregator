#!/usr/bin/env python3
"""
Reclassify entity types that were incorrectly categorized.
Fixes entities that were defaulted to 'cryptocurrency' but should be other types.
"""
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))
    db = client[os.getenv('MONGODB_DB_NAME', 'crypto_news')]
    
    print("=" * 70)
    print("RECLASSIFYING ENTITY TYPES IN SIGNAL_SCORES")
    print("=" * 70)
    print()
    
    # Comprehensive entity type mapping
    reclassifications = {
        # DeFi Protocols (currently cryptocurrency, should be protocol)
        "Aave": "protocol",
        "Uniswap": "protocol",
        "Lido DAO": "protocol",
        "Maker": "protocol",
        "Compound": "protocol",
        "Curve": "protocol",
        "SushiSwap": "protocol",
        
        # Traditional Companies (currently cryptocurrency, should be company)
        "BlackRock": "company",
        "PayPal": "company",
        "Paxos": "company",
        "Circle": "company",
        "MicroStrategy": "company",
        "Tesla": "company",
        "Square": "company",
        "Fidelity": "company",
        "Grayscale": "company",
        "JPMorgan": "company",
        "Goldman Sachs": "company",
        "Morgan Stanley": "company",
        "Visa": "company",
        "Mastercard": "company",
        "Walmart": "company",
        "Citi": "company",
        
        # Government/Regulatory Organizations (currently cryptocurrency, should be organization)
        "SEC": "organization",
        "Federal Reserve": "organization",
        "CFTC": "organization",
        "IMF": "organization",
        "World Bank": "organization",
        "US government": "organization",
        "Treasury": "organization",
        "Congress": "organization",
        "Senate": "organization",
        "House": "organization",
        "European Central Bank": "organization",
        "Bank of England": "organization",
    }
    
    print(f"🔍 Checking {len(reclassifications)} entities for reclassification...")
    print()
    
    updated_count = 0
    not_found_count = 0
    already_correct_count = 0
    
    for entity, correct_type in reclassifications.items():
        # Find the signal
        signal = await db.signal_scores.find_one({"entity": entity})
        
        if not signal:
            not_found_count += 1
            continue
        
        current_type = signal.get('entity_type')
        
        if current_type == correct_type:
            already_correct_count += 1
            print(f"  ✓ {entity}: Already correct ({correct_type})")
            continue
        
        # Update the entity type
        result = await db.signal_scores.update_one(
            {"_id": signal["_id"]},
            {"$set": {"entity_type": correct_type}}
        )
        
        if result.modified_count > 0:
            print(f"  ✓ Updated {entity}: {current_type} → {correct_type}")
            updated_count += 1
        else:
            print(f"  ✗ Failed to update {entity}")
    
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"✅ Updated: {updated_count}")
    print(f"✓  Already correct: {already_correct_count}")
    print(f"⊘  Not found in database: {not_found_count}")
    print()
    
    # Show current distribution
    print("=" * 70)
    print("CURRENT ENTITY TYPE DISTRIBUTION")
    print("=" * 70)
    
    pipeline = [
        {"$group": {
            "_id": "$entity_type",
            "count": {"$sum": 1}
        }},
        {"$sort": {"count": -1}}
    ]
    
    distribution = await db.signal_scores.aggregate(pipeline).to_list(length=100)
    
    for item in distribution:
        entity_type = item['_id'] if item['_id'] else "NULL"
        count = item['count']
        print(f"  {entity_type}: {count}")
    
    print()
    client.close()

if __name__ == "__main__":
    asyncio.run(main())
