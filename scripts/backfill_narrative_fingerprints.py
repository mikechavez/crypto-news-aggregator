"""
Backfill narrative fingerprints for existing narratives.

This script:
1. Queries all narratives from the database
2. For each narrative without a fingerprint field:
   - Computes fingerprint using compute_narrative_fingerprint
   - Uses entities list as top_actors
   - Uses theme as nucleus_entity (if no nucleus_entity exists)
   - Uses empty actions list
3. Updates each narrative document with the computed fingerprint
4. Logs progress every 10 narratives
5. Provides final summary of total processed
"""

import asyncio
import sys
import logging
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))

from crypto_news_aggregator.db.mongodb import mongo_manager
from crypto_news_aggregator.services.narrative_themes import compute_narrative_fingerprint

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def backfill_narrative_fingerprints():
    """
    Backfill fingerprints for all narratives that don't have one.
    
    Returns:
        Tuple of (total_processed, total_updated, total_skipped)
    """
    logger.info("=" * 80)
    logger.info("NARRATIVE FINGERPRINT BACKFILL")
    logger.info("=" * 80)
    
    await mongo_manager.initialize()
    
    try:
        db = await mongo_manager.get_async_database()
        narratives_collection = db.narratives
        
        # Count total narratives
        total_narratives = await narratives_collection.count_documents({})
        logger.info(f"📊 Total narratives in database: {total_narratives}")
        
        if total_narratives == 0:
            logger.info("✅ No narratives found - nothing to backfill")
            return 0, 0, 0
        
        # Query all narratives
        cursor = narratives_collection.find({})
        narratives = await cursor.to_list(length=None)
        
        total_processed = 0
        total_updated = 0
        total_skipped = 0
        
        logger.info(f"🔍 Processing {len(narratives)} narratives...")
        logger.info("")
        
        for narrative in narratives:
            total_processed += 1
            narrative_id = narrative.get('_id')
            title = narrative.get('title', 'Unknown')
            
            # Check if narrative already has a fingerprint
            if 'fingerprint' in narrative and narrative['fingerprint']:
                total_skipped += 1
                logger.debug(f"⏭️  Skipping narrative '{title}' - already has fingerprint")
                continue
            
            # Extract data for fingerprint computation
            # Use entities list as top_actors
            entities = narrative.get('entities', [])
            
            # Use theme as nucleus_entity if no nucleus_entity exists
            nucleus_entity = narrative.get('nucleus_entity') or narrative.get('theme', '')
            
            # Build cluster dict for compute_narrative_fingerprint
            # Convert entities list to actors dict with default salience
            actors_dict = {entity: 3 for entity in entities}  # Default salience of 3
            
            cluster_data = {
                'nucleus_entity': nucleus_entity,
                'actors': actors_dict,
                'actions': []  # Empty actions list
            }
            
            # Compute fingerprint
            try:
                fingerprint = compute_narrative_fingerprint(cluster_data)
                
                # Update narrative with fingerprint
                await narratives_collection.update_one(
                    {'_id': narrative_id},
                    {'$set': {'fingerprint': fingerprint}}
                )
                
                total_updated += 1
                
                # Log progress every 10 narratives
                if total_updated % 10 == 0:
                    logger.info(
                        f"✅ Progress: {total_updated} narratives updated "
                        f"({total_processed}/{len(narratives)} processed)"
                    )
                
                logger.debug(
                    f"✅ Updated narrative '{title}' with fingerprint: "
                    f"nucleus={fingerprint.get('nucleus_entity')}, "
                    f"actors={len(fingerprint.get('top_actors', []))}"
                )
                
            except Exception as e:
                logger.error(f"❌ Failed to process narrative '{title}': {e}")
                continue
        
        # Final summary
        logger.info("")
        logger.info("=" * 80)
        logger.info("BACKFILL COMPLETE")
        logger.info("=" * 80)
        logger.info(f"📊 Total narratives processed: {total_processed}")
        logger.info(f"✅ Narratives updated with fingerprints: {total_updated}")
        logger.info(f"⏭️  Narratives skipped (already had fingerprint): {total_skipped}")
        logger.info("=" * 80)
        
        return total_processed, total_updated, total_skipped
        
    except Exception as e:
        logger.exception(f"❌ Error during backfill: {e}")
        raise
    finally:
        await mongo_manager.close()


async def main():
    """Main entry point."""
    try:
        total_processed, total_updated, total_skipped = await backfill_narrative_fingerprints()
        
        # Exit with appropriate code
        if total_updated > 0:
            logger.info("✅ Backfill successful!")
            sys.exit(0)
        elif total_skipped > 0:
            logger.info("✅ All narratives already have fingerprints!")
            sys.exit(0)
        else:
            logger.info("ℹ️  No narratives to process")
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"❌ Backfill failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
