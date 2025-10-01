"""
Simple test script to verify MongoDB connection and clean shutdown.
"""

import asyncio
import sys


async def test_mongodb_shutdown():
    """Test MongoDB connection and shutdown."""
    from src.crypto_news_aggregator.db.mongodb import get_mongo_manager

    print("\nTesting MongoDB connection and shutdown...")

    # Get the MongoDB manager
    manager = get_mongo_manager()

    try:
        # Initialize the async client
        if not hasattr(manager, "_async_client") or manager._async_client is None:
            from motor.motor_asyncio import AsyncIOMotorClient

            manager._async_client = AsyncIOMotorClient(
                getattr(manager.settings, "MONGODB_URI", "mongodb://localhost:27017"),
                serverSelectionTimeoutMS=5000,
            )

        # Get database name (default to 'crypto_news' if not set)
        db_name = getattr(manager.settings, "MONGODB_DB", "crypto_news")
        db = manager._async_client[db_name]

        # Test connection
        await db.command("ping")
        print(
            f"✓ Successfully connected to MongoDB at {getattr(manager.settings, 'MONGODB_URI', 'mongodb://localhost:27017')}"
        )
        print(f"✓ Using database: {db_name}")

        # Test cleanup
        print("\nTesting shutdown...")
        if hasattr(manager, "aclose"):
            await manager.aclose()
            print("✓ Clean shutdown completed successfully")
        else:
            print("⚠ No aclose() method found on manager")

    except Exception as e:
        print(f"✗ Error during test: {e}")
        return False
    finally:
        print("Test completed.")
        # Ensure we don't leave any connections open
        if hasattr(manager, "_async_client") and manager._async_client is not None:
            manager._async_client = None

    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(test_mongodb_shutdown())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)
