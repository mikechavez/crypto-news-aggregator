import asyncio
import json
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from crypto_news_aggregator.core.config import get_settings

async def export_headlines():
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

    # Create output data
    output = {
        "narrative": {
            "title": narrative.get('title'),
            "theme": narrative.get('theme'),
            "summary": narrative.get('summary'),
            "entities": narrative.get('entities'),
            "article_count": narrative.get('article_count'),
        },
        "articles": []
    }

    # Add each article with index
    for i, article in enumerate(articles, 1):
        output["articles"].append({
            "index": i,
            "title": article.get('title'),
            "source": article.get('source'),
            "published_at": article.get('published_at').isoformat() if article.get('published_at') else 'N/A',
            "url": article.get('url'),
            "id": str(article.get('_id'))
        })

    # Save to file
    output_file = '/Users/mc/dev-projects/crypto-news-aggregator/coinbase_headlines_review.json'
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n✅ Exported {len(articles)} headlines to: {output_file}")

    # Also create a text file for easier reading
    text_file = '/Users/mc/dev-projects/crypto-news-aggregator/coinbase_headlines_review.txt'
    with open(text_file, 'w') as f:
        f.write(f"COINBASE NARRATIVE REVIEW\n")
        f.write(f"{'='*120}\n\n")
        f.write(f"Narrative Title: {narrative.get('title')}\n")
        f.write(f"Theme: {narrative.get('theme')}\n")
        f.write(f"Summary: {narrative.get('summary')}\n")
        f.write(f"Entities: {', '.join(narrative.get('entities', []))}\n")
        f.write(f"Total Articles: {len(articles)}\n")
        f.write(f"\n{'='*120}\n")
        f.write(f"HEADLINES (Total: {len(articles)})\n")
        f.write(f"{'='*120}\n\n")

        for i, article in enumerate(articles, 1):
            f.write(f"{i}. {article.get('title')}\n")
            f.write(f"   Source: {article.get('source')}\n")
            f.write(f"   Published: {article.get('published_at').isoformat() if article.get('published_at') else 'N/A'}\n")
            f.write(f"   URL: {article.get('url')}\n")
            f.write(f"\n")

    print(f"✅ Also exported to text format: {text_file}")
    print(f"\nFiles ready for review!")

    client.close()

asyncio.run(export_headlines())
