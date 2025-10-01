"""
Basic test to verify async test functionality.
"""

import pytest
import asyncio


@pytest.mark.asyncio
async def test_async_basic():
    """Basic async test that should always pass."""
    print("\n=== Starting basic async test ===")
    await asyncio.sleep(0.1)  # Simulate async operation
    assert True  # This should always pass
    print("=== Basic async test passed ===\n")
