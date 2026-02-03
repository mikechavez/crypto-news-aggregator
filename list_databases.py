import asyncio
import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

async def list_dbs():
    url = os.getenv('MONGODB_URI')
    client = AsyncIOMotorClient(url)

    try:
        # List all databases
        result = await client.admin.command('listDatabases')
        databases = result.get('databases', [])

        print('=== Available Databases ===\n')
        for db in databases:
            name = db['name']
            size = db.get('sizeOnDisk', 0)
            print(f'{name}: {size:,} bytes')

        # Try to connect to crypto_news_aggregator
        print('\n=== crypto_news_aggregator Collections ===\n')
        db = client['crypto_news_aggregator']
        collections = await db.list_collection_names()
        for collection in collections:
            count = await db[collection].count_documents({})
            print(f'{collection}: {count} documents')

    except Exception as e:
        print(f'Error: {e}')

    client.close()

asyncio.run(list_dbs())
