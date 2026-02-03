import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os

async def check_db():
    url = os.getenv('MONGODB_URI')
    print(f'MONGODB_URI set: {bool(url)}')
    print(f'MONGODB_URI prefix: {url[:50] if url else "NOT SET"}...')

    try:
        client = AsyncIOMotorClient(url)
        # Test connection
        await client.admin.command('ping')
        print('✅ Database connection successful')

        db = client['crypto_news_aggregator']
        collections = await db.list_collection_names()
        print(f'\nCollections in database: {collections}')

        # Count documents in each collection
        for collection in collections:
            count = await db[collection].count_documents({})
            print(f'  {collection}: {count} documents')

        client.close()
    except Exception as e:
        print(f'❌ Connection failed: {e}')

asyncio.run(check_db())
