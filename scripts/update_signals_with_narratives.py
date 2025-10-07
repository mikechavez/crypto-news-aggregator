#!/usr/bin/env python3
"""
Update all signals with narrative linkage.

This script:
- Queries all signals from signal_scores collection
- For each signal, recalculates the signal score (which includes narrative_ids)
- Updates the signal with narrative_ids and is_emerging flag
- Logs progress

Usage:
    # Run locally
    poetry run python scripts/update_signals_with_narratives.py
    
    # Run on Railway
    railway run python scripts/update_signals_with_narratives.py
"""

import asyncio
import sys
import os
from datetime import datetime, timezone

# Add src to path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, os.path.join(project_root, "src"))

from crypto_news_aggregator.db.mongodb import mongo_manager
from crypto_news_aggregator.services.signal_service import calculate_signal_score


async def update_all_signals():
    """Update all signals with narrative linkage."""
    print("=" * 80)
    print("SIGNAL NARRATIVE LINKAGE UPDATE")
    print("=" * 80)
    print(f"Started at: {datetime.now(timezone.utc).isoformat()}")
    print()
    
    # Connect to database
    db = await mongo_manager.get_async_database()
    signal_collection = db.signal_scores
    
    # Get all signals
    signals = await signal_collection.find().to_list(length=None)
    total_signals = len(signals)
    
    print(f"Found {total_signals} signals to update")
    print()
    
    # Track stats
    updated_count = 0
    with_narratives = 0
    emerging_count = 0
    failed_count = 0
    
    # Process each signal
    for idx, signal in enumerate(signals, 1):
        entity = signal.get("entity")
        if not entity:
            print(f"[{idx}/{total_signals}] ⚠️  Signal missing entity field, skipping")
            failed_count += 1
            continue
        
        try:
            # Recalculate signal score (includes narrative linkage)
            updated_signal = await calculate_signal_score(entity)
            
            # Update the signal in database
            await signal_collection.update_one(
                {"_id": signal["_id"]},
                {
                    "$set": {
                        "narrative_ids": updated_signal["narrative_ids"],
                        "is_emerging": updated_signal["is_emerging"],
                        "updated_at": datetime.now(timezone.utc),
                    }
                }
            )
            
            # Track stats
            updated_count += 1
            if updated_signal["narrative_ids"]:
                with_narratives += 1
            if updated_signal["is_emerging"]:
                emerging_count += 1
            
            # Log progress
            narrative_count = len(updated_signal["narrative_ids"])
            status = "🆕 EMERGING" if updated_signal["is_emerging"] else f"📊 {narrative_count} narrative(s)"
            print(f"[{idx}/{total_signals}] ✅ {entity}: {status}")
            
        except Exception as e:
            print(f"[{idx}/{total_signals}] ❌ {entity}: Error - {str(e)}")
            failed_count += 1
    
    # Print summary
    print()
    print("=" * 80)
    print("UPDATE COMPLETE")
    print("=" * 80)
    print(f"Total signals: {total_signals}")
    print(f"Updated: {updated_count}")
    print(f"With narratives: {with_narratives}")
    print(f"Emerging (no narratives): {emerging_count}")
    print(f"Failed: {failed_count}")
    print()
    print(f"Finished at: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 80)


async def main():
    """Main entry point."""
    try:
        await update_all_signals()
    finally:
        # Clean up database connection
        await mongo_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
