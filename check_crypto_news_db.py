import asyncio
import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

async def check_db():
    url = os.getenv('MONGODB_URI')
    client = AsyncIOMotorClient(url)

    db = client['crypto_news']
    collections = await db.list_collection_names()

    print('=== crypto_news Database Collections ===\n')
    for collection in collections:
        count = await db[collection].count_documents({})
        print(f'{collection}: {count} documents')

    # Now check for narratives with mismatches
    if 'narratives' in collections:
        print('\n=== Checking for Article Count Mismatches ===\n')

        mismatches = []
        total = await db.narratives.count_documents({})
        print(f'Total narratives: {total}')

        async for narrative in db.narratives.find({}):
            article_count = narrative.get('article_count', 0)
            article_ids = narrative.get('article_ids', [])
            actual_count = len(article_ids)

            if article_count != actual_count:
                mismatches.append({
                    'theme': narrative.get('theme'),
                    'reported': article_count,
                    'actual': actual_count,
                })

        print(f'Narratives with mismatches: {len(mismatches)}\n')

        if mismatches:
            print('⚠️  MISMATCHES FOUND:\n')
            for m in mismatches[:10]:
                print(f'Theme: {m["theme"]}')
                print(f'  Reported: {m["reported"]}, Actual: {m["actual"]}\n')
        else:
            print('✅ NO MISMATCHES FOUND')

    client.close()

asyncio.run(check_db())
