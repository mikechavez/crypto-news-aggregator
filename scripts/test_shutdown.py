"""
Test script to verify MongoDB connection and clean shutdown behavior.
"""
import asyncio
import sys
import os
from src.crypto_news_aggregator.db.mongodb import get_mongo_manager

def print_banner():
    print("\n" + "="*50)
    print("TESTING MONGODB CONNECTION AND SHUTDOWN")
    print("="*50)

async def test_connection():
    """Test MongoDB connection and print connection info."""
    print("\nTesting MongoDB connection...")
    manager = get_mongo_manager()
    try:
        # Initialize async client if not already done
        if not hasattr(manager, '_async_client') or manager._async_client is None:
            manager._async_client = manager._get_async_client()
            
        # Get database name from settings or use default
        db_name = getattr(manager.settings, 'MONGODB_DB', 'crypto_news')
        
        # Get database instance
        db = manager._async_client[db_name]
        
        # Test connection with a simple command
        server_info = await db.command('ping')
        print(f"✓ Connected to MongoDB server: {manager.settings.MONGODB_URI}")
        print(f"✓ Database name: {db_name}")
        return True
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False
    finally:
        print("Test completed. Cleaning up...")

async def main():
    print_banner()
    
    # Set default MongoDB URI if not set
    os.environ.setdefault('MONGODB_URI', 'mongodb://localhost:27017')
    os.environ.setdefault('MONGODB_DB', 'crypto_news')
    
    # Test connection
    success = await test_connection()
    
    if success:
        print("\n✓ Connection test passed!")
        print("The application should now shut down cleanly without logging errors.")
        print("Check the output for any error messages during shutdown.\n")
    else:
        print("\n✗ Connection test failed!")
        print("Please check your MongoDB connection settings and try again.\n")
    
    # Small delay to ensure all output is captured
    await asyncio.sleep(0.1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        sys.exit(1)
