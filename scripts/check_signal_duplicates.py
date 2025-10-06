"""
Check for duplicate signal scores in production database.
"""
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()
from motor.motor_asyncio import AsyncIOMotorClient
import re

async def main():
    client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))
    db = client[os.getenv('MONGODB_DB_NAME')]
    
    print("Checking for duplicate signal scores in production...\n")
    print("="*80)
    
    # Check for Doge variants
    print("\n🐕 DOGE/DOGECOIN Signals:")
    print("-" * 80)
    doge_signals = await db.signal_scores.find({
        'entity': {'$regex': 'doge', '$options': 'i'}
    }).to_list(None)
    
    if doge_signals:
        for signal in doge_signals:
            print(f"Entity: {signal.get('entity')}")
            print(f"  Score: {signal.get('score', 0):.4f}")
            print(f"  Source Count: {signal.get('source_count', 0)}")
            print(f"  Last Updated: {signal.get('last_updated', 'N/A')}")
            print()
    else:
        print("  No signals found")
    
    # Check for BTC/Bitcoin variants
    print("\n₿ BTC/BITCOIN Signals:")
    print("-" * 80)
    btc_signals = await db.signal_scores.find({
        '$or': [
            {'entity': {'$regex': 'btc', '$options': 'i'}},
            {'entity': {'$regex': 'bitcoin', '$options': 'i'}}
        ]
    }).to_list(None)
    
    if btc_signals:
        for signal in btc_signals:
            print(f"Entity: {signal.get('entity')}")
            print(f"  Score: {signal.get('score', 0):.4f}")
            print(f"  Source Count: {signal.get('source_count', 0)}")
            print(f"  Last Updated: {signal.get('last_updated', 'N/A')}")
            print()
    else:
        print("  No signals found")
    
    # Check for SOL/Solana variants
    print("\n◎ SOL/SOLANA Signals:")
    print("-" * 80)
    sol_signals = await db.signal_scores.find({
        '$or': [
            {'entity': {'$regex': '^sol$', '$options': 'i'}},
            {'entity': {'$regex': 'solana', '$options': 'i'}}
        ]
    }).to_list(None)
    
    if sol_signals:
        for signal in sol_signals:
            print(f"Entity: {signal.get('entity')}")
            print(f"  Score: {signal.get('score', 0):.4f}")
            print(f"  Source Count: {signal.get('source_count', 0)}")
            print(f"  Last Updated: {signal.get('last_updated', 'N/A')}")
            print()
    else:
        print("  No signals found")
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY:")
    print(f"  Doge variants: {len(doge_signals)}")
    print(f"  BTC/Bitcoin variants: {len(btc_signals)}")
    print(f"  SOL/Solana variants: {len(sol_signals)}")
    
    total_duplicates = len(doge_signals) + len(btc_signals) + len(sol_signals)
    if total_duplicates > 3:
        print(f"\n⚠️  Found {total_duplicates} total signals - duplicates likely exist!")
        print("   Expected: 3 signals (1 for each normalized entity)")
    else:
        print(f"\n✅ Found {total_duplicates} total signals - normalization appears to be working!")
    
    client.close()

asyncio.run(main())
