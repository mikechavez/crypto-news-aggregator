#!/usr/bin/env python3
"""
Diagnostic script to investigate velocity indicator issue.

This script:
1. Fetches current signal scores from the database
2. Shows actual velocity values being stored
3. Compares against UI thresholds
4. Shows entity scoring coverage
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from crypto_news_aggregator.db.mongodb import mongo_manager


async def diagnose_velocity_issue():
    """Diagnose why all velocities show as 'Surging'."""
    
    print("=" * 80)
    print("VELOCITY INDICATOR DIAGNOSTIC")
    print("=" * 80)
    print()
    
    # Connect to database
    await mongo_manager.initialize()
    db = await mongo_manager.get_async_database()
    
    # 1. Check UI thresholds
    print("📊 UI THRESHOLDS (from Signals.tsx):")
    print("-" * 80)
    print("  Surging:   velocity >= 50")
    print("  Rising:    velocity >= 20")
    print("  Growing:   velocity >= 5")
    print("  Active:    velocity >= 0")
    print("  Declining: velocity < 0")
    print()
    
    # 2. Check backend velocity calculation
    print("🔧 BACKEND CALCULATION (from signal_service.py):")
    print("-" * 80)
    print("  Velocity = (current_period - previous_period) / previous_period")
    print("  Example: 50 mentions now vs 30 before = (50-30)/30 = 0.67 (67% growth)")
    print("  Returns: DECIMAL (0.67), not percentage (67)")
    print()
    
    # 3. Get sample signal scores
    print("📈 SAMPLE SIGNAL SCORES (7d timeframe):")
    print("-" * 80)
    
    signal_scores = db.signal_scores
    cursor = signal_scores.find().sort("score_7d", -1).limit(10)
    
    signals = []
    async for signal in cursor:
        signals.append(signal)
    
    if not signals:
        print("  ⚠️  No signal scores found in database!")
        print()
    else:
        print(f"{'Entity':<20} {'Velocity_7d':<12} {'UI Label':<12} {'Score_7d':<10} {'Mentions_7d':<12}")
        print("-" * 80)
        
        for signal in signals:
            entity = signal.get("entity", "Unknown")
            velocity_7d = signal.get("velocity_7d", 0.0)
            score_7d = signal.get("score_7d", 0.0)
            mentions_7d = signal.get("mentions_7d", 0)
            
            # Determine UI label based on thresholds
            if velocity_7d >= 50:
                ui_label = "🔥 Surging"
            elif velocity_7d >= 20:
                ui_label = "↑ Rising"
            elif velocity_7d >= 5:
                ui_label = "→ Growing"
            elif velocity_7d >= 0:
                ui_label = "Active"
            else:
                ui_label = "↓ Declining"
            
            print(f"{entity:<20} {velocity_7d:<12.3f} {ui_label:<12} {score_7d:<10.2f} {mentions_7d:<12}")
        
        print()
    
    # 4. Check entity coverage
    print("🎯 ENTITY SCORING COVERAGE:")
    print("-" * 80)
    
    entity_mentions = db.entity_mentions
    signal_scores_coll = db.signal_scores
    
    total_entities = len(await entity_mentions.distinct("entity"))
    scored_entities = await signal_scores_coll.count_documents({})
    entities_with_7d = await signal_scores_coll.count_documents({"velocity_7d": {"$exists": True}})
    
    print(f"  Total unique entities in entity_mentions: {total_entities}")
    print(f"  Entities with signal_scores: {scored_entities}")
    print(f"  Entities with 7d velocity data: {entities_with_7d}")
    print()
    
    # 5. Show velocity distribution
    print("📊 VELOCITY DISTRIBUTION (7d):")
    print("-" * 80)
    
    velocity_ranges = [
        ("Surging (>=50)", 50, float('inf')),
        ("Rising (20-50)", 20, 50),
        ("Growing (5-20)", 5, 20),
        ("Active (0-5)", 0, 5),
        ("Declining (<0)", float('-inf'), 0),
    ]
    
    for label, min_val, max_val in velocity_ranges:
        if max_val == float('inf'):
            count = await signal_scores_coll.count_documents({"velocity_7d": {"$gte": min_val}})
        elif min_val == float('-inf'):
            count = await signal_scores_coll.count_documents({"velocity_7d": {"$lt": max_val}})
        else:
            count = await signal_scores_coll.count_documents({
                "velocity_7d": {"$gte": min_val, "$lt": max_val}
            })
        print(f"  {label:<20}: {count:>5} entities")
    
    print()
    
    # 6. Root cause analysis
    print("🔍 ROOT CAUSE ANALYSIS:")
    print("-" * 80)
    print("  ISSUE: Backend returns velocity as DECIMAL (0.67 = 67% growth)")
    print("         UI expects velocity as PERCENTAGE (67 = 67% growth)")
    print()
    print("  RESULT: All velocities < 50 (most are 0.0 to 3.0) show as 'Active'")
    print("          Only velocities >= 50 (extremely rare) show as 'Surging'")
    print()
    print("  SOLUTION OPTIONS:")
    print("    1. Backend: Multiply velocity by 100 before storing (0.67 -> 67)")
    print("    2. UI: Divide thresholds by 100 (50 -> 0.5, 20 -> 0.2, etc.)")
    print("    3. API: Transform velocity * 100 when returning to frontend")
    print()
    
    # Cleanup (manager handles its own lifecycle)
    print("✅ Diagnostic complete!")


if __name__ == "__main__":
    asyncio.run(diagnose_velocity_issue())
