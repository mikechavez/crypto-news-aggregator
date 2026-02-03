import asyncio
import os
import sys
from pathlib import Path

# Load environment variables from .env
from dotenv import load_dotenv
load_dotenv()

from motor.motor_asyncio import AsyncIOMotorClient

async def check_mismatches():
    url = os.getenv('MONGODB_URI')
    if not url:
        print('❌ MONGODB_URI not set')
        sys.exit(1)

    print(f'Connecting to MongoDB...')
    client = AsyncIOMotorClient(url)

    try:
        await client.admin.command('ping')
        print('✅ Connected to MongoDB\n')
    except Exception as e:
        print(f'❌ Connection failed: {e}')
        sys.exit(1)

    db = client['crypto_news_aggregator']

    # Count narratives with mismatches
    print('=== Scanning for Article Count Mismatches ===\n')

    mismatches = []
    total_count = 0

    async for narrative in db.narratives.find({}):
        total_count += 1
        article_count = narrative.get('article_count', 0)
        article_ids = narrative.get('article_ids', [])
        actual_count = len(article_ids)

        if article_count != actual_count:
            mismatches.append({
                'theme': narrative.get('theme'),
                'reported': article_count,
                'actual': actual_count,
                'id': narrative.get('_id'),
                'lifecycle_state': narrative.get('lifecycle_state')
            })

    print(f'Total narratives scanned: {total_count}')
    print(f'Narratives with mismatches: {len(mismatches)}\n')

    if mismatches:
        print('⚠️  MISMATCHES FOUND:\n')
        for m in mismatches[:10]:  # Show first 10
            print(f'Theme: {m["theme"]}')
            print(f'  Reported: {m["reported"]}, Actual: {m["actual"]}')
            print(f'  State: {m["lifecycle_state"]}')
            print(f'  ID: {m["id"]}\n')
        if len(mismatches) > 10:
            print(f'... and {len(mismatches) - 10} more')
    else:
        print('✅ NO MISMATCHES FOUND - Database is clean!')

    client.close()

asyncio.run(check_mismatches())
