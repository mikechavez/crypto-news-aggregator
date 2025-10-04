"""
Set is_primary flag for entities still using old types (project/ticker/event).
"""
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
    db = client[os.getenv("MONGODB_DB_NAME", "crypto_news_db")]
    
    # Map old types to is_primary flag
    primary_types = ["project", "ticker"]
    context_types = ["event"]
    
    # Update primary entities
    result_primary = await db.entity_mentions.update_many(
        {"entity_type": {"$in": primary_types}, "is_primary": {"$exists": False}},
        {"$set": {"is_primary": True}}
    )
    print(f"Set is_primary=True for {result_primary.modified_count} entities (project/ticker)")
    
    # Update context entities
    result_context = await db.entity_mentions.update_many(
        {"entity_type": {"$in": context_types}, "is_primary": {"$exists": False}},
        {"$set": {"is_primary": False}}
    )
    print(f"Set is_primary=False for {result_context.modified_count} entities (event)")
    
    client.close()
    print("✅ Done!")

if __name__ == "__main__":
    asyncio.run(main())
