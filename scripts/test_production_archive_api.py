#!/usr/bin/env python3
"""
Test the production Railway API to check if archived narratives are returned correctly.

This script tests if the API's fallback logic for old schema narratives is working.
"""

import asyncio
import httpx
import json
import os
from datetime import datetime


# Production Railway URL
PRODUCTION_URL = "https://crypto-news-aggregator-production.up.railway.app"

# You can also set this via environment variable
API_URL = os.getenv("RAILWAY_API_URL", PRODUCTION_URL)


async def test_production_archive_api():
    """Test the production archived narratives endpoint."""
    
    print("=" * 80)
    print("TESTING PRODUCTION ARCHIVE API")
    print("=" * 80)
    print(f"\nAPI URL: {API_URL}")
    print(f"Endpoint: /api/v1/narratives/archived")
    print(f"Parameters: limit=50, days=30")
    print()
    
    # Test multiple possible endpoints
    endpoints_to_test = [
        (f"{API_URL}/api/v1/narratives/active", "Base API (with /api/v1)"),
        (f"{API_URL}/narratives/active", "Base API (without /api/v1)"),
        (f"{API_URL}/health", "Health check"),
        (f"{API_URL}/api/v1/health", "Health check (with /api/v1)"),
    ]
    
    endpoint = f"{API_URL}/api/v1/narratives/archived"
    params = {"limit": 50, "days": 30}
    
    # Headers (add Authorization if needed)
    headers = {
        "Accept": "application/json",
        "User-Agent": "Archive-Debug-Script/1.0"
    }
    
    # Add API key if available
    api_key = os.getenv("API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
        print("✓ Using API key from environment")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test multiple endpoints to find which one works
            print("Testing various endpoints to find the correct API path...")
            print()
            
            working_endpoint = None
            for test_url, description in endpoints_to_test:
                try:
                    print(f"Testing {description}: {test_url}")
                    test_response = await client.get(test_url, headers=headers, timeout=10.0)
                    print(f"  Status: {test_response.status_code}")
                    
                    if test_response.status_code == 200:
                        print(f"  ✓ SUCCESS - This endpoint works!")
                        working_endpoint = test_url
                        break
                    elif test_response.status_code == 401:
                        print(f"  ⚠ Requires authentication")
                    else:
                        print(f"  Response: {test_response.text[:100]}")
                except Exception as e:
                    print(f"  ✗ Error: {str(e)[:100]}")
                print()
            
            if not working_endpoint:
                print("❌ Could not find a working API endpoint")
                print("\nThe Railway deployment may not be running or the URL is incorrect.")
                print("Check Railway dashboard for deployment status.")
                return
            
            print("=" * 80)
            print(f"Using working endpoint pattern for archived narratives...")
            print()
            
            # Adjust archived endpoint based on what worked
            if "/api/v1/" in working_endpoint:
                endpoint = f"{API_URL}/api/v1/narratives/archived"
            else:
                endpoint = f"{API_URL}/narratives/archived"
            
            print(f"Sending request to: {endpoint}")
            response = await client.get(endpoint, params=params, headers=headers)
            
            print(f"Status Code: {response.status_code}")
            print()
            
            if response.status_code == 200:
                narratives = response.json()
                
                print("=" * 80)
                print("API RESPONSE SUMMARY")
                print("=" * 80)
                print(f"\n✓ Total narratives returned: {len(narratives)}")
                print()
                
                if not narratives:
                    print("⚠ API returned 0 narratives")
                    print("\nPossible reasons:")
                    print("  1. No dormant narratives in production database")
                    print("  2. No dormant narratives updated in last 30 days")
                    print("  3. Database query issue")
                    return
                
                # Analyze each narrative
                print("=" * 80)
                print("NARRATIVE DETAILS")
                print("=" * 80)
                print()
                
                issues_found = []
                
                for i, narrative in enumerate(narratives, 1):
                    narrative_id = narrative.get('_id', 'N/A')
                    title = narrative.get('title')
                    theme = narrative.get('theme')
                    summary = narrative.get('summary')
                    story = narrative.get('story')
                    entities = narrative.get('entities', [])
                    article_count = narrative.get('article_count', 0)
                    lifecycle_state = narrative.get('lifecycle_state', 'N/A')
                    
                    # Determine display title (same logic as frontend)
                    display_title = title or theme
                    display_summary = summary or story
                    
                    print(f"{i}. Narrative ID: {narrative_id}")
                    print(f"   Title: {title if title else '❌ NULL'}")
                    print(f"   Theme: {theme if theme else '❌ NULL'}")
                    print(f"   Display Title: {display_title if display_title else '❌ EMPTY'}")
                    print(f"   Summary: {summary[:50] + '...' if summary else '❌ NULL'}")
                    print(f"   Story: {story[:50] + '...' if story else '❌ NULL'}")
                    print(f"   Display Summary: {display_summary[:50] + '...' if display_summary else '❌ EMPTY'}")
                    print(f"   Entities: {len(entities)} - {', '.join(entities[:3]) if entities else '❌ EMPTY'}")
                    print(f"   Article Count: {article_count}")
                    print(f"   Lifecycle State: {lifecycle_state}")
                    
                    # Check for issues
                    narrative_issues = []
                    
                    if not display_title:
                        narrative_issues.append("No title or theme")
                    
                    if not display_summary:
                        narrative_issues.append("No summary or story")
                    
                    if not entities:
                        narrative_issues.append("No entities")
                    
                    if narrative_issues:
                        print(f"   ⚠ Issues: {', '.join(narrative_issues)}")
                        issues_found.append({
                            'id': narrative_id,
                            'article_count': article_count,
                            'issues': narrative_issues
                        })
                    else:
                        print(f"   ✓ All fields present")
                    
                    print()
                
                # Summary of issues
                print("=" * 80)
                print("ISSUE SUMMARY")
                print("=" * 80)
                print()
                
                if issues_found:
                    print(f"❌ Found {len(issues_found)} narrative(s) with missing fields:")
                    print()
                    
                    for issue in issues_found:
                        print(f"  • ID: {issue['id']}")
                        print(f"    Article Count: {issue['article_count']}")
                        print(f"    Issues: {', '.join(issue['issues'])}")
                        print()
                    
                    print("DIAGNOSIS:")
                    print("-" * 80)
                    print("The API is NOT properly transforming old schema narratives.")
                    print("The fallback logic in narratives.py (lines 359-379) is not working.")
                    print()
                    print("This explains why the archive tab shows '2 articles' but no cards:")
                    print("  - The API returns the narrative")
                    print("  - But with empty title/summary/entities")
                    print("  - Frontend can't render a card with no data")
                    print()
                    print("SOLUTION:")
                    print("  1. Fix the API fallback logic for old schema narratives")
                    print("  2. OR migrate old schema narratives to new format")
                    
                else:
                    print("✓ All narratives have proper title, summary, and entities")
                    print()
                    print("DIAGNOSIS:")
                    print("-" * 80)
                    print("The API is correctly transforming narratives.")
                    print("If the archive tab is still empty, the issue is in the frontend.")
                    print()
                    print("Check:")
                    print("  1. Browser console for [DEBUG] messages")
                    print("  2. Network tab to verify API response")
                    print("  3. Frontend rendering logic in Narratives.tsx")
                
                # Check for the specific 2-article narrative
                print()
                print("=" * 80)
                print("CHECKING FOR 2-ARTICLE NARRATIVE")
                print("=" * 80)
                print()
                
                two_article_narratives = [n for n in narratives if n.get('article_count') == 2]
                
                if two_article_narratives:
                    print(f"✓ Found {len(two_article_narratives)} narrative(s) with 2 articles:")
                    print()
                    
                    for n in two_article_narratives:
                        print(f"  ID: {n.get('_id', 'N/A')}")
                        print(f"  Title: {n.get('title') or n.get('theme') or 'EMPTY'}")
                        print(f"  Summary: {(n.get('summary') or n.get('story') or 'EMPTY')[:80]}...")
                        print(f"  Entities: {len(n.get('entities', []))}")
                        print()
                    
                    if any(not (n.get('title') or n.get('theme')) for n in two_article_narratives):
                        print("❌ The 2-article narrative has no title!")
                        print("This is why it's not rendering in the frontend.")
                    else:
                        print("✓ The 2-article narrative has a title.")
                        print("It should be visible in the frontend.")
                else:
                    print("⚠ No narratives with exactly 2 articles found in API response")
                    print("The database has one, but the API didn't return it.")
                    print("Check the API logs for filtering issues.")
                
                # Show full JSON for first narrative (for debugging)
                print()
                print("=" * 80)
                print("FULL JSON (First Narrative)")
                print("=" * 80)
                print()
                print(json.dumps(narratives[0], indent=2, default=str))
                
            elif response.status_code == 401:
                print("❌ Authentication failed (401 Unauthorized)")
                print("\nThe API requires authentication.")
                print("Set the API_KEY environment variable:")
                print("  export API_KEY='your-api-key'")
                
            elif response.status_code == 404:
                print("❌ Endpoint not found (404)")
                print("\nThe /api/v1/narratives/archived endpoint doesn't exist.")
                print("Check if the API is deployed correctly.")
                
            elif response.status_code >= 500:
                print(f"❌ Server error ({response.status_code})")
                print(f"\nResponse: {response.text}")
                print("\nCheck Railway logs for error details.")
                
            else:
                print(f"❌ Unexpected status code: {response.status_code}")
                print(f"Response: {response.text}")
    
    except httpx.ConnectError as e:
        print(f"❌ Connection failed: {e}")
        print(f"\nCouldn't connect to {API_URL}")
        print("\nPossible reasons:")
        print("  1. API is not deployed or not running")
        print("  2. Wrong URL")
        print("  3. Network issue")
        print("\nCheck Railway dashboard to verify deployment status.")
    
    except httpx.TimeoutException:
        print("❌ Request timed out")
        print("\nThe API took too long to respond.")
        print("Check Railway logs for performance issues.")
    
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print()


if __name__ == "__main__":
    print()
    print("Testing production Railway API...")
    print()
    print("You can override the API URL with:")
    print("  export RAILWAY_API_URL='https://your-custom-url.railway.app'")
    print()
    print("If authentication is required:")
    print("  export API_KEY='your-api-key'")
    print()
    print("-" * 80)
    print()
    
    asyncio.run(test_production_archive_api())
