"""
Test script to verify MongoDB connection.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("mongodb_test")

# Add the project root to the Python path
project_root = Path(
    __file__
).parent.parent  # Go up one more level to get to the project root
sys.path.insert(0, str(project_root))

# Import after path setup
from crypto_news_aggregator.db.mongodb import mongo_manager
from crypto_news_aggregator.core.config import get_settings


async def test_mongodb_connection():
    """Test MongoDB connection and basic operations."""
    settings = get_settings()

    # Log the MongoDB URI (masking the password for security)
    masked_uri = ""
    if settings.MONGODB_URI:
        parts = settings.MONGODB_URI.split("//")
        if len(parts) > 1:
            masked_uri = f"{parts[0]}//****:****@{'@'.join(parts[1:])}"

    logger.info("=== Testing MongoDB Connection ===")
    logger.info(f"MongoDB URI: {masked_uri}")
    logger.info(f"Database name: {settings.MONGODB_NAME}")

    if not settings.MONGODB_URI:
        logger.error("MONGODB_URI is not set in the configuration")
        return False

    try:
        # Test connection
        logger.info("Testing connection...")
        is_connected = await mongo_manager.ping()

        if not is_connected:
            logger.error("Failed to connect to MongoDB")
            return False

        logger.info("✅ Successfully connected to MongoDB")

        # Test basic operations
        test_collection = await mongo_manager.get_async_collection("test_connection")

        # Insert a test document
        test_doc = {"test": "connection_test", "status": "success"}

        logger.info("Inserting test document...")
        result = await test_collection.insert_one(test_doc)
        logger.info(f"✅ Inserted document with ID: {result.inserted_id}")

        # Retrieve the document
        logger.info("Retrieving test document...")
        found_doc = await test_collection.find_one({"_id": result.inserted_id})

        if found_doc:
            logger.info(f"✅ Retrieved document: {found_doc}")
        else:
            logger.error("❌ Failed to retrieve test document")
            return False

        # Clean up
        logger.info("Cleaning up test document...")
        await test_collection.delete_one({"_id": result.inserted_id})
        logger.info("✅ Cleanup complete")

        return True

    except Exception as e:
        logger.error(f"❌ MongoDB test failed: {str(e)}")
        import traceback

        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    logger.info("Starting MongoDB connection test...")
    success = asyncio.run(test_mongodb_connection())

    if success:
        logger.info("✅ All MongoDB tests passed!")
    else:
        logger.error("❌ MongoDB tests failed. See logs above for details.")

    # Clean up the MongoDB client (async)
    try:
        asyncio.run(mongo_manager.aclose())
        logger.info("MongoDB client closed")
    except Exception as e:
        logger.warning(f"Error closing MongoDB client: {e}")
