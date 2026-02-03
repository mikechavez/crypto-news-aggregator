import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os

async def check_narrative():
    client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))
    db = client['crypto_news_aggregator']

    # Find the narrative
    narrative = await db.narratives.find_one({
        'theme': {'$regex': 'Shiba Inu Price Volatility', '$options': 'i'}
    })

    if narrative:
        print(f'\n=== Shiba Inu Price Volatility Narrative ===')
        print(f'Theme: {narrative.get("theme")}')
        print(f'Article count field: {narrative.get("article_count")}')
        print(f'Actual article IDs count: {len(narrative.get("article_ids", []))}')
        print(f'Mismatch: {narrative.get("article_count") != len(narrative.get("article_ids", []))}')
        print(f'Lifecycle state: {narrative.get("lifecycle_state")}')
        print(f'ID: {narrative.get("_id")}')

        # Check which articles actually exist
        article_ids = narrative.get("article_ids", [])
        print(f'\nChecking {len(article_ids)} articles in database...')
        existing = await db.articles.count_documents({'_id': {'$in': article_ids}})
        print(f'Articles that exist in DB: {existing}')
        print(f'Articles that are missing: {len(article_ids) - existing}')

        # Find missing articles
        existing_ids = []
        async for article in db.articles.find({'_id': {'$in': article_ids}}, {'_id': 1}):
            existing_ids.append(article['_id'])

        missing_ids = [aid for aid in article_ids if aid not in existing_ids]
        if missing_ids:
            print(f'\nMissing article IDs: {missing_ids[:5]}...')
    else:
        print('Narrative not found')

    client.close()

asyncio.run(check_narrative())
