#!/usr/bin/env python3
"""
Simple MongoDB connection test script.
"""
import asyncio
import os
import sys
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('mongodb_test')

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, os.path.join(project_root, 'src'))

async def test_mongodb_connection():
    """Test MongoDB connection with direct client."""
    from motor.motor_asyncio import AsyncIOMotorClient
    
    # Default MongoDB connection string
    mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGODB_NAME", "test_news_aggregator")
    
    logger.info(f"Testing MongoDB connection to: {mongo_uri}")
    logger.info(f"Database: {db_name}")
    
    try:
        # Create a new client and connect to the server
        client = AsyncIOMotorClient(
            mongo_uri,
            serverSelectionTimeoutMS=5000,  # 5 second timeout
            connectTimeoutMS=10000,         # 10 second connection timeout
            socketTimeoutMS=30000           # 30 second socket timeout
        )
        
        # Test the connection
        logger.info("Pinging MongoDB...")
        await client.admin.command('ping')
        logger.info("✅ Successfully connected to MongoDB")
        
        # Get database and list collections
        db = client[db_name]
        collections = await db.list_collection_names()
        logger.info(f"✅ Collections in database '{db_name}': {collections}")
        
        # Test basic CRUD operations
        test_collection = db["test_connection"]
        
        # Insert a test document
        logger.info("Inserting test document...")
        result = await test_collection.insert_one({"test": "connection", "status": "success"})
        logger.info(f"✅ Inserted document with ID: {result.inserted_id}")
        
        # Find the document
        doc = await test_collection.find_one({"_id": result.inserted_id})
        logger.info(f"✅ Found document: {doc}")
        
        # Clean up
        logger.info("Cleaning up...")
        await test_collection.drop()
        logger.info("✅ Cleanup complete")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ MongoDB test failed: {str(e)}")
        logger.error("Please make sure MongoDB is running and accessible at the specified URI.")
        logger.error("You can start MongoDB with: brew services start mongodb-community")
        return False
    finally:
        if 'client' in locals():
            client.close()
            logger.info("✅ MongoDB connection closed")

if __name__ == "__main__":
    logger.info("Starting MongoDB connection test...")
    success = asyncio.run(test_mongodb_connection())
    
    if success:
        logger.info("✅ All MongoDB tests passed!")
        sys.exit(0)
    else:
        logger.error("❌ MongoDB tests failed. See logs above for details.")
        sys.exit(1)
