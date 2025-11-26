#!/usr/bin/env python3
"""
Test script for Admin Cost Monitoring API Endpoints

Usage:
    python scripts/test_admin_endpoints.py [--base-url URL] [--api-key KEY]

Example:
    python scripts/test_admin_endpoints.py --base-url http://localhost:8000 --api-key your-api-key
"""

import argparse
import os
import sys

import requests


def test_endpoints(base_url: str, api_key: str):
    """Test all admin endpoints"""
    headers = {"X-API-Key": api_key}
    admin_url = f"{base_url}/admin"
    
    print("🧪 Testing Admin Cost Monitoring Endpoints\n")
    print(f"   Base URL: {base_url}")
    print(f"   API Key: {api_key[:4]}...{api_key[-4:] if len(api_key) > 8 else '***'}\n")
    
    all_passed = True
    
    # Test 1: Health check (no auth required)
    print("0️⃣  Testing /admin/health (no auth)...")
    try:
        response = requests.get(f"{admin_url}/health", timeout=10)
        if response.status_code == 200:
            print(f"   ✓ Status: {response.json()['status']}\n")
        else:
            print(f"   ✗ Failed with status {response.status_code}\n")
            all_passed = False
    except Exception as e:
        print(f"   ✗ Error: {e}\n")
        all_passed = False
    
    # Test 1: Cost summary
    print("1️⃣  Testing /admin/api-costs/summary...")
    try:
        response = requests.get(f"{admin_url}/api-costs/summary", headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ Month to date: ${data['month_to_date']}")
            print(f"   ✓ Projected: ${data['projected_monthly']}")
            print(f"   ✓ Days elapsed: {data['days_elapsed']}")
            print(f"   ✓ Total calls: {data['total_calls']}")
            print(f"   ✓ Cache hit rate: {data['cache_hit_rate_percent']}%")
            print(f"   ✓ Operations tracked: {len(data['breakdown_by_operation'])}\n")
        else:
            print(f"   ✗ Failed with status {response.status_code}: {response.text}\n")
            all_passed = False
    except Exception as e:
        print(f"   ✗ Error: {e}\n")
        all_passed = False
    
    # Test 2: Daily costs
    print("2️⃣  Testing /admin/api-costs/daily?days=7...")
    try:
        response = requests.get(f"{admin_url}/api-costs/daily?days=7", headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ Days requested: {data['days_requested']}")
            print(f"   ✓ Days returned: {len(data['daily_costs'])}")
            print(f"   ✓ Total cost: ${data['total_cost']}\n")
        else:
            print(f"   ✗ Failed with status {response.status_code}: {response.text}\n")
            all_passed = False
    except Exception as e:
        print(f"   ✗ Error: {e}\n")
        all_passed = False
    
    # Test 3: Costs by model
    print("3️⃣  Testing /admin/api-costs/by-model...")
    try:
        response = requests.get(f"{admin_url}/api-costs/by-model", headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ Period: {data['period_days']} days")
            print(f"   ✓ Models tracked: {len(data['models'])}")
            if data['models']:
                top = data['models'][0]
                print(f"   ✓ Top model: {top['model']}")
                print(f"   ✓ Top model cost: ${top['total_cost']}")
                print(f"   ✓ Top model calls: {top['total_calls']}")
            print(f"   ✓ Total cost: ${data['total_cost']}\n")
        else:
            print(f"   ✗ Failed with status {response.status_code}: {response.text}\n")
            all_passed = False
    except Exception as e:
        print(f"   ✗ Error: {e}\n")
        all_passed = False
    
    # Test 4: Cache stats
    print("4️⃣  Testing /admin/cache/stats...")
    try:
        response = requests.get(f"{admin_url}/cache/stats", headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            entries = data['cache_entries']
            perf = data['performance']
            print(f"   ✓ Total cache entries: {entries['total']}")
            print(f"   ✓ Active entries: {entries['active']}")
            print(f"   ✓ Expired entries: {entries['expired']}")
            print(f"   ✓ Cache hits: {perf['cache_hits']}")
            print(f"   ✓ Cache misses: {perf['cache_misses']}")
            print(f"   ✓ Hit rate: {perf['hit_rate_percent']}%\n")
        else:
            print(f"   ✗ Failed with status {response.status_code}: {response.text}\n")
            all_passed = False
    except Exception as e:
        print(f"   ✗ Error: {e}\n")
        all_passed = False
    
    # Test 5: Clear expired cache
    print("5️⃣  Testing /admin/cache/clear-expired...")
    try:
        response = requests.post(f"{admin_url}/cache/clear-expired", headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ Deleted: {data['deleted_count']} entries")
            print(f"   ✓ Message: {data['message']}\n")
        else:
            print(f"   ✗ Failed with status {response.status_code}: {response.text}\n")
            all_passed = False
    except Exception as e:
        print(f"   ✗ Error: {e}\n")
        all_passed = False
    
    # Test 6: Processing stats
    print("6️⃣  Testing /admin/processing/stats...")
    try:
        response = requests.get(f"{admin_url}/processing/stats", headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            summary = data['summary']
            print(f"   ✓ Period: {data['period_days']} days")
            print(f"   ✓ Sources tracked: {len(data['sources'])}")
            print(f"   ✓ Total articles: {summary['total_articles']}")
            print(f"   ✓ LLM extractions: {summary['total_llm_extractions']}")
            print(f"   ✓ Simple extractions: {summary['total_simple_extractions']}\n")
        else:
            print(f"   ✗ Failed with status {response.status_code}: {response.text}\n")
            all_passed = False
    except Exception as e:
        print(f"   ✗ Error: {e}\n")
        all_passed = False
    
    # Summary
    if all_passed:
        print("✅ All endpoints working!\n")
    else:
        print("❌ Some endpoints failed. Check the output above.\n")
    
    # Print cost optimization summary
    print("📊 Cost Optimization Summary:")
    try:
        cost_response = requests.get(f"{admin_url}/api-costs/summary", headers=headers, timeout=10)
        if cost_response.status_code == 200:
            cost_data = cost_response.json()
            print(f"   Current month: ${cost_data['month_to_date']:.2f}")
            print(f"   Projected end of month: ${cost_data['projected_monthly']:.2f}")
            print(f"   Cache efficiency: {cost_data['cache_hit_rate_percent']:.1f}%")
            
            if cost_data['projected_monthly'] < 10:
                print("   🎉 TARGET MET! Under $10/month!")
            elif cost_data['projected_monthly'] < 15:
                print("   ✅ Great progress! Close to target.")
            elif cost_data['total_calls'] == 0:
                print("   ℹ️  No API calls recorded yet. Run some LLM operations first.")
            else:
                print("   ⚠️  Still optimizing... give cache time to warm up (3-7 days)")
    except Exception as e:
        print(f"   Could not fetch summary: {e}")
    
    return all_passed


def main():
    parser = argparse.ArgumentParser(description="Test Admin Cost Monitoring API Endpoints")
    parser.add_argument(
        "--base-url",
        default=os.getenv("API_BASE_URL", "http://localhost:8000"),
        help="Base URL of the API server (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("API_KEY", ""),
        help="API key for authentication"
    )
    
    args = parser.parse_args()
    
    if not args.api_key:
        print("❌ Error: API key is required.")
        print("   Set via --api-key argument or API_KEY environment variable.")
        sys.exit(1)
    
    success = test_endpoints(args.base_url, args.api_key)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
