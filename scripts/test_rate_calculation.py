#!/usr/bin/env python3
"""
Quick test to verify rate limiting calculations.
"""

def calculate_throughput(batch_size: int, batch_delay: int, article_delay: float):
    """Calculate expected throughput for given parameters."""
    time_per_batch = ((batch_size - 1) * article_delay) + batch_delay
    articles_per_minute = (batch_size / time_per_batch) * 60
    return time_per_batch, articles_per_minute


def test_configurations():
    """Test various rate limiting configurations."""
    configs = [
        # (batch_size, batch_delay, article_delay, description)
        (15, 30, 1.0, "Default conservative"),
        (20, 30, 0.5, "Old aggressive"),
        (15, 30, 0.5, "Faster conservative"),
        (10, 30, 1.0, "Very conservative"),
        (20, 30, 1.0, "Slower aggressive"),
    ]
    
    print("Rate Limiting Configuration Tests")
    print("=" * 80)
    print(f"{'Config':<25} {'Time/Batch':<15} {'Articles/Min':<15} {'Status':<20}")
    print("-" * 80)
    
    for batch_size, batch_delay, article_delay, desc in configs:
        time_per_batch, articles_per_minute = calculate_throughput(
            batch_size, batch_delay, article_delay
        )
        
        if articles_per_minute > 22:
            status = "⚠️  TOO FAST"
        elif articles_per_minute > 20:
            status = "✓ Safe range"
        else:
            status = "✓ Very safe"
        
        config_str = f"B:{batch_size} D:{batch_delay}s A:{article_delay}s"
        print(f"{desc:<25} {time_per_batch:>6.1f}s         {articles_per_minute:>6.1f}/min      {status}")
    
    print("=" * 80)
    print("\nTarget: <20 articles/min (leaves 20% buffer under 25/min limit)")
    print("Warning threshold: >22 articles/min")


if __name__ == "__main__":
    test_configurations()
