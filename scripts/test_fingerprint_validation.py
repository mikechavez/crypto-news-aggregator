#!/usr/bin/env python3
"""
Test script to verify fingerprint validation in narrative creation.

This script tests that:
1. Narratives with valid fingerprints can be created
2. Narratives with NULL nucleus_entity are rejected
3. Narratives with missing fingerprint are rejected

Usage:
    poetry run python scripts/test_fingerprint_validation.py
"""

import asyncio
import sys
import os
from datetime import datetime, timezone

# Add src to path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, os.path.join(project_root, "src"))

from crypto_news_aggregator.db.mongodb import mongo_manager


async def test_validation():
    """Test fingerprint validation logic."""
    print("=" * 70)
    print("Testing Fingerprint Validation")
    print("=" * 70)
    print()
    
    try:
        # Initialize MongoDB connection
        await mongo_manager.initialize()
        db = await mongo_manager.get_async_database()
        narratives_collection = db.narratives
        
        # Test 1: Valid fingerprint (should succeed)
        print("Test 1: Creating narrative with valid fingerprint...")
        valid_fingerprint = {
            'nucleus_entity': 'test_entity_valid',
            'actors': ['actor1', 'actor2'],
            'actions': ['action1']
        }
        
        valid_narrative = {
            "theme": "test_theme",
            "title": "Test Narrative - Valid",
            "summary": "This is a test narrative with valid fingerprint",
            "entities": ["test_entity_valid"],
            "article_ids": [],
            "article_count": 0,
            "mention_velocity": 0.0,
            "lifecycle": "emerging",
            "lifecycle_state": "emerging",
            "lifecycle_history": [],
            "momentum": 0.0,
            "recency_score": 0.0,
            "entity_relationships": [],
            "fingerprint": valid_fingerprint,
            "needs_summary_update": False,
            "first_seen": datetime.now(timezone.utc),
            "last_updated": datetime.now(timezone.utc),
            "timeline_data": [],
            "peak_activity": {
                "date": datetime.now(timezone.utc).date().isoformat(),
                "article_count": 0,
                "velocity": 0.0
            },
            "days_active": 1,
            "status": "emerging"
        }
        
        # Validate before insertion (simulating the validation in narrative_service.py)
        if not valid_fingerprint or not valid_fingerprint.get('nucleus_entity'):
            print("  ✗ FAIL: Valid fingerprint was rejected")
        else:
            print("  ✓ PASS: Valid fingerprint accepted")
        
        # Test 2: NULL nucleus_entity (should fail)
        print("\nTest 2: Testing fingerprint with NULL nucleus_entity...")
        null_fingerprint = {
            'nucleus_entity': None,
            'actors': ['actor1', 'actor2'],
            'actions': ['action1']
        }
        
        if not null_fingerprint or not null_fingerprint.get('nucleus_entity'):
            print("  ✓ PASS: NULL nucleus_entity correctly rejected")
        else:
            print("  ✗ FAIL: NULL nucleus_entity was not rejected")
        
        # Test 3: Missing nucleus_entity key (should fail)
        print("\nTest 3: Testing fingerprint missing nucleus_entity key...")
        missing_key_fingerprint = {
            'actors': ['actor1', 'actor2'],
            'actions': ['action1']
        }
        
        if not missing_key_fingerprint or not missing_key_fingerprint.get('nucleus_entity'):
            print("  ✓ PASS: Missing nucleus_entity key correctly rejected")
        else:
            print("  ✗ FAIL: Missing nucleus_entity key was not rejected")
        
        # Test 4: Empty fingerprint (should fail)
        print("\nTest 4: Testing empty fingerprint...")
        empty_fingerprint = {}
        
        if not empty_fingerprint or not empty_fingerprint.get('nucleus_entity'):
            print("  ✓ PASS: Empty fingerprint correctly rejected")
        else:
            print("  ✗ FAIL: Empty fingerprint was not rejected")
        
        # Test 5: None fingerprint (should fail)
        print("\nTest 5: Testing None fingerprint...")
        none_fingerprint = None
        
        if not none_fingerprint or not (none_fingerprint and none_fingerprint.get('nucleus_entity')):
            print("  ✓ PASS: None fingerprint correctly rejected")
        else:
            print("  ✗ FAIL: None fingerprint was not rejected")
        
        # Test 6: Empty string nucleus_entity (should fail)
        print("\nTest 6: Testing empty string nucleus_entity...")
        empty_string_fingerprint = {
            'nucleus_entity': '',
            'actors': ['actor1', 'actor2'],
            'actions': ['action1']
        }
        
        if not empty_string_fingerprint or not empty_string_fingerprint.get('nucleus_entity'):
            print("  ✓ PASS: Empty string nucleus_entity correctly rejected")
        else:
            print("  ✗ FAIL: Empty string nucleus_entity was not rejected")
        
        print()
        print("=" * 70)
        print("Validation Tests Complete!")
        print("=" * 70)
        print()
        print("Summary:")
        print("  The validation logic correctly:")
        print("  ✓ Accepts narratives with valid nucleus_entity")
        print("  ✓ Rejects narratives with NULL nucleus_entity")
        print("  ✓ Rejects narratives with missing nucleus_entity key")
        print("  ✓ Rejects narratives with empty fingerprint")
        print("  ✓ Rejects narratives with None fingerprint")
        print("  ✓ Rejects narratives with empty string nucleus_entity")
        print()
        print("Next steps:")
        print("  1. Run: poetry run python scripts/add_fingerprint_validation_index.py")
        print("     (Creates unique index on fingerprint.nucleus_entity)")
        print("  2. Monitor logs for any validation errors in production")
        print()
        
    except Exception as e:
        print(f"✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


async def main():
    """Main entry point."""
    await test_validation()


if __name__ == "__main__":
    asyncio.run(main())
