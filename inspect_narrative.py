import asyncio
import json
from motor.motor_asyncio import AsyncIOMotorClient
from crypto_news_aggregator.core.config import get_settings

async def inspect_narrative():
    settings = get_settings()
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_NAME]

    # Find the Shiba Inu narrative
    narrative = await db.narratives.find_one({'focus': 'Shiba Inu'})

    if narrative:
        print('=== Full Narrative Document ===')
        print(json.dumps(narrative, indent=2, default=str))

        print('\n\n=== Available Fields ===')
        print(list(narrative.keys()))
    else:
        print('Narrative not found with focus=Shiba Inu')
        # Try to find any narratives with Shiba Inu in title/focus
        narratives = await db.narratives.find({'$or': [
            {'focus': {'$regex': 'Shiba', '$options': 'i'}},
            {'title': {'$regex': 'Shiba', '$options': 'i'}}
        ]}).to_list(length=5)
        print(f'Found {len(narratives)} narratives with Shiba:')
        for n in narratives:
            print(f'  - focus: {n.get("focus")}, title: {n.get("title")}')

    client.close()

asyncio.run(inspect_narrative())
