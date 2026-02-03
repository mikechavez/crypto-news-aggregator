import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os

async def verify_cleanup():
    client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))
    db = client['crypto_news_aggregator']

    print('=== Cleanup Verification Report ===\n')

    # Count narratives with mismatches
    mismatches = 0
    invalid_refs = 0
    duplicates_found = 0

    total_narratives = await db.narratives.count_documents({})
    print(f'Total narratives: {total_narratives}')

    async for narrative in db.narratives.find({}):
        article_count = narrative.get('article_count', 0)
        article_ids = narrative.get('article_ids', [])
        actual_count = len(article_ids)

        if article_count != actual_count:
            mismatches += 1
            print(f'\n⚠️  MISMATCH FOUND:')
            print(f'   Theme: {narrative.get("theme")}')
            print(f'   Reported: {article_count}, Actual: {actual_count}')
            print(f'   ID: {narrative.get("_id")}')

        # Check for duplicates in article_ids
        if len(article_ids) != len(set(article_ids)):
            duplicates_found += 1
            print(f'\n⚠️  DUPLICATE ARTICLES:')
            print(f'   Theme: {narrative.get("theme")}')
            print(f'   ID: {narrative.get("_id")}')

    print(f'\n=== Summary ===')
    print(f'Narratives with count mismatches: {mismatches}')
    print(f'Narratives with duplicate article IDs: {duplicates_found}')
    print(f'Status: {"✅ ALL CLEAN" if mismatches == 0 and duplicates_found == 0 else "❌ ISSUES FOUND"}')

    client.close()

asyncio.run(verify_cleanup())
