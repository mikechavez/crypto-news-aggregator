#!/usr/bin/env python3
"""
Simple MongoDB connection test script with pytest-asyncio support.
"""
import asyncio
import os
import sys
import pytest
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("mongodb_test")

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, os.path.join(project_root, "src"))

# Use pytest-asyncio for async test support
pytestmark = pytest.mark.asyncio


async def test_mongodb_connection():
    """Test MongoDB connection with direct client using pytest-asyncio."""
    from motor.motor_asyncio import AsyncIOMotorClient

    # Default MongoDB connection string
    mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGODB_NAME", "test_news_aggregator")

    logger.info(f"Testing MongoDB connection to: {mongo_uri}")
    logger.info(f"Database: {db_name}")

    # Create a new client and connect to the server
    client = AsyncIOMotorClient(
        mongo_uri,
        serverSelectionTimeoutMS=5000,  # 5 second timeout
        connectTimeoutMS=10000,  # 10 second connection timeout
        socketTimeoutMS=30000,  # 30 second socket timeout
    )

    try:
        # Test the connection
        logger.info("Pinging MongoDB...")
        await client.admin.command("ping")
        logger.info("✅ Successfully connected to MongoDB")

        # Get database and list collections
        db = client[db_name]
        collections = await db.list_collection_names()
        logger.info(f"✅ Collections in database '{db_name}': {collections}")

        # Test basic CRUD operations
        test_collection = db["test_connection"]

        # Insert a test document
        logger.info("Inserting test document...")
        result = await test_collection.insert_one(
            {"test": "connection", "status": "success"}
        )
        logger.info(f"✅ Inserted document with ID: {result.inserted_id}")

        # Find the document
        doc = await test_collection.find_one({"_id": result.inserted_id})
        logger.info(f"✅ Found document: {doc}")

        # Clean up
        logger.info("Cleaning up...")
        await test_collection.drop()

    except Exception as e:
        logger.error(f"❌ Failed to connect to MongoDB: {e}")
        raise
    finally:
        # Clean up
        client.close()
        logger.info("✅ Closed MongoDB connection")


# This allows the script to be run directly for manual testing
if __name__ == "__main__":
    logger.info("Starting MongoDB connection test...")

    # Create a new event loop for the test
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        success = loop.run_until_complete(test_mongodb_connection())
        if success:
            logger.info("✅ MongoDB connection test completed successfully")
            sys.exit(0)
        else:
            logger.error("❌ MongoDB connection test failed")
            sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Error during MongoDB connection test: {e}")
        sys.exit(1)
    finally:
        loop.close()
