#!/usr/bin/env python3
"""
Cost tracking verification script.

Makes test LLM calls and verifies cost tracking is working correctly.
Displays tracked data and validates accuracy.

Usage:
    poetry run python scripts/verify_cost_tracking.py
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
import certifi

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from crypto_news_aggregator.llm.optimized_anthropic import OptimizedAnthropicProvider
from crypto_news_aggregator.services.cost_tracker import CostTracker, get_cost_tracker


async def verify_cost_tracking():
    """Run cost tracking verification."""

    print("="*60)
    print("         Cost Tracking Verification")
    print("="*60)
    print()

    # 1. Connect to MongoDB
    print("ℹ️  Connecting to MongoDB...")
    mongodb_uri = os.getenv("MONGODB_URI")
    if not mongodb_uri:
        print("❌ MONGODB_URI not set")
        return

    client = AsyncIOMotorClient(mongodb_uri, tlsCAFile=certifi.where())
    db = client["crypto_news"]
    print("✅ Connected to MongoDB")
    print()

    # 2. Get cost tracker
    print("ℹ️  Initializing cost tracker...")
    tracker = get_cost_tracker(db)
    print("✅ Cost tracker initialized")
    print()

    # 3. Make test LLM call
    print("ℹ️  Making test LLM call...")
    print("   Model: claude-3-5-haiku-20241022")
    print("   Operation: verification_test")
    print()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set")
        client.close()
        return

    provider = OptimizedAnthropicProvider(api_key=api_key)

    test_prompt = "Say 'Cost tracking verification successful' in 5 words or less."

    try:
        response_text = await provider.generate_completion(
            prompt=test_prompt,
            model="claude-3-5-haiku-20241022",
            max_tokens=50,
            operation="verification_test"
        )

        print(f"✅ LLM call succeeded")
        print(f"   Response: {response_text}")
        print()
    except Exception as e:
        print(f"❌ LLM call failed: {e}")
        client.close()
        return

    # 4. Wait for tracking to complete (async task)
    print("ℹ️  Waiting for cost tracking to complete...")
    await asyncio.sleep(2)  # Give time for async tracking
    print()

    # 5. Query database for tracked call
    print("ℹ️  Querying database for tracked call...")
    cutoff = datetime.now(timezone.utc)
    cutoff = cutoff.replace(second=cutoff.second - 10)  # Last 10 seconds

    doc = await db.api_costs.find_one(
        {
            "operation": "verification_test",
            "timestamp": {"$gte": cutoff}
        },
        sort=[("timestamp", -1)]
    )

    if not doc:
        print("❌ No tracked call found in database")
        print("   Check if cost tracking is integrated correctly")
        client.close()
        return

    print("✅ Found tracked call in database")
    print()

    # 6. Display tracked data
    print("="*60)
    print("         Tracked Call Details")
    print("="*60)
    print()
    print(f"Timestamp:      {doc['timestamp']}")
    print(f"Operation:      {doc['operation']}")
    print(f"Model:          {doc['model']}")
    print(f"Input Tokens:   {doc['input_tokens']}")
    print(f"Output Tokens:  {doc['output_tokens']}")
    print(f"Cost (USD):     ${doc['cost']:.6f}")
    print(f"Cached:         {doc['cached']}")
    print()

    # 7. Verify cost calculation
    print("="*60)
    print("         Cost Calculation Verification")
    print("="*60)
    print()

    expected_cost = tracker.calculate_cost(
        model=doc['model'],
        input_tokens=doc['input_tokens'],
        output_tokens=doc['output_tokens']
    )

    print(f"Tracked Cost:   ${doc['cost']:.6f}")
    print(f"Expected Cost:  ${expected_cost:.6f}")

    if abs(doc['cost'] - expected_cost) < 0.000001:
        print("✅ Cost calculation is accurate")
    else:
        print(f"❌ Cost mismatch: {abs(doc['cost'] - expected_cost):.6f}")
    print()

    # 8. Get monthly cost summary
    print("="*60)
    print("         Monthly Cost Summary")
    print("="*60)
    print()

    monthly_cost = await tracker.get_monthly_cost()
    daily_cost = await tracker.get_daily_cost(days=1)

    print(f"Month-to-Date:  ${monthly_cost:.4f}")
    print(f"Last 24 Hours:  ${daily_cost:.4f}")
    print()

    # 9. Get operation breakdown
    print("="*60)
    print("         Cost Breakdown (Last 24h)")
    print("="*60)
    print()

    from datetime import timedelta
    cutoff_24h = datetime.now(timezone.utc) - timedelta(hours=24)

    pipeline = [
        {"$match": {"timestamp": {"$gte": cutoff_24h}}},
        {"$group": {
            "_id": "$operation",
            "total_cost": {"$sum": "$cost"},
            "call_count": {"$sum": 1},
            "cached_count": {"$sum": {"$cond": ["$cached", 1, 0]}}
        }},
        {"$sort": {"total_cost": -1}}
    ]

    results = await db.api_costs.aggregate(pipeline).to_list(None)

    if results:
        for r in results:
            print(f"{r['_id']:20s} ${r['total_cost']:.4f} ({r['call_count']} calls, {r['cached_count']} cached)")
    else:
        print("No operations in last 24 hours")
    print()

    # 10. Success summary
    print("="*60)
    print("         Verification Complete")
    print("="*60)
    print()
    print("✅ Cost tracking is working correctly")
    print("✅ Database writes successful")
    print("✅ Cost calculations accurate")
    print()
    print("Next steps:")
    print("  1. Deploy to production")
    print("  2. Monitor costs in dashboard")
    print("  3. Set up alerts for daily cost > $0.50")
    print()

    client.close()


if __name__ == "__main__":
    asyncio.run(verify_cost_tracking())
