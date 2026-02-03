import asyncio
import json
from motor.motor_asyncio import AsyncIOMotorClient
from crypto_news_aggregator.core.config import get_settings

async def inspect_narrative():
    settings = get_settings()
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_NAME]

    # Get the Shiba narrative with focus fields
    narrative = await db.narratives.find_one({'title': {'$regex': 'Shiba', '$options': 'i'}})

    if narrative:
        print('=== Shiba Inu Narrative - Full Document ===\n')
        print(f'Title: {narrative.get("title")}')
        print(f'Theme: {narrative.get("theme")}')
        print(f'Focus: {narrative.get("focus")}')
        print(f'Narrative Focus: {narrative.get("narrative_focus")}')
        print(f'Nucleus Entity: {narrative.get("nucleus_entity")}')
        print(f'Article Count: {narrative.get("article_count")}')
        print(f'Article IDs Length: {len(narrative.get("article_ids", []))}')
        print(f'Lifecycle State: {narrative.get("lifecycle_state")}')
        print(f'\nFull Document:')
        print(json.dumps(narrative, indent=2, default=str))

    client.close()

asyncio.run(inspect_narrative())
