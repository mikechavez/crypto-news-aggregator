#!/usr/bin/env python3
"""
Test script to verify narrative articles API endpoint.
Tests the full flow: fetch narratives -> get specific narrative -> verify articles.
"""
import requests
import json
import sys
import os
from typing import Optional

# API base URL - update if needed
API_BASE_URL = "https://context-owl-production.up.railway.app"
API_KEY = os.getenv("API_KEY", "")

def get_headers():
    """Get headers with API key."""
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["X-API-Key"] = API_KEY
    return headers

def test_narratives_list():
    """Fetch list of narratives."""
    print("=" * 80)
    print("STEP 1: Fetching narratives list")
    print("=" * 80)
    
    url = f"{API_BASE_URL}/api/v1/narratives/active"
    print(f"GET {url}")
    
    try:
        response = requests.get(url, headers=get_headers(), timeout=10)
        response.raise_for_status()
        narratives = response.json()
        
        print(f"Status: {response.status_code}")
        print(f"Response type: {type(narratives).__name__}")
        print(f"Number of narratives: {len(narratives)}")
        
        if narratives and len(narratives) > 0:
            first_narrative = narratives[0]
            print(f"\nFirst narrative:")
            print(f"  Available keys: {list(first_narrative.keys())}")
            print(f"  ID (_id): {first_narrative.get('_id')}")
            print(f"  ID (id): {first_narrative.get('id')}")
            print(f"  Title: {first_narrative.get('title')}")
            print(f"  Article count: {first_narrative.get('article_count', 0)}")
            narrative_id = first_narrative.get('_id') or first_narrative.get('id')
            return narrative_id
        else:
            print("ERROR: No narratives found!")
            return None
            
    except Exception as e:
        print(f"ERROR: {e}")
        return None

def test_narrative_detail(narrative_id: int):
    """Fetch specific narrative with articles."""
    print("\n" + "=" * 80)
    print(f"STEP 2: Fetching narrative detail (ID: {narrative_id})")
    print("=" * 80)
    
    url = f"{API_BASE_URL}/api/v1/narratives/{narrative_id}"
    print(f"GET {url}")
    
    try:
        response = requests.get(url, headers=get_headers(), timeout=10)
        response.raise_for_status()
        data = response.json()
        
        print(f"Status: {response.status_code}")
        print(f"\nResponse structure:")
        print(f"  Top-level keys: {list(data.keys())}")
        
        # Check for articles
        articles = data.get('articles', [])
        print(f"\n  Articles field exists: {'articles' in data}")
        print(f"  Articles type: {type(articles)}")
        print(f"  Number of articles: {len(articles) if isinstance(articles, list) else 'N/A'}")
        
        # Print full response for debugging
        print(f"\nFull response (formatted):")
        print(json.dumps(data, indent=2, default=str))
        
        # If articles exist, show structure
        if articles and len(articles) > 0:
            print(f"\n" + "=" * 80)
            print("ARTICLE STRUCTURE (First article)")
            print("=" * 80)
            first_article = articles[0]
            print(json.dumps(first_article, indent=2, default=str))
            
            print(f"\nArticle fields:")
            for key in first_article.keys():
                print(f"  - {key}: {type(first_article[key]).__name__}")
        else:
            print("\n⚠️  WARNING: No articles in response!")
            print("   This is likely the root cause of the frontend issue.")
        
        return data
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    print("Testing Narrative Articles API")
    print("=" * 80)
    
    # Step 1: Get a narrative ID
    narrative_id = test_narratives_list()
    
    if not narrative_id:
        print("\n❌ FAILED: Could not fetch narratives list")
        sys.exit(1)
    
    # Step 2: Get narrative detail with articles
    detail = test_narrative_detail(narrative_id)
    
    if not detail:
        print("\n❌ FAILED: Could not fetch narrative detail")
        sys.exit(1)
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    articles = detail.get('articles', [])
    if articles and len(articles) > 0:
        print(f"✅ SUCCESS: API returns {len(articles)} articles")
        print(f"   Article fields: {', '.join(articles[0].keys())}")
    else:
        print("❌ PROBLEM: API returns NO articles")
        print("   Check backend endpoint implementation")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
