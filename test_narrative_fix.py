#!/usr/bin/env python3
"""
Test script to verify detect_narratives() works with correct parameters.
"""
import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from crypto_news_aggregator.services.narrative_service import detect_narratives
from crypto_news_aggregator.db.mongodb import initialize_mongodb, mongo_manager


async def test_old_call():
    """Test that old parameters cause TypeError."""
    print("Testing OLD call with invalid parameters...")
    try:
        # This should fail
        narratives = await detect_narratives(min_score=5.0, max_narratives=5)
        print("❌ UNEXPECTED: Old call succeeded (should have failed)")
        return False
    except TypeError as e:
        print(f"✅ EXPECTED: Old call failed with TypeError: {e}")
        return True


async def test_new_call():
    """Test that new parameters work correctly."""
    print("\nTesting NEW call with correct parameters...")
    try:
        # This should work
        narratives = await detect_narratives()
        print(f"✅ SUCCESS: New call succeeded, returned {len(narratives)} narratives")
        return True
    except Exception as e:
        print(f"❌ FAILED: New call failed with error: {e}")
        return False


async def main():
    """Run both tests."""
    print("=" * 60)
    print("Narrative Detection Parameter Fix Verification")
    print("=" * 60)
    
    # Initialize MongoDB
    await initialize_mongodb()
    
    # Test old call fails
    old_test_passed = await test_old_call()
    
    # Test new call works
    new_test_passed = await test_new_call()
    
    # Cleanup
    await mongo_manager.aclose()
    
    print("\n" + "=" * 60)
    if old_test_passed and new_test_passed:
        print("✅ ALL TESTS PASSED - Fix is correct!")
        print("=" * 60)
        return 0
    else:
        print("❌ TESTS FAILED - Fix may not work correctly")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
