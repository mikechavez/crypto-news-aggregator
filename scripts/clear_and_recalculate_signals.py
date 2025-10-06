"""
Clear all signal scores and force fresh recalculation from normalized entity mentions.
"""
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone

from crypto_news_aggregator.services.signal_service import calculate_signal_score
from crypto_news_aggregator.db.operations.signal_scores import upsert_signal_score

async def main():
    client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))
    db = client[os.getenv('MONGODB_DB_NAME')]
    
    print("Clearing and recalculating all signal scores...\n")
    print("="*80)
    
    # Step 1: Delete all existing signal scores
    print("\n[STEP 1] Deleting all existing signal scores...")
    old_count = await db.signal_scores.count_documents({})
    print(f"Found {old_count} existing signal scores")
    
    result = await db.signal_scores.delete_many({})
    deleted_count = result.deleted_count
    print(f"✓ Deleted {deleted_count} signal scores")
    
    # Step 2: Get all unique primary entities from entity_mentions
    print("\n[STEP 2] Getting unique entities from entity_mentions...")
    unique_entities = await db.entity_mentions.distinct(
        "entity",
        {"is_primary": True}
    )
    print(f"Found {len(unique_entities)} unique entities to score")
    
    # Step 3: Recalculate signal scores for each entity
    print("\n[STEP 3] Recalculating signal scores...")
    created_count = 0
    errors = 0
    
    for entity in unique_entities:
        try:
            # Calculate signal score
            signal_data = await calculate_signal_score(entity)
            
            # Get first_seen timestamp
            first_mention = await db.entity_mentions.find_one(
                {"entity": entity, "is_primary": True},
                sort=[("created_at", 1)]
            )
            first_seen = first_mention["created_at"] if first_mention else datetime.now(timezone.utc)
            
            # Get entity type from first mention
            entity_type = first_mention.get("entity_type", "cryptocurrency") if first_mention else "cryptocurrency"
            
            # Store the signal score
            await upsert_signal_score(
                entity=entity,
                entity_type=entity_type,
                score=signal_data["score"],
                velocity=signal_data["velocity"],
                source_count=signal_data["source_count"],
                sentiment=signal_data["sentiment"],
                first_seen=first_seen,
            )
            
            created_count += 1
            
            if created_count % 10 == 0:
                print(f"  Progress: {created_count}/{len(unique_entities)} entities scored")
        
        except Exception as e:
            print(f"  Error calculating signal for '{entity}': {e}")
            errors += 1
    
    # Step 4: Verify new count
    print("\n[STEP 4] Verifying new signal scores...")
    new_count = await db.signal_scores.count_documents({})
    print(f"Signal scores in database: {new_count}")
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY:")
    print(f"  Deleted {deleted_count} old signals")
    print(f"  Created {created_count} new signals")
    print(f"  Errors: {errors}")
    print(f"  Final count in database: {new_count}")
    
    if created_count == new_count:
        print("\n✅ Signal recalculation completed successfully!")
    else:
        print(f"\n⚠️  Mismatch: Created {created_count} but database has {new_count}")
    
    print("\nDeleted {} old signals, created {} new signals".format(deleted_count, created_count))
    print("="*80)
    
    client.close()

asyncio.run(main())
