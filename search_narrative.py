import asyncio
import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

async def search():
    url = os.getenv('MONGODB_URI')
    client = AsyncIOMotorClient(url)
    db = client['crypto_news']

    # Search for narratives with "Volatility" or "Whale"
    searches = ['Volatility', 'Whale Bets', 'Price Volatility', 'Shiba Inu']

    for search_term in searches:
        print(f'\nSearching for "{search_term}"...')
        found = False
        async for narrative in db.narratives.find({'theme': {'$regex': search_term, '$options': 'i'}}):
            found = True
            theme = narrative.get('theme')
            reported = narrative.get('article_count')
            actual = len(narrative.get('article_ids', []))
            status = '✅' if reported == actual else '❌'
            print(f'{status} {theme}')
            print(f'   Count: {reported} reported, {actual} actual')

        if not found:
            print(f'  No narratives found')

    client.close()

asyncio.run(search())
