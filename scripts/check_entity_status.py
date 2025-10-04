"""
Quick verification script to check the current state of entity mentions in the database.
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from collections import Counter


async def main():
    mongo_uri = os.getenv("MONGODB_URI")
    client = AsyncIOMotorClient(mongo_uri)
    db = client[os.getenv("MONGODB_DB_NAME", "crypto_news_db")]
    
    # Count total entity mentions
    total = await db.entity_mentions.count_documents({})
    print(f"Total entity mentions: {total}")
    
    if total == 0:
        print("\n⚠️  No entity mentions found. You may need to:")
        print("   1. Run the RSS fetcher to ingest articles")
        print("   2. Run the entity extraction backfill script")
        client.close()
        return
    
    # Count by entity_type
    type_counts = await db.entity_mentions.aggregate([
        {"$group": {"_id": "$entity_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]).to_list(None)
    
    print("\nEntity mentions by type:")
    for item in type_counts:
        entity_type = item["_id"] or "UNCLASSIFIED"
        print(f"  {entity_type:15}: {item['count']:4}")
    
    # Count by is_primary
    primary_counts = await db.entity_mentions.aggregate([
        {"$group": {"_id": "$is_primary", "count": {"$sum": 1}}},
    ]).to_list(None)
    
    print("\nEntity mentions by primary status:")
    for item in primary_counts:
        is_primary = item["_id"]
        status = "PRIMARY" if is_primary else "CONTEXT" if is_primary is False else "UNSET"
        print(f"  {status:15}: {item['count']:4}")
    
    # Count unique entities
    unique_entities = await db.entity_mentions.distinct("entity")
    print(f"\nUnique entities: {len(unique_entities)}")
    
    # Show sample of unclassified entities (if any)
    unclassified = await db.entity_mentions.find(
        {"entity_type": {"$exists": False}}
    ).limit(10).to_list(10)
    
    if unclassified:
        print(f"\n⚠️  Found {len(unclassified)} unclassified entity mentions (showing first 10):")
        unique_unclassified = set()
        for mention in unclassified:
            unique_unclassified.add(mention["entity"])
        for entity in sorted(unique_unclassified):
            print(f"  - {entity}")
        print("\n💡 Run: poetry run python scripts/classify_existing_entities.py")
    else:
        print("\n✅ All entity mentions are classified!")
    
    # Show top 10 most mentioned entities
    top_entities = await db.entity_mentions.aggregate([
        {"$group": {"_id": "$entity", "count": {"$sum": 1}, "type": {"$first": "$entity_type"}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]).to_list(10)
    
    if top_entities:
        print("\nTop 10 most mentioned entities:")
        for item in top_entities:
            entity_type = item.get("type", "unknown")
            print(f"  {item['_id']:20} ({entity_type:12}): {item['count']:3} mentions")
    
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
