#!/usr/bin/env python3
"""
Fix legacy entity types in MongoDB signal_scores collection.
Specifically fixes "CRYPTO_ENTITY" to proper types.
"""
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))
    db = client[os.getenv('MONGODB_DB_NAME', 'crypto_news')]
    
    print("=" * 70)
    print("FIXING LEGACY ENTITY TYPES IN SIGNAL_SCORES")
    print("=" * 70)
    print()
    
    # Find all signals with CRYPTO_ENTITY type
    print("🔍 Finding signals with 'CRYPTO_ENTITY' type...")
    legacy_signals = await db.signal_scores.find({
        "entity_type": "CRYPTO_ENTITY"
    }).to_list(length=100)
    
    if not legacy_signals:
        print("✓ No legacy entity types found!")
        client.close()
        return
    
    print(f"Found {len(legacy_signals)} signals with legacy type:")
    for signal in legacy_signals:
        print(f"  - {signal.get('entity')} (score: {signal.get('score')})")
    print()
    
    # Map entities to correct types
    entity_type_map = {
        # Cryptocurrencies
        "Bitcoin": "cryptocurrency",
        "Ethereum": "cryptocurrency",
        "Solana": "cryptocurrency",
        "Cardano": "cryptocurrency",
        "Polkadot": "cryptocurrency",
        "Avalanche": "cryptocurrency",
        "Polygon": "cryptocurrency",
        "Chainlink": "cryptocurrency",
        "Litecoin": "cryptocurrency",
        "Ripple": "cryptocurrency",
        "Stellar": "cryptocurrency",
        "Tron": "cryptocurrency",
        "Dogecoin": "cryptocurrency",
        
        # Stablecoins
        "Tether": "cryptocurrency",
        "USDC": "cryptocurrency",
        
        # DeFi Protocols
        "Aave": "protocol",
        "Uniswap": "protocol",
        "Lido DAO": "protocol",
        "Maker": "protocol",
        "Compound": "protocol",
        
        # Exchanges (Companies)
        "FTX": "company",
        "Binance": "company",
        "Coinbase": "company",
        "Kraken": "company",
        "KuCoin": "company",
        "Gemini": "company",
        "Crypto.com": "company",
        
        # Traditional Companies
        "BlackRock": "company",
        "PayPal": "company",
        "Paxos": "company",
        "Circle": "company",
        "MicroStrategy": "company",
        "Tesla": "company",
        "Square": "company",
        
        # Government/Regulatory Organizations
        "SEC": "organization",
        "Federal Reserve": "organization",
        "CFTC": "organization",
        "IMF": "organization",
        "World Bank": "organization",
        "US government": "organization",
    }
    
    print("🔧 Updating entity types...")
    updated_count = 0
    
    for signal in legacy_signals:
        entity = signal.get('entity')
        correct_type = entity_type_map.get(entity, "cryptocurrency")  # Default to cryptocurrency
        
        result = await db.signal_scores.update_one(
            {"_id": signal["_id"]},
            {"$set": {"entity_type": correct_type}}
        )
        
        if result.modified_count > 0:
            print(f"  ✓ Updated {entity}: CRYPTO_ENTITY → {correct_type}")
            updated_count += 1
        else:
            print(f"  ✗ Failed to update {entity}")
    
    print()
    print(f"✅ Updated {updated_count} of {len(legacy_signals)} signals")
    print()
    
    # Verify the changes
    print("🔍 Verifying changes...")
    remaining_legacy = await db.signal_scores.count_documents({
        "entity_type": "CRYPTO_ENTITY"
    })
    
    if remaining_legacy == 0:
        print("✓ All legacy entity types have been fixed!")
    else:
        print(f"⚠️  {remaining_legacy} legacy entity types still remain")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(main())
