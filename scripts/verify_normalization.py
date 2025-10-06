#!/usr/bin/env python3
"""
Verification script to check if entity normalization is working on new data.

Usage:
    python scripts/verify_normalization.py
"""

import asyncio
from datetime import datetime, timezone, timedelta
from crypto_news_aggregator.db.mongodb import mongo_manager


async def verify_normalization():
    """Check if new entity mentions are being normalized."""
    db = await mongo_manager.get_async_database()
    
    # Check for mentions from last 2 hours
    two_hours_ago = datetime.now(timezone.utc) - timedelta(hours=2)
    
    print("=" * 70)
    print("Entity Normalization Verification")
    print("=" * 70)
    print(f"\nChecking mentions created after: {two_hours_ago.isoformat()}")
    
    # Check for non-canonical ticker mentions (should be 0)
    print("\n--- Checking for Non-Canonical Mentions (Should be 0) ---")
    non_canonical = ["BTC", "$BTC", "btc", "ETH", "$ETH", "eth", 
                     "SOL", "$SOL", "sol", "DOGE", "$DOGE", "doge"]
    
    total_non_canonical = 0
    for entity in non_canonical:
        count = await db.entity_mentions.count_documents({
            "entity": entity,
            "created_at": {"$gte": two_hours_ago}
        })
        if count > 0:
            print(f"❌ {entity}: {count} mentions (SHOULD BE 0!)")
            total_non_canonical += count
        else:
            print(f"✅ {entity}: 0 mentions")
    
    # Check for canonical mentions (should be > 0 if articles were processed)
    print("\n--- Checking for Canonical Mentions (Should be > 0) ---")
    canonical = ["Bitcoin", "Ethereum", "Solana", "Dogecoin"]
    
    total_canonical = 0
    for entity in canonical:
        count = await db.entity_mentions.count_documents({
            "entity": entity,
            "created_at": {"$gte": two_hours_ago}
        })
        if count > 0:
            print(f"✅ {entity}: {count} mentions")
            total_canonical += count
        else:
            print(f"⚪ {entity}: 0 mentions (no new articles)")
    
    # Check total new mentions
    print("\n--- Summary ---")
    total_new = await db.entity_mentions.count_documents({
        "created_at": {"$gte": two_hours_ago}
    })
    print(f"Total new mentions: {total_new}")
    print(f"Canonical mentions: {total_canonical}")
    print(f"Non-canonical mentions: {total_non_canonical}")
    
    # Check for is_primary flag
    print("\n--- Checking is_primary Flag ---")
    primary_count = await db.entity_mentions.count_documents({
        "created_at": {"$gte": two_hours_ago},
        "is_primary": True
    })
    context_count = await db.entity_mentions.count_documents({
        "created_at": {"$gte": two_hours_ago},
        "is_primary": False
    })
    missing_flag = await db.entity_mentions.count_documents({
        "created_at": {"$gte": two_hours_ago},
        "is_primary": {"$exists": False}
    })
    
    print(f"Primary entities: {primary_count}")
    print(f"Context entities: {context_count}")
    print(f"Missing flag: {missing_flag}")
    
    # Final verdict
    print("\n" + "=" * 70)
    if total_non_canonical == 0 and total_new > 0:
        print("✅ NORMALIZATION WORKING CORRECTLY!")
        print("   All new mentions use canonical names.")
    elif total_non_canonical > 0:
        print("❌ NORMALIZATION NOT WORKING!")
        print(f"   Found {total_non_canonical} non-canonical mentions.")
        print("   Check Railway logs for errors.")
    elif total_new == 0:
        print("⚠️  NO NEW MENTIONS FOUND")
        print("   Wait for next RSS fetch cycle and run again.")
    print("=" * 70)
    
    await mongo_manager.close()


if __name__ == "__main__":
    asyncio.run(verify_normalization())
