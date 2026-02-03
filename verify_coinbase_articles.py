import asyncio
import json
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from crypto_news_aggregator.core.config import get_settings

async def verify_coinbase():
    settings = get_settings()
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_NAME]

    # Find Coinbase narrative
    print("🔍 Searching for Coinbase narrative...")
    narrative = await db.narratives.find_one({
        'title': {'$regex': 'Coinbase', '$options': 'i'}
    })

    if not narrative:
        print("❌ Coinbase narrative not found")
        client.close()
        return

    print(f"✅ Found: {narrative.get('title')}")
    print(f"   Theme: {narrative.get('theme')}")
    print(f"   Article Count: {narrative.get('article_count')}")
    print(f"   Entities: {narrative.get('entities')}")

    # Get all article IDs
    article_ids = narrative.get('article_ids', [])
    print(f"\n📊 Total article IDs: {len(article_ids)}")

    # Convert to ObjectIds
    object_ids = []
    for aid in article_ids:
        try:
            if isinstance(aid, str):
                object_ids.append(ObjectId(aid))
            else:
                object_ids.append(aid)
        except:
            pass

    print(f"✅ Converted {len(object_ids)} IDs to ObjectIds")

    # Fetch all articles
    articles = []
    cursor = db.articles.find({"_id": {"$in": object_ids}}).sort("published_at", -1)
    async for article in cursor:
        articles.append(article)

    print(f"✅ Retrieved {len(articles)} articles from database")

    # Display articles
    print(f"\n{'='*130}")
    print(f"{'#':<4} {'Title':<60} {'Source':<15} {'Published':<20}")
    print(f"{'='*130}")

    for i, article in enumerate(articles, 1):
        title = article.get('title', 'N/A')[:57]
        source = article.get('source', 'N/A')[:13]
        published = article.get('published_at', 'N/A')
        if published != 'N/A':
            published_str = published.strftime('%Y-%m-%d %H:%M') if hasattr(published, 'strftime') else str(published)[:19]
        else:
            published_str = 'N/A'

        print(f"{i:<4} {title:<60} {source:<15} {published_str:<20}")

    # Sample detailed view
    print(f"\n{'='*130}")
    print(f"Sample Analysis (First 5 articles):")
    print(f"{'='*130}")
    for i, article in enumerate(articles[:5], 1):
        print(f"\n{i}. Title: {article.get('title')}")
        print(f"   Source: {article.get('source')}")
        print(f"   Published: {article.get('published_at')}")
        print(f"   URL: {article.get('url')[:100]}...")

    client.close()

asyncio.run(verify_coinbase())
