#!/usr/bin/env python3
"""
Inspect the specific dormant narrative with 2 articles to see why it's not rendering.
"""

import asyncio
import sys
from pathlib import Path
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from crypto_news_aggregator.db.mongodb import mongo_manager


async def inspect_dormant_narrative():
    """Inspect the dormant narrative with 2 articles."""
    
    print("=" * 80)
    print("INSPECTING DORMANT NARRATIVE WITH 2 ARTICLES")
    print("=" * 80)
    print()
    
    try:
        db = await mongo_manager.get_async_database()
        collection = db.narratives
        
        # Find the dormant narrative with 2 articles
        narrative = await collection.find_one({
            "article_count": 2,
            "lifecycle_state": "dormant"
        })
        
        if not narrative:
            print("✗ No dormant narrative with 2 articles found")
            return
        
        print("✓ Found the narrative!")
        print()
        
        # Convert ObjectId to string for JSON serialization
        narrative['_id'] = str(narrative['_id'])
        
        # Pretty print the full narrative
        print("FULL NARRATIVE DATA:")
        print("-" * 80)
        print(json.dumps(narrative, indent=2, default=str))
        print()
        
        # Check for potential rendering issues
        print("=" * 80)
        print("POTENTIAL RENDERING ISSUES")
        print("=" * 80)
        print()
        
        issues = []
        
        # Check title
        title = narrative.get('title') or narrative.get('theme')
        if not title:
            issues.append("❌ No title or theme - might render as blank")
        else:
            print(f"✓ Title: {title}")
        
        # Check summary
        summary = narrative.get('summary') or narrative.get('story')
        if not summary:
            issues.append("⚠ No summary or story - card might look empty")
        else:
            print(f"✓ Summary: {summary[:100]}...")
        
        # Check entities
        entities = narrative.get('entities', [])
        if not entities:
            issues.append("⚠ No entities - might affect display")
        else:
            print(f"✓ Entities: {', '.join(entities[:5])}")
        
        # Check lifecycle_state
        lifecycle_state = narrative.get('lifecycle_state')
        if lifecycle_state != 'dormant':
            issues.append(f"❌ lifecycle_state is '{lifecycle_state}', not 'dormant'")
        else:
            print(f"✓ Lifecycle State: {lifecycle_state}")
        
        # Check article_count
        article_count = narrative.get('article_count', 0)
        print(f"✓ Article Count: {article_count}")
        
        # Check dates
        first_seen = narrative.get('first_seen')
        last_updated = narrative.get('last_updated')
        print(f"✓ First Seen: {first_seen}")
        print(f"✓ Last Updated: {last_updated}")
        
        print()
        
        if issues:
            print("ISSUES FOUND:")
            for issue in issues:
                print(f"  {issue}")
        else:
            print("✓ No obvious rendering issues found")
            print()
            print("The narrative has all required fields.")
            print("Check the frontend console logs and Network tab to see if:")
            print("  1. The API is returning this narrative")
            print("  2. The frontend is receiving it")
            print("  3. There's a rendering error in the browser console")
        
        print()
        print("=" * 80)
        print("NEXT STEPS")
        print("=" * 80)
        print()
        print("1. Open the frontend and go to Archive tab")
        print("2. Open browser DevTools Console")
        print("3. Look for this debug message:")
        print("   [DEBUG] archive API returned: X narratives")
        print("4. Check if the API returned this narrative")
        print("5. If yes, check for JavaScript errors in console")
        print("6. If no, check Railway logs for API errors")
        print()
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(inspect_dormant_narrative())
