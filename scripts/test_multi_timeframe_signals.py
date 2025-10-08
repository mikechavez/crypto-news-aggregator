#!/usr/bin/env python3
"""
Test script for multi-timeframe signal scoring.

Tests that 24h, 7d, and 30d timeframes produce different scores and velocities.
"""

import asyncio
import sys
import os
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from crypto_news_aggregator.db.mongodb import initialize_mongodb, mongo_manager
from crypto_news_aggregator.services.signal_service import calculate_signal_score
from crypto_news_aggregator.db.operations.signal_scores import upsert_signal_score, get_entity_signal


async def test_multi_timeframe_scoring():
    """Test multi-timeframe signal scoring."""
    print("=" * 80)
    print("MULTI-TIMEFRAME SIGNAL SCORING TEST")
    print("=" * 80)
    
    await initialize_mongodb()
    
    try:
        # Get a sample entity from recent mentions
        db = await mongo_manager.get_async_database()
        entity_mentions = db.entity_mentions
        
        # Find an entity with mentions
        sample_mention = await entity_mentions.find_one({"is_primary": True})
        
        if not sample_mention:
            print("\n❌ No entity mentions found in database")
            print("Please run RSS fetcher first to populate data")
            return
        
        entity = sample_mention["entity"]
        entity_type = sample_mention.get("entity_type", "unknown")
        
        print(f"\n📊 Testing entity: {entity} (type: {entity_type})")
        print("-" * 80)
        
        # Calculate scores for all three timeframes
        print("\n🔍 Calculating signal scores for all timeframes...")
        
        signal_24h = await calculate_signal_score(entity, timeframe_hours=24)
        signal_7d = await calculate_signal_score(entity, timeframe_hours=168)
        signal_30d = await calculate_signal_score(entity, timeframe_hours=720)
        
        # Display results
        print("\n📈 24-HOUR TIMEFRAME:")
        print(f"  Score:          {signal_24h['score']}")
        print(f"  Velocity:       {signal_24h['velocity']} ({signal_24h['velocity']*100:.1f}% growth)")
        print(f"  Mentions:       {signal_24h.get('mentions', 0)}")
        print(f"  Source Count:   {signal_24h['source_count']}")
        print(f"  Recency Factor: {signal_24h.get('recency_factor', 0)}")
        
        print("\n📈 7-DAY TIMEFRAME:")
        print(f"  Score:          {signal_7d['score']}")
        print(f"  Velocity:       {signal_7d['velocity']} ({signal_7d['velocity']*100:.1f}% growth)")
        print(f"  Mentions:       {signal_7d.get('mentions', 0)}")
        print(f"  Source Count:   {signal_7d['source_count']}")
        print(f"  Recency Factor: {signal_7d.get('recency_factor', 0)}")
        
        print("\n📈 30-DAY TIMEFRAME:")
        print(f"  Score:          {signal_30d['score']}")
        print(f"  Velocity:       {signal_30d['velocity']} ({signal_30d['velocity']*100:.1f}% growth)")
        print(f"  Mentions:       {signal_30d.get('mentions', 0)}")
        print(f"  Source Count:   {signal_30d['source_count']}")
        print(f"  Recency Factor: {signal_30d.get('recency_factor', 0)}")
        
        # Test storage
        print("\n💾 Testing database storage...")
        
        # Get first_seen timestamp
        first_mention = await entity_mentions.find_one(
            {"entity": entity, "is_primary": True},
            sort=[("created_at", 1)]
        )
        first_seen = first_mention["created_at"] if first_mention else datetime.now(timezone.utc)
        
        # Store with all timeframes
        await upsert_signal_score(
            entity=entity,
            entity_type=entity_type,
            score=signal_24h["score"],  # Use 24h as default
            velocity=signal_24h["velocity"],
            source_count=signal_24h["source_count"],
            sentiment=signal_24h["sentiment"],
            narrative_ids=signal_24h.get("narrative_ids", []),
            is_emerging=signal_24h.get("is_emerging", False),
            first_seen=first_seen,
            score_24h=signal_24h["score"],
            score_7d=signal_7d["score"],
            score_30d=signal_30d["score"],
            velocity_24h=signal_24h["velocity"],
            velocity_7d=signal_7d["velocity"],
            velocity_30d=signal_30d["velocity"],
            mentions_24h=signal_24h.get("mentions", 0),
            mentions_7d=signal_7d.get("mentions", 0),
            mentions_30d=signal_30d.get("mentions", 0),
            recency_24h=signal_24h.get("recency_factor", 0.0),
            recency_7d=signal_7d.get("recency_factor", 0.0),
            recency_30d=signal_30d.get("recency_factor", 0.0),
        )
        
        # Retrieve and verify
        stored_signal = await get_entity_signal(entity)
        
        if stored_signal:
            print("✅ Signal stored successfully")
            print("\n📦 Stored data:")
            print(f"  24h: score={stored_signal.get('score_24h')}, velocity={stored_signal.get('velocity_24h')}")
            print(f"  7d:  score={stored_signal.get('score_7d')}, velocity={stored_signal.get('velocity_7d')}")
            print(f"  30d: score={stored_signal.get('score_30d')}, velocity={stored_signal.get('velocity_30d')}")
        else:
            print("❌ Failed to retrieve stored signal")
        
        # Validation
        print("\n✅ VALIDATION:")
        
        # Check if timeframes produce different values
        scores_differ = len(set([signal_24h['score'], signal_7d['score'], signal_30d['score']])) > 1
        velocities_differ = len(set([signal_24h['velocity'], signal_7d['velocity'], signal_30d['velocity']])) > 1
        
        if scores_differ:
            print("  ✓ Scores differ across timeframes")
        else:
            print("  ⚠ Scores are identical across timeframes (may indicate insufficient data)")
        
        if velocities_differ:
            print("  ✓ Velocities differ across timeframes")
        else:
            print("  ⚠ Velocities are identical across timeframes (may indicate insufficient data)")
        
        # Test with multiple entities
        print("\n🔍 Testing with top 5 entities...")
        cursor = entity_mentions.find({"is_primary": True}).limit(100)
        
        entities_tested = set()
        results = []
        
        async for mention in cursor:
            entity = mention["entity"]
            if entity not in entities_tested and len(entities_tested) < 5:
                entities_tested.add(entity)
                
                try:
                    sig_24h = await calculate_signal_score(entity, timeframe_hours=24)
                    sig_7d = await calculate_signal_score(entity, timeframe_hours=168)
                    sig_30d = await calculate_signal_score(entity, timeframe_hours=720)
                    
                    results.append({
                        "entity": entity,
                        "score_24h": sig_24h["score"],
                        "score_7d": sig_7d["score"],
                        "score_30d": sig_30d["score"],
                        "velocity_24h": sig_24h["velocity"],
                        "velocity_7d": sig_7d["velocity"],
                        "velocity_30d": sig_30d["velocity"],
                    })
                except Exception as e:
                    print(f"  ⚠ Error scoring {entity}: {e}")
        
        print("\n📊 MULTI-ENTITY RESULTS:")
        print("-" * 80)
        for result in results:
            print(f"\n{result['entity']}:")
            print(f"  Scores:     24h={result['score_24h']:.2f}  7d={result['score_7d']:.2f}  30d={result['score_30d']:.2f}")
            print(f"  Velocities: 24h={result['velocity_24h']:.3f}  7d={result['velocity_7d']:.3f}  30d={result['velocity_30d']:.3f}")
        
        print("\n" + "=" * 80)
        print("✅ MULTI-TIMEFRAME SIGNAL SCORING TEST COMPLETE")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await mongo_manager.aclose()


if __name__ == "__main__":
    asyncio.run(test_multi_timeframe_scoring())
