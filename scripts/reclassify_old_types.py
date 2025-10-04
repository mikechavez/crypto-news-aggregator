"""
Reclassify entities with old types (project/ticker/event) using Claude Haiku.
Focuses on the ~100 unique entities that still have old classification.
"""
import asyncio
import os
import json
from dotenv import load_dotenv
load_dotenv()
from motor.motor_asyncio import AsyncIOMotorClient
from anthropic import Anthropic

async def main():
    client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))
    db = client[os.getenv('MONGODB_DB_NAME')]
    
    # Get unique entities with old types
    pipeline = [
        {'$match': {'entity_type': {'$in': ['project', 'ticker', 'event']}}},
        {'$group': {'_id': '$entity', 'old_type': {'$first': '$entity_type'}}},
        {'$project': {'entity': '$_id', 'old_type': 1, '_id': 0}}
    ]
    
    old_entities = await db.entity_mentions.aggregate(pipeline).to_list(None)
    print(f'Found {len(old_entities)} unique entities to reclassify\n')
    
    anthropic_client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    
    # Process in batches of 50
    for i in range(0, len(old_entities), 50):
        batch = old_entities[i:i+50]
        entity_names = [e['entity'] for e in batch]
        
        prompt = f"""Classify these crypto-related entities. Return ONLY valid JSON.

Types (with examples):
- cryptocurrency: Bitcoin, Ethereum, $BTC, $ETH (coins/tokens)
- blockchain: Ethereum, Solana, Avalanche (platforms)
- protocol: Uniswap, 1Inch, Aave, Lido (DeFi protocols)
- company: Coinbase, Circle, Anthropic, SpaceX, Apollo, World Liberty Financial (businesses)
- concept: DeFi, Web3, Pilot Program, Ai (abstract ideas)
- location: New York, Abu Dhabi, Us (if it means USA)
- person: names of individuals
- event: launch, upgrade, rally (temporal occurrences)

Entities to classify: {json.dumps(entity_names)}

Return format:
{{
  "Bitcoin": {{"type": "cryptocurrency", "confidence": 0.95}},
  "Anthropic": {{"type": "company", "confidence": 0.92}},
  "Us": {{"type": "location", "confidence": 0.75}}
}}

Rules:
- Companies are businesses (Anthropic, SpaceX, Naver Financial)
- Protocols are DeFi/blockchain apps (Uniswap, 1Inch, Seedify)
- Tickers starting with $ are cryptocurrency
- Generic terms like "Ai", "Pilot Program" are concepts
- Only include entities from the input list"""

        try:
            response = anthropic_client.messages.create(
                model="claude-haiku-3-5-20241022",
                max_tokens=3000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse response
            text = response.content[0].text
            text = text.replace("```json\n", "").replace("```json", "").replace("\n```", "").replace("```", "").strip()
            classifications = json.loads(text)
            
            # Update database
            for entity_name, data in classifications.items():
                entity_type = data['type']
                is_primary = entity_type in ['cryptocurrency', 'blockchain', 'protocol', 'company']
                
                result = await db.entity_mentions.update_many(
                    {'entity': entity_name},
                    {'$set': {
                        'entity_type': entity_type,
                        'is_primary': is_primary,
                        'confidence': data.get('confidence', 0.85)
                    }}
                )
                
                primary_label = 'PRIMARY' if is_primary else 'context'
                print(f'  {entity_name:30} -> {entity_type:15} ({primary_label}) [{result.modified_count} docs]')
            
            print(f'\nBatch {i//50 + 1} complete\n')
            
        except Exception as e:
            print(f'Error in batch {i//50 + 1}: {e}')
            continue
    
    # Verify
    remaining = await db.entity_mentions.count_documents({'entity_type': {'$in': ['project', 'ticker', 'event']}})
    print(f'\n✅ Complete! Remaining old types: {remaining}')
    
    client.close()

asyncio.run(main())
