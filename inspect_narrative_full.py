import asyncio
import json
from motor.motor_asyncio import AsyncIOMotorClient
from crypto_news_aggregator.core.config import get_settings

async def inspect_narrative():
    settings = get_settings()
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_NAME]

    # Find narratives with Shiba
    narratives = await db.narratives.find({
        '$or': [
            {'title': {'$regex': 'Shiba', '$options': 'i'}},
            {'focus': {'$regex': 'Shiba', '$options': 'i'}},
            {'theme': {'$regex': 'Shiba', '$options': 'i'}}
        ]
    }).to_list(length=10)

    print(f'Found {len(narratives)} Shiba-related narratives\n')

    for i, narrative in enumerate(narratives):
        print(f'=== Narrative {i+1} ===')
        print(f'Title: {narrative.get("title")}')
        print(f'Focus: {narrative.get("focus")}')
        print(f'Theme: {narrative.get("theme")}')
        print(f'Description: {narrative.get("description", "N/A")[:100]}')
        print(f'Article Count: {narrative.get("article_count")}')
        print(f'Article IDs: {len(narrative.get("article_ids", []))}')
        print(f'Lifecycle State: {narrative.get("lifecycle_state")}')
        print(f'\nAll Fields: {list(narrative.keys())}')
        print('---\n')

    client.close()

asyncio.run(inspect_narrative())
