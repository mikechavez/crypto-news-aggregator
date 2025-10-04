"""
Clear orphaned entity mentions and regenerate from current articles.
"""
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))
    db = client[os.getenv('MONGODB_DB_NAME')]
    
    print("Step 1: Clearing orphaned entity mentions...")
    
    # Delete all entity mentions (they're all orphaned)
    result = await db.entity_mentions.delete_many({})
    print(f"Deleted {result.deleted_count} orphaned entity mentions")
    
    print("\nStep 2: Clearing entities field from articles...")
    
    # Clear entities field from all articles so backfill script will process them
    result = await db.articles.update_many(
        {},
        {'$unset': {'entities': ''}}
    )
    print(f"Cleared entities from {result.modified_count} articles")
    
    print("\nStep 3: Ready for entity extraction")
    print("Run: poetry run python scripts/backfill_entities.py --yes")
    
    client.close()

asyncio.run(main())
