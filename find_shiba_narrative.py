import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os

async def find_narrative():
    client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))
    db = client['crypto_news_aggregator']

    # Search for Shiba-related narratives
    narratives = []
    async for narrative in db.narratives.find({'theme': {'$regex': 'Shiba', '$options': 'i'}}):
        narratives.append(narrative)

    if not narratives:
        print("No Shiba narratives found. Let's search for all narratives with mismatches...")
        # Find any narrative with a mismatch
        async for narrative in db.narratives.find({}).limit(500):
            article_count = narrative.get('article_count', 0)
            actual_count = len(narrative.get('article_ids', []))
            if article_count != actual_count:
                print(f'\nTheme: {narrative.get("theme")}')
                print(f'Article count field: {article_count}')
                print(f'Actual article IDs: {actual_count}')
                print(f'ID: {narrative.get("_id")}')
                break
    else:
        for narrative in narratives:
            print(f'\nTheme: {narrative.get("theme")}')
            print(f'Article count field: {narrative.get("article_count")}')
            print(f'Actual article IDs: {len(narrative.get("article_ids", []))}')
            print(f'Mismatch: {narrative.get("article_count") != len(narrative.get("article_ids", []))}')

    client.close()

asyncio.run(find_narrative())
