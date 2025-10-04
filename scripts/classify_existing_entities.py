"""
Classify all existing entities in entity_mentions collection that don't have entity_type set.
Uses Claude Haiku to batch-classify entities based on their names.
"""

from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file

import asyncio
import os
import json
from motor.motor_asyncio import AsyncIOMotorClient
from anthropic import Anthropic


async def main():
    # Connect to MongoDB
    mongo_uri = os.getenv("MONGODB_URI")
    client = AsyncIOMotorClient(mongo_uri)
    db = client[os.getenv("MONGODB_DB_NAME", "crypto_news_db")]
    
    # Get unique entities that need classification (where entity_type is missing)
    pipeline = [
        {"$match": {"entity_type": {"$exists": False}}},
        {"$group": {"_id": "$entity"}},
        {"$project": {"entity": "$_id", "_id": 0}}
    ]
    result = await db.entity_mentions.aggregate(pipeline).to_list(None)
    entities = [doc["entity"] for doc in result]
    
    if not entities:
        print("No entities need classification. All done!")
        return
    
    print(f"Classifying {len(entities)} entities...")
    
    anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
    # Process in batches of 50
    for i in range(0, len(entities), 50):
        batch = entities[i:i+50]
        
        prompt = f"""Classify these crypto-related entities by type. Return ONLY valid JSON with no markdown.

Entity types:
- cryptocurrency: Bitcoin, Ethereum, Litecoin (tradeable coins)
- blockchain: Ethereum, Solana, Avalanche (platforms)
- protocol: Uniswap, Aave, Lido (DeFi protocols)
- company: Circle, Coinbase, BlackRock, Standard Chartered
- event: launch, hack, upgrade, halving, rally
- concept: DeFi, regulation, staking, altcoin, ETF
- person: Vitalink Buterin, Michael Saylor, Donald Trump, Melania
- location: New York, Abu Dhabi, Dubai

Entities to classify: {json.dumps(batch)}

Return format:
{{
  "Bitcoin": {{"type": "cryptocurrency", "confidence": 0.95}},
  "New York": {{"type": "location", "confidence": 0.90}}
}}

Only include entities from the input list. Confidence should be 0.80-1.00."""

        try:
            response = anthropic_client.messages.create(
                model="claude-haiku-3-5-20241022",
                max_tokens=3000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse JSON response (handle markdown wrapping)
            text = response.content[0].text
            text = text.replace("```json\n", "").replace("```json", "").replace("\n```", "").replace("```", "").strip()
            classifications = json.loads(text)
            
            # Update database
            for entity_name, data in classifications.items():
                # Determine is_primary based on type
                entity_type = data["type"]
                is_primary = entity_type in ["cryptocurrency", "blockchain", "protocol", "company"]
                
                result = await db.entity_mentions.update_many(
                    {"entity": entity_name},
                    {"$set": {
                        "entity_type": entity_type,
                        "is_primary": is_primary,
                        "confidence": data.get("confidence", 0.85)
                    }}
                )
                print(f"  {entity_name}: {entity_type} (primary={is_primary}, updated {result.modified_count} docs)")
            
            print(f"✓ Batch {i//50 + 1}/{(len(entities) + 49)//50} complete")
            
        except Exception as e:
            print(f"✗ Error in batch {i//50 + 1}: {e}")
            continue
    
    print("✅ Classification complete!")
    
    # Show summary
    summary = await db.entity_mentions.aggregate([
        {"$group": {
            "_id": {"type": "$entity_type", "is_primary": "$is_primary"},
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id.is_primary": -1, "_id.type": 1}}
    ]).to_list(None)
    
    print("\nSummary:")
    for item in summary:
        type_name = item["_id"]["type"] or "unclassified"
        is_primary = item["_id"]["is_primary"]
        count = item["count"]
        primary_label = "PRIMARY" if is_primary else "context"
        print(f"  {type_name:15} ({primary_label:8}): {count:4} mentions")
    
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
