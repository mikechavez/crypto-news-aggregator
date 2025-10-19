#!/usr/bin/env python3
"""
Test script to debug the archive tab API endpoint.

Tests the archived narratives API endpoint and logs the full response structure.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

import httpx
import json
from datetime import datetime


async def test_archive_api():
    """Test the archived narratives API endpoint."""
    
    # Get API URL from environment or use default
    api_url = os.getenv("API_URL", "http://localhost:8000")
    endpoint = f"{api_url}/api/v1/narratives/archived"
    
    print("=" * 80)
    print("TESTING ARCHIVED NARRATIVES API ENDPOINT")
    print("=" * 80)
    print(f"\nEndpoint: {endpoint}")
    print(f"Parameters: limit=50, days=30")
    print()
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test with default parameters (same as frontend)
            params = {"limit": 50, "days": 30}
            response = await client.get(endpoint, params=params)
            
            print(f"Status Code: {response.status_code}")
            print()
            
            if response.status_code == 200:
                narratives = response.json()
                
                print(f"✓ API returned {len(narratives)} narratives")
                print()
                
                if narratives:
                    print("=" * 80)
                    print("NARRATIVE DETAILS")
                    print("=" * 80)
                    
                    for i, narrative in enumerate(narratives, 1):
                        print(f"\n{i}. {narrative.get('title', 'N/A')}")
                        print(f"   Theme: {narrative.get('theme', 'N/A')}")
                        print(f"   Lifecycle State: {narrative.get('lifecycle_state', 'N/A')}")
                        print(f"   Article Count: {narrative.get('article_count', 0)}")
                        print(f"   Entities: {', '.join(narrative.get('entities', [])[:5])}")
                        print(f"   Last Updated: {narrative.get('last_updated', 'N/A')}")
                        print(f"   First Seen: {narrative.get('first_seen', 'N/A')}")
                        print(f"   Reawakening Count: {narrative.get('reawakening_count', 0)}")
                        
                        # Check if articles are included
                        articles = narrative.get('articles', [])
                        print(f"   Articles Included: {len(articles)}")
                    
                    print()
                    print("=" * 80)
                    print("SUMMARY STATISTICS")
                    print("=" * 80)
                    
                    # Count by lifecycle_state
                    lifecycle_counts = {}
                    total_articles = 0
                    
                    for narrative in narratives:
                        state = narrative.get('lifecycle_state', 'unknown')
                        lifecycle_counts[state] = lifecycle_counts.get(state, 0) + 1
                        total_articles += narrative.get('article_count', 0)
                    
                    print(f"\nTotal Narratives: {len(narratives)}")
                    print(f"Total Articles: {total_articles}")
                    print(f"\nLifecycle State Breakdown:")
                    for state, count in sorted(lifecycle_counts.items()):
                        print(f"  {state}: {count}")
                    
                    # Check for reawakened narratives
                    reawakened = [n for n in narratives if n.get('reawakening_count', 0) > 0]
                    print(f"\nReawakened Narratives: {len(reawakened)}")
                    
                    print()
                    print("=" * 80)
                    print("FULL RESPONSE STRUCTURE (First Narrative)")
                    print("=" * 80)
                    print(json.dumps(narratives[0], indent=2, default=str))
                    
                else:
                    print("⚠ API returned 0 narratives")
                    print("\nThis could mean:")
                    print("  1. No narratives have lifecycle_state='dormant'")
                    print("  2. No dormant narratives in the last 30 days")
                    print("  3. Database query issue")
                
            else:
                print(f"✗ API request failed with status {response.status_code}")
                print(f"Response: {response.text}")
    
    except Exception as e:
        print(f"✗ Error testing API: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_archive_api())
