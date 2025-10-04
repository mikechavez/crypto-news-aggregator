"""
Create mock entity mentions from articles to enable signal scoring.
This extracts entities from article titles using simple keyword matching.
"""
import asyncio
import os
import re
from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv()
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

# Common crypto entities to look for
CRYPTO_ENTITIES = {
    'Bitcoin', 'BTC', 'Ethereum', 'ETH', 'Solana', 'SOL', 'Cardano', 'ADA',
    'XRP', 'Ripple', 'Polkadot', 'DOT', 'Avalanche', 'AVAX', 'Chainlink', 'LINK',
    'Polygon', 'MATIC', 'Litecoin', 'LTC', 'Stellar', 'XLM', 'Tether', 'USDC',
    'Binance', 'Coinbase', 'Kraken', 'SEC', 'BlackRock', 'PayPal', 'Tesla',
    'MicroStrategy', 'Grayscale', 'FTX', 'Alameda', 'Circle', 'Tron', 'TRX',
    'Uniswap', 'Aave', 'Lido', 'Maker', 'Compound', 'Curve', 'Synthetix',
    'Gemini', 'Paxos', 'Celsius', 'BlockFi', 'Nexo', 'Crypto.com', 'KuCoin',
    'Bybit', 'OKX', 'Huobi', 'Gate.io', 'Bitfinex', 'Bitstamp'
}

def extract_entities_from_text(text):
    """Extract crypto entities from text using simple keyword matching."""
    if not text:
        return []
    
    entities = []
    text_upper = text.upper()
    
    for entity in CRYPTO_ENTITIES:
        # Look for whole word matches
        pattern = r'\b' + re.escape(entity) + r'\b'
        if re.search(pattern, text, re.IGNORECASE):
            entities.append({
                'value': entity,
                'type': 'CRYPTO_ENTITY',
                'confidence': 0.8
            })
    
    return entities

async def main():
    client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))
    db = client[os.getenv('MONGODB_DB_NAME')]
    
    print("Creating mock entity mentions from articles...")
    
    # Get all articles
    cursor = db.articles.find({})
    articles_processed = 0
    mentions_created = 0
    
    async for article in cursor:
        article_id = article['_id']
        title = article.get('title', '')
        content = article.get('content', '')
        source = article.get('source', 'unknown')
        published_at = article.get('published_at')
        
        # Extract entities from title and content
        text = f"{title} {content}"
        entities = extract_entities_from_text(text)
        
        if entities:
            # Update article with entities
            await db.articles.update_one(
                {'_id': article_id},
                {'$set': {'entities': entities}}
            )
            
            # Create entity mentions
            for entity in entities:
                mention = {
                    'entity': entity['value'],
                    'entity_type': entity['type'],
                    'article_id': article_id,
                    'source': source,
                    'sentiment': 'neutral',
                    'confidence': entity['confidence'],
                    'is_primary': True,
                    'created_at': published_at or datetime.now(timezone.utc),
                    'metadata': {
                        'article_title': title,
                        'mock_extraction': True
                    }
                }
                await db.entity_mentions.insert_one(mention)
                mentions_created += 1
            
            articles_processed += 1
            if articles_processed % 50 == 0:
                print(f"Processed {articles_processed} articles, created {mentions_created} mentions...")
    
    print(f"\nComplete!")
    print(f"Articles processed: {articles_processed}")
    print(f"Entity mentions created: {mentions_created}")
    
    client.close()

asyncio.run(main())
