"""
Test script to verify MongoDB connection and clean shutdown behavior.
"""

import asyncio
import sys
from src.crypto_news_aggregator.db.mongodb import mongo_manager


def print_banner():
    print("\n" + "=" * 50)
    print("TESTING MONGODB CONNECTION AND SHUTDOWN")
    print("=" * 50)


async def test_connection():
    """Test MongoDB connection and print connection info."""
    print("\nTesting MongoDB connection...")
    try:
        # Initialize the MongoDB connection
        await mongo_manager.initialize()

        # Get the async client
        client = await mongo_manager.get_async_client()

        # Get database instance
        db = client[mongo_manager.settings.MONGODB_NAME]

        # Test connection with a simple command
        server_info = await db.command("ping")
        print(
            f"✅ Successfully connected to MongoDB server: {server_info.get('ok') == 1.0}"
        )

        # Print database stats
        stats = await db.command("dbstats")
        print(f"\nDatabase Stats:")
        print(f"- Name: {stats['db']}")
        print(f"- Collections: {stats['collections']}")
        print(f"- Documents: {stats['objects']}")
        print(f"- Data Size: {stats['dataSize'] / (1024*1024):.2f} MB")

        return True
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        return False
    finally:
        # Clean up the connection
        if mongo_manager.is_initialized():
            await mongo_manager.close()


async def main():
    """Main test function."""
    print_banner()

    # Test connection
    success = await test_connection()

    if success:
        print("\n✅ MongoDB connection test completed successfully!")
    else:
        print("\n❌ MongoDB connection test failed!")

    print("\nPress Ctrl+C to test shutdown behavior...")

    # Keep the connection open to test shutdown
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        print("\nShutting down gracefully...")
    finally:
        # Ensure cleanup on exit
        if mongo_manager.is_initialized():
            await mongo_manager.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nCaught KeyboardInterrupt, shutting down...")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
    finally:
        print("Test completed. Exiting...")
        sys.exit(0)
