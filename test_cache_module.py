"""Test the cache module"""
import asyncio
import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from src.crypto_news_aggregator.llm.cache import LLMResponseCache, CostTracker

# Load environment variables
load_dotenv()


async def test_cache_and_cost_tracking():
    """Test cache and cost tracking functionality"""
    print("🧪 Testing Cache and Cost Tracking Modules\n")
    
    # Connect to MongoDB
    mongodb_uri = os.getenv("MONGODB_URI")
    if not mongodb_uri:
        print("❌ Error: MONGODB_URI environment variable not set")
        return
    
    client = AsyncIOMotorClient(mongodb_uri)
    db = client["crypto_news"]
    
    print("✅ Connected to MongoDB\n")
    
    # Test 1: LLM Cache
    print("1️⃣ Testing LLMResponseCache...")
    cache = LLMResponseCache(db, ttl_hours=1)
    await cache.initialize_indexes()
    
    # Set a test response
    test_prompt = "Extract entities from: Bitcoin surges to new high"
    test_model = "claude-3-5-haiku-20241022"
    test_response = {"entities": ["Bitcoin"]}
    
    await cache.set(test_prompt, test_model, test_response)
    print("   ✓ Cache set successful")
    
    # Get the response back
    retrieved = await cache.get(test_prompt, test_model)
    assert retrieved == test_response, "Cache get/set mismatch!"
    print("   ✓ Cache get successful")
    
    # Test cache miss
    miss = await cache.get("different prompt", test_model)
    assert miss is None, "Should be cache miss!"
    print("   ✓ Cache miss working correctly")
    
    # Get stats
    stats = await cache.get_stats()
    print(f"   ✓ Cache stats: {stats['cache_hits']} hits, {stats['cache_misses']} misses, "
          f"{stats['hit_rate_percent']:.1f}% hit rate\n")
    
    # Test 2: Cost Tracker
    print("2️⃣ Testing CostTracker...")
    tracker = CostTracker(db)
    await tracker.initialize_indexes()
    
    # Log a test call
    cost = await tracker.log_call(
        model=test_model,
        input_tokens=1000,
        output_tokens=100,
        operation="test_entity_extraction",
        cached=False
    )
    print(f"   ✓ Cost logged: ${cost:.6f}")
    
    # Log a cached call (no cost)
    await tracker.log_call(
        model=test_model,
        input_tokens=0,
        output_tokens=0,
        operation="test_entity_extraction",
        cached=True
    )
    print("   ✓ Cached call logged (no cost)")
    
    # Get monthly summary
    summary = await tracker.get_monthly_summary()
    print(f"   ✓ Monthly summary:")
    print(f"      - Month to date: ${summary['month_to_date']:.4f}")
    print(f"      - Total calls: {summary['total_calls']}")
    print(f"      - Cached calls: {summary['cached_calls']}")
    print(f"      - Cache hit rate: {summary['cache_hit_rate_percent']:.1f}%\n")
    
    # Test 3: Verify collections exist
    print("3️⃣ Verifying MongoDB collections...")
    collections = await db.list_collection_names()
    assert "llm_cache" in collections, "llm_cache collection not found!"
    assert "api_costs" in collections, "api_costs collection not found!"
    print("   ✓ Both collections exist\n")
    
    # Test 4: Verify indexes
    print("4️⃣ Verifying indexes...")
    cache_indexes = await db.llm_cache.index_information()
    cost_indexes = await db.api_costs.index_information()
    
    print(f"   ✓ Cache indexes: {len(cache_indexes)} created")
    print(f"   ✓ Cost indexes: {len(cost_indexes)} created\n")
    
    client.close()
    print("✅ All tests passed!\n")
    
    print("📊 Summary:")
    print(f"   - Cache is working with {stats['hit_rate_percent']:.0f}% hit rate")
    print(f"   - Cost tracking is recording: ${summary['month_to_date']:.4f} so far")
    print(f"   - Ready for integration with LLM client!")


if __name__ == "__main__":
    asyncio.run(test_cache_and_cost_tracking())
