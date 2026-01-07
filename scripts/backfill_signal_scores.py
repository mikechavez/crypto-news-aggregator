#!/usr/bin/env python3
"""Backfill signal scores for all entities with recent mentions."""
import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient
from crypto_news_aggregator.core.config import settings
from crypto_news_aggregator.services.signal_service import calculate_signal_score
from crypto_news_aggregator.services.entity_normalization import normalize_entity_name
from crypto_news_aggregator.db.operations.signal_scores import upsert_signal_score

async def main():
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_NAME]
    
    print("=" * 80)
    print("SIGNAL SCORES BACKFILL")
    print("=" * 80)
    print()
    
    # Get all unique entities from last 7 days
    week_ago = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7)
    
    print(f"Finding entities with mentions in last 7 days...")
    
    cursor = db.entity_mentions.find({
        "created_at": {"$gte": week_ago},
        "is_primary": True
    })
    
    # Normalize and deduplicate
    entity_map = {}
    async for mention in cursor:
        raw_entity = mention.get("entity")
        entity_type = mention.get("entity_type")
        canonical = normalize_entity_name(raw_entity)
        if canonical not in entity_map:
            entity_map[canonical] = entity_type
    
    entities = list(entity_map.items())
    print(f"Found {len(entities)} unique entities to score")
    print()
    
    # Calculate scores
    scored = 0
    for i, (entity, entity_type) in enumerate(entities, 1):
        try:
            print(f"[{i}/{len(entities)}] Scoring {entity}...", end=" ")
            
            # Calculate all timeframes
            signal_24h = await calculate_signal_score(entity, timeframe_hours=24)
            signal_7d = await calculate_signal_score(entity, timeframe_hours=168)
            signal_30d = await calculate_signal_score(entity, timeframe_hours=720)
            signal_legacy = await calculate_signal_score(entity)
            
            # Get first_seen
            first_mention = await db.entity_mentions.find_one(
                {"entity": entity, "is_primary": True},
                sort=[("created_at", 1)]
            )
            first_seen = first_mention["created_at"] if first_mention else datetime.now(timezone.utc)
            
            # Store
            await upsert_signal_score(
                entity=entity,
                entity_type=entity_type,
                score=signal_legacy["score"],
                velocity=signal_legacy["velocity"],
                source_count=signal_legacy["source_count"],
                sentiment=signal_legacy["sentiment"],
                narrative_ids=signal_legacy.get("narrative_ids", []),
                is_emerging=signal_legacy.get("is_emerging", False),
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
            
            scored += 1
            print(f"✅ Score: {signal_legacy['score']:.1f}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print()
    print("=" * 80)
    print(f"COMPLETE: Scored {scored}/{len(entities)} entities")
    print("=" * 80)
    
    client.close()

if __name__ == "__main__":
    asyncio.run(main())
