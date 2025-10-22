#!/usr/bin/env python3
"""
Test script to measure /api/v1/signals endpoint performance.
Tests both cache miss and cache hit scenarios.
"""

import asyncio
import time
import httpx

API_URL = "http://localhost:8000/api/v1/signals"

async def test_endpoint():
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("Testing /api/v1/signals endpoint performance\n")
        print("=" * 60)
        
        # Test 1: Cache MISS (first request)
        print("\n🔍 Test 1: Cache MISS (first request)")
        start = time.time()
        response = await client.get(API_URL)
        cache_miss_time = (time.time() - start) * 1000
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status: {response.status_code}")
            print(f"⏱️  Time: {cache_miss_time:.2f}ms")
            print(f"📊 Signals count: {data.get('count', 0)}")
            print(f"🕐 Cached at: {data.get('cached_at', 'N/A')}")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            return
        
        # Wait a moment
        await asyncio.sleep(0.5)
        
        # Test 2: Cache HIT (immediate second request)
        print("\n🔍 Test 2: Cache HIT (immediate second request)")
        start = time.time()
        response = await client.get(API_URL)
        cache_hit_time = (time.time() - start) * 1000
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status: {response.status_code}")
            print(f"⏱️  Time: {cache_hit_time:.2f}ms")
            print(f"📊 Signals count: {data.get('count', 0)}")
            print(f"🕐 Cached at: {data.get('cached_at', 'N/A')}")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            return
        
        # Test 3: Another cache hit
        print("\n🔍 Test 3: Cache HIT (third request)")
        start = time.time()
        response = await client.get(API_URL)
        cache_hit_time_2 = (time.time() - start) * 1000
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status: {response.status_code}")
            print(f"⏱️  Time: {cache_hit_time_2:.2f}ms")
            print(f"📊 Signals count: {data.get('count', 0)}")
            print(f"🕐 Cached at: {data.get('cached_at', 'N/A')}")
        
        # Summary
        print("\n" + "=" * 60)
        print("📈 PERFORMANCE SUMMARY")
        print("=" * 60)
        print(f"Cache MISS time:  {cache_miss_time:.2f}ms")
        print(f"Cache HIT time 1: {cache_hit_time:.2f}ms")
        print(f"Cache HIT time 2: {cache_hit_time_2:.2f}ms")
        print(f"Avg cache HIT:    {(cache_hit_time + cache_hit_time_2) / 2:.2f}ms")
        print(f"Speedup:          {cache_miss_time / cache_hit_time:.1f}x faster")
        print("\n✅ Expected cache MISS: ~500-800ms")
        print("✅ Expected cache HIT:  ~50-100ms")

if __name__ == "__main__":
    asyncio.run(test_endpoint())
