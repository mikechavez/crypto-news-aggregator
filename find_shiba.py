import asyncio
import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

async def find_shiba():
    url = os.getenv('MONGODB_URI')
    client = AsyncIOMotorClient(url)

    db = client['crypto_news']

    # Search for any narratives with "Shiba" in the theme
    print('=== Searching for Shiba-related narratives ===\n')

    found = False
    async for narrative in db.narratives.find({'theme': {'$regex': 'Shiba', '$options': 'i'}}):
        found = True
        print(f'Theme: {narrative.get("theme")}')
        print(f'Article count field: {narrative.get("article_count")}')
        print(f'Actual article IDs: {len(narrative.get("article_ids", []))}')
        print(f'Lifecycle state: {narrative.get("lifecycle_state")}')
        print(f'ID: {narrative.get("_id")}\n')

    if not found:
        print('❌ No Shiba narratives found in database\n')
        print('Checking all active narratives...\n')

        # List some active narratives
        count = 0
        async for narrative in db.narratives.find({'lifecycle_state': 'active'}).limit(5):
            count += 1
            print(f'{count}. {narrative.get("theme")}')

    client.close()

asyncio.run(find_shiba())
