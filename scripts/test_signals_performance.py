#!/usr/bin/env python3
"""
Test script to verify Signals endpoint performance optimization.

This script tests the /api/v1/signals/trending endpoint and reports:
- Response time
- Number of signals returned
- Payload size
- Performance metrics from the response

Usage:
    python scripts/test_signals_performance.py
    python scripts/test_signals_performance.py --base-url http://localhost:8000
    python scripts/test_signals_performance.py --timeframe 24h
"""

import argparse
import json
import sys
import time
from typing import Dict, Any

try:
    import requests
except ImportError:
    print("Error: requests library not installed")
    print("Install with: pip install requests")
    sys.exit(1)


def test_signals_endpoint(
    base_url: str = "http://localhost:8000",
    timeframe: str = "7d",
    limit: int = 50
) -> Dict[str, Any]:
    """
    Test the signals endpoint and return performance metrics.
    
    Args:
        base_url: Base URL of the API
        timeframe: Timeframe for signals (24h, 7d, 30d)
        limit: Maximum number of signals to return
    
    Returns:
        Dict with performance metrics
    """
    url = f"{base_url}/api/v1/signals/trending"
    params = {
        "limit": limit,
        "timeframe": timeframe,
    }
    
    print(f"\n{'='*60}")
    print(f"Testing Signals Endpoint Performance")
    print(f"{'='*60}")
    print(f"URL: {url}")
    print(f"Parameters: {params}")
    print(f"{'='*60}\n")
    
    # Measure request time
    start_time = time.time()
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return {"error": str(e)}
    
    end_time = time.time()
    request_duration = end_time - start_time
    
    # Parse response
    try:
        data = response.json()
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse JSON response: {e}")
        return {"error": "Invalid JSON response"}
    
    # Calculate payload size
    payload_size_bytes = len(response.content)
    payload_size_kb = payload_size_bytes / 1024
    
    # Extract metrics
    signal_count = data.get("count", 0)
    backend_performance = data.get("performance", {})
    
    # Print results
    print("📊 Performance Results:")
    print(f"{'─'*60}")
    
    print(f"\n🌐 Network Metrics:")
    print(f"  Total Request Time:     {request_duration:.3f}s")
    print(f"  HTTP Status Code:       {response.status_code}")
    print(f"  Payload Size:           {payload_size_kb:.2f} KB ({payload_size_bytes:,} bytes)")
    
    if backend_performance:
        print(f"\n⚡ Backend Performance (from response):")
        print(f"  Backend Time:           {backend_performance.get('total_time_seconds', 'N/A')}s")
        print(f"  Database Queries:       {backend_performance.get('query_count', 'N/A')}")
        print(f"  Backend Payload Size:   {backend_performance.get('payload_size_kb', 'N/A')} KB")
    
    print(f"\n📈 Data Metrics:")
    print(f"  Signals Returned:       {signal_count}")
    print(f"  Timeframe:              {timeframe}")
    print(f"  Limit:                  {limit}")
    
    # Check for articles
    if data.get("signals"):
        first_signal = data["signals"][0]
        article_count = len(first_signal.get("recent_articles", []))
        narrative_count = len(first_signal.get("narratives", []))
        print(f"  Articles per Signal:    {article_count} (sample from first signal)")
        print(f"  Narratives per Signal:  {narrative_count} (sample from first signal)")
    
    # Performance assessment
    print(f"\n✅ Performance Assessment:")
    
    if backend_performance:
        backend_time = backend_performance.get('total_time_seconds', 999)
        query_count = backend_performance.get('query_count', 999)
        
        if backend_time < 1.0:
            print(f"  Backend Speed:          ✅ Excellent ({backend_time:.3f}s)")
        elif backend_time < 2.0:
            print(f"  Backend Speed:          ✅ Good ({backend_time:.3f}s)")
        elif backend_time < 5.0:
            print(f"  Backend Speed:          ⚠️  Acceptable ({backend_time:.3f}s)")
        else:
            print(f"  Backend Speed:          ❌ Slow ({backend_time:.3f}s)")
        
        if query_count <= 3:
            print(f"  Query Optimization:     ✅ Excellent ({query_count} queries)")
        elif query_count <= 10:
            print(f"  Query Optimization:     ⚠️  Could be better ({query_count} queries)")
        else:
            print(f"  Query Optimization:     ❌ N+1 problem detected ({query_count} queries)")
    
    if request_duration < 2.0:
        print(f"  Total Response Time:    ✅ Excellent ({request_duration:.3f}s)")
    elif request_duration < 5.0:
        print(f"  Total Response Time:    ⚠️  Acceptable ({request_duration:.3f}s)")
    else:
        print(f"  Total Response Time:    ❌ Slow ({request_duration:.3f}s)")
    
    if payload_size_kb < 100:
        print(f"  Payload Size:           ✅ Excellent ({payload_size_kb:.2f} KB)")
    elif payload_size_kb < 200:
        print(f"  Payload Size:           ⚠️  Acceptable ({payload_size_kb:.2f} KB)")
    else:
        print(f"  Payload Size:           ❌ Large ({payload_size_kb:.2f} KB)")
    
    print(f"\n{'='*60}\n")
    
    return {
        "request_duration": request_duration,
        "payload_size_kb": payload_size_kb,
        "signal_count": signal_count,
        "backend_performance": backend_performance,
        "status_code": response.status_code,
    }


def main():
    """Main function to run the performance test."""
    parser = argparse.ArgumentParser(
        description="Test Signals endpoint performance"
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL of the API (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--timeframe",
        default="7d",
        choices=["24h", "7d", "30d"],
        help="Timeframe for signals (default: 7d)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum number of signals (default: 50)"
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="Number of times to repeat the test (default: 1)"
    )
    
    args = parser.parse_args()
    
    if args.repeat > 1:
        print(f"\nRunning {args.repeat} tests...\n")
        results = []
        
        for i in range(args.repeat):
            print(f"\n{'#'*60}")
            print(f"Test Run {i + 1} of {args.repeat}")
            print(f"{'#'*60}")
            
            result = test_signals_endpoint(
                base_url=args.base_url,
                timeframe=args.timeframe,
                limit=args.limit
            )
            results.append(result)
            
            if i < args.repeat - 1:
                print("Waiting 3 seconds before next test...")
                time.sleep(3)
        
        # Calculate averages
        if results and "error" not in results[0]:
            avg_duration = sum(r["request_duration"] for r in results) / len(results)
            avg_payload = sum(r["payload_size_kb"] for r in results) / len(results)
            
            print(f"\n{'='*60}")
            print(f"Average Results ({args.repeat} runs):")
            print(f"{'='*60}")
            print(f"  Avg Request Time:       {avg_duration:.3f}s")
            print(f"  Avg Payload Size:       {avg_payload:.2f} KB")
            print(f"{'='*60}\n")
    else:
        test_signals_endpoint(
            base_url=args.base_url,
            timeframe=args.timeframe,
            limit=args.limit
        )


if __name__ == "__main__":
    main()
