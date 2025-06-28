"""
MongoDB database connection and utilities.
"""
from typing import Optional, Dict, Any, List, TypeVar, Type
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from functools import lru_cache
import logging

from ..core.config import get_settings

logger = logging.getLogger(__name__)

# Type variables for better type hints
T = TypeVar('T', bound='MongoManager')

class MongoManager:
    """
    MongoDB connection manager that provides both synchronous and asynchronous clients.
    """
    _instance = None
    _sync_client: Optional[MongoClient] = None
    _async_client: Optional[AsyncIOMotorClient] = None
    
    def __new__(cls: Type[T]) -> T:
        """Singleton pattern to ensure only one instance exists."""
        if cls._instance is None:
            cls._instance = super(MongoManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the MongoDB connection manager."""
        if not hasattr(self, '_initialized') or not self._initialized:
            self.settings = get_settings()
            self._initialized = True
    
    @property
    def sync_client(self) -> MongoClient:
        """Get a synchronous MongoDB client (creates if it doesn't exist)."""
        if self._sync_client is None:
            self._sync_client = MongoClient(
                self.settings.MONGODB_URI,
                serverSelectionTimeoutMS=5000,  # 5 second timeout
                connectTimeoutMS=30000,        # 30 second connection timeout
                socketTimeoutMS=30000,          # 30 second socket timeout
                maxPoolSize=100,                # Maximum number of connections
                minPoolSize=10,                 # Minimum number of connections
                retryWrites=True,
                retryReads=True
            )
            logger.info("Created new synchronous MongoDB client")
        return self._sync_client
    
    @property
    def async_client(self) -> AsyncIOMotorClient:
        """Get an asynchronous MongoDB client (creates if it doesn't exist)."""
        if self._async_client is None:
            self._async_client = AsyncIOMotorClient(
                self.settings.MONGODB_URI,
                serverSelectionTimeoutMS=5000,  # 5 second timeout
                connectTimeoutMS=30000,        # 30 second connection timeout
                socketTimeoutMS=30000,          # 30 second socket timeout
                maxPoolSize=100,                # Maximum number of connections
                minPoolSize=10,                 # Minimum number of connections
                retryWrites=True,
                retryReads=True
            )
            logger.info("Created new asynchronous MongoDB client")
        return self._async_client
    
    def get_database(self, name: Optional[str] = None) -> Database:
        """Get a synchronous database instance."""
        db_name = name or self.settings.MONGODB_NAME
        return self.sync_client[db_name]
    
    async def get_async_database(self, name: Optional[str] = None) -> AsyncIOMotorDatabase:
        """Get an asynchronous database instance."""
        db_name = name or self.settings.MONGODB_NAME
        return self.async_client[db_name]
    
    def get_collection(self, name: str, db_name: Optional[str] = None) -> Collection:
        """Get a synchronous collection instance."""
        return self.get_database(db_name)[name]
    
    async def get_async_collection(self, name: str, db_name: Optional[str] = None) -> AsyncIOMotorCollection:
        """Get an asynchronous collection instance."""
        db = await self.get_async_database(db_name)
        return db[name]
    
    async def ping(self) -> bool:
        """Ping the MongoDB server to check connectivity."""
        try:
            await self.async_client.admin.command('ping')
            logger.info("Successfully connected to MongoDB")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            return False
    
    def close(self):
        """Close all MongoDB connections."""
        if self._sync_client:
            self._sync_client.close()
            self._sync_client = None
            logger.info("Closed synchronous MongoDB client")
        
        # Note: Motor clients don't need explicit closing in most cases
        self._async_client = None
        logger.info("Cleaned up asynchronous MongoDB client")

# Singleton instance
mongo_manager = MongoManager()

# Helper functions for dependency injection
async def get_mongodb() -> AsyncIOMotorDatabase:
    """Dependency to get the MongoDB database instance."""
    return await mongo_manager.get_async_database()

async def get_collection(collection_name: str) -> AsyncIOMotorCollection:
    """Dependency to get a MongoDB collection."""
    return await mongo_manager.get_async_collection(collection_name)
