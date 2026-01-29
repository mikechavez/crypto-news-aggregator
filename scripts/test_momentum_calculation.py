#!/usr/bin/env python3
"""
Test script to verify momentum-aware lifecycle calculation.

Tests the new calculate_momentum() and determine_lifecycle_stage() functions
with various scenarios.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from crypto_news_aggregator.services.narrative_service import (
    calculate_momentum,
    determine_lifecycle_stage
)


def test_momentum_calculation():
    """Test momentum calculation with various article date patterns."""
    
    print("=" * 60)
    print("TESTING MOMENTUM CALCULATION")
    print("=" * 60)
    
    now = datetime.now(timezone.utc)
    
    # Test 1: Growing momentum (accelerating articles)
    print("\n1. Growing Momentum (accelerating articles)")
    dates_growing = [
        now - timedelta(hours=48),  # 2 days ago
        now - timedelta(hours=36),  # 1.5 days ago
        now - timedelta(hours=24),  # 1 day ago
        now - timedelta(hours=6),   # 6 hours ago
        now - timedelta(hours=3),   # 3 hours ago
        now - timedelta(hours=1),   # 1 hour ago
    ]
    momentum = calculate_momentum(dates_growing)
    print(f"   Result: {momentum} (expected: growing)")
    assert momentum == "growing", f"Expected 'growing', got '{momentum}'"
    
    # Test 2: Declining momentum (decelerating articles)
    # Older period: many articles in short time (high velocity)
    # Recent period: few articles spread out (low velocity)
    print("\n2. Declining Momentum (decelerating articles)")
    dates_declining = [
        now - timedelta(hours=48),  # 2 days ago - start of older period
        now - timedelta(hours=46),  # Older period: 3 articles in 4 hours
        now - timedelta(hours=44),  # (high velocity)
        now - timedelta(hours=20),  # Recent period: 3 articles in 18 hours
        now - timedelta(hours=10),  # (low velocity = declining)
        now - timedelta(hours=2),   # End of recent period
    ]
    dates_declining.sort()
    
    momentum = calculate_momentum(dates_declining)
    print(f"   Result: {momentum} (expected: declining)")
    assert momentum == "declining", f"Expected 'declining', got '{momentum}'"
    
    # Test 3: Stable momentum (consistent rate)
    print("\n3. Stable Momentum (consistent rate)")
    dates_stable = [
        now - timedelta(hours=24),
        now - timedelta(hours=20),
        now - timedelta(hours=16),
        now - timedelta(hours=12),
        now - timedelta(hours=8),
        now - timedelta(hours=4),
    ]
    momentum = calculate_momentum(dates_stable)
    print(f"   Result: {momentum} (expected: stable)")
    assert momentum == "stable", f"Expected 'stable', got '{momentum}'"
    
    # Test 4: Unknown momentum (too few articles)
    print("\n4. Unknown Momentum (too few articles)")
    dates_few = [
        now - timedelta(hours=24),
        now - timedelta(hours=12),
    ]
    momentum = calculate_momentum(dates_few)
    print(f"   Result: {momentum} (expected: unknown)")
    assert momentum == "unknown", f"Expected 'unknown', got '{momentum}'"
    
    print("\n✅ All momentum tests passed!")


def test_lifecycle_stages():
    """Test lifecycle stage determination with momentum integration."""
    
    print("\n" + "=" * 60)
    print("TESTING LIFECYCLE STAGES")
    print("=" * 60)
    
    # Test 1: Emerging → Rising (with growth)
    print("\n1. Emerging → Rising (3 articles, growing)")
    lifecycle = determine_lifecycle_stage(3, 0.5, "growing")
    print(f"   Result: {lifecycle} (expected: rising)")
    assert lifecycle == "rising", f"Expected 'rising', got '{lifecycle}'"
    
    # Test 2: Hot with growth → Heating
    print("\n2. Hot → Heating (6 articles, 2.0 velocity, growing)")
    lifecycle = determine_lifecycle_stage(6, 2.0, "growing")
    print(f"   Result: {lifecycle} (expected: heating)")
    assert lifecycle == "heating", f"Expected 'heating', got '{lifecycle}'"
    
    # Test 3: Mature with decline → Cooling
    print("\n3. Mature → Cooling (10 articles, 5.5 velocity, declining)")
    lifecycle = determine_lifecycle_stage(10, 5.5, "declining")
    print(f"   Result: {lifecycle} (expected: cooling)")
    assert lifecycle == "cooling", f"Expected 'cooling', got '{lifecycle}'"
    
    # Test 4: Hot stage (adjusted thresholds)
    print("\n4. Hot (5 articles, 1.0 velocity)")
    lifecycle = determine_lifecycle_stage(5, 1.0, "stable")
    print(f"   Result: {lifecycle} (expected: hot)")
    assert lifecycle == "hot", f"Expected 'hot', got '{lifecycle}'"
    
    # Test 5: Mature stage (high velocity)
    print("\n5. Mature (8 articles, 6.0 velocity)")
    lifecycle = determine_lifecycle_stage(8, 6.0, "stable")
    print(f"   Result: {lifecycle} (expected: mature)")
    assert lifecycle == "mature", f"Expected 'mature', got '{lifecycle}'"
    
    # Test 6: Emerging (low counts)
    print("\n6. Emerging (2 articles, 0.3 velocity)")
    lifecycle = determine_lifecycle_stage(2, 0.3, "unknown")
    print(f"   Result: {lifecycle} (expected: emerging)")
    assert lifecycle == "emerging", f"Expected 'emerging', got '{lifecycle}'"
    
    print("\n✅ All lifecycle tests passed!")


def test_threshold_comparison():
    """Compare old vs new thresholds."""
    
    print("\n" + "=" * 60)
    print("THRESHOLD COMPARISON (Old vs New)")
    print("=" * 60)
    
    test_cases = [
        (5, 1.5, "unknown"),   # 5 articles, 1.5 velocity
        (8, 2.0, "stable"),    # 8 articles, 2.0 velocity
        (12, 3.5, "stable"),   # 12 articles, 3.5 velocity
        (3, 0.5, "growing"),   # 3 articles, 0.5 velocity, growing
    ]
    
    print("\n{:<20} {:<15} {:<15}".format("Scenario", "Old Result", "New Result"))
    print("-" * 50)
    
    for article_count, velocity, momentum in test_cases:
        # Old logic (simplified)
        if article_count <= 4:
            old_result = "emerging"
        elif 5 <= article_count <= 10 and velocity > 2.0:
            old_result = "hot"
        elif article_count > 10 or velocity > 3.0:
            old_result = "mature"
        else:
            old_result = "emerging"
        
        # New logic
        new_result = determine_lifecycle_stage(article_count, velocity, momentum)
        
        scenario = f"{article_count}a, {velocity}v"
        if momentum != "unknown":
            scenario += f", {momentum[:4]}"
        
        print(f"{scenario:<20} {old_result:<15} {new_result:<15}")
    
    print("\n📊 Key improvements:")
    print("   - Lower thresholds allow progression beyond 'emerging'")
    print("   - Momentum adds nuance (rising, heating, cooling)")
    print("   - Article count >= 5 now qualifies as 'hot'")


if __name__ == "__main__":
    try:
        test_momentum_calculation()
        test_lifecycle_stages()
        test_threshold_comparison()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nMomentum-aware lifecycle calculation is working correctly.")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
