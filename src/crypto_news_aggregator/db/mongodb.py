"""
MongoDB database connection and utilities.
"""
import asyncio
import logging
import threading
from typing import Optional, Dict, Any, List, TypeVar, Type, Union, TypeVar, Generic, Callable, Awaitable, Any, Coroutine
from pymongo import MongoClient, IndexModel, TEXT, ASCENDING, DESCENDING
from pymongo.database import Database
from pymongo.collection import Collection
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
import certifi
from functools import lru_cache, wraps
import logging
import asyncio
from contextlib import asynccontextmanager
from bson import ObjectId
from pydantic import BaseModel, Field


from pydantic_core import core_schema
from pydantic import GetCoreSchemaHandler

class PyObjectId(str):
    """Custom type for MongoDB ObjectId that works with Pydantic v2."""

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,
        _handler: GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:
        return core_schema.json_or_python_schema(
            json_schema=core_schema.str_schema(),
            python_schema=core_schema.union_schema(
                [
                    core_schema.is_instance_schema(ObjectId),
                    core_schema.chain_schema(
                        [
                            core_schema.str_schema(),
                            core_schema.no_info_plain_validator_function(cls.validate),
                        ]
                    ),
                ]
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(lambda x: str(x)),
        )

    @classmethod
    def validate(cls, v: str) -> ObjectId:
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)


# Add PyObjectId to the module's __all__ for better import handling
__all__ = ["PyObjectId"]

from ..core.config import get_settings


# Index definitions
ARTICLE_INDEXES = [
    {
        "keys": [("url", 1)],
        "name": "url_unique",
        "unique": True
    },
    {
        "keys": [("title", "text"), ("content", "text"), ("description", "text")],
        "name": "full_text_search",
        "default_language": "english",
        "weights": {
            "title": 10,
            "description": 5,
            "content": 1
        }
    },
    {
        "keys": [("published_at", -1)],
        "name": "published_at_desc"
    },
    {
        "keys": [("source.id", 1)],
        "name": "source_id"
    },
    {
        "keys": [("sentiment.score", 1)],
        "name": "sentiment_score"
    },
    {
        "keys": [("keywords", 1)],
        "name": "keywords_idx"
    },
    {
        "keys": [("is_duplicate", 1)],
        "name": "is_duplicate"
    },
    {
        "keys": [("processed", 1)],
        "name": "processed_flag"
    }
]

ALERT_INDEXES = [
    {
        "keys": [("user_id", 1), ("is_active", 1)],
        "name": "user_active_alerts",
        "background": True
    },
    {
        "keys": [("crypto_id", 1), ("is_active", 1), ("last_triggered", -1)],
        "name": "crypto_active_alerts",
        "background": True
    },
    {
        "keys": [("created_at", 1)],
        "name": "alert_expiration",
        "expireAfterSeconds": 90 * 24 * 60 * 60,  # 90 days
        "background": True
    }
]

TWEET_INDEXES = [
    {
        "keys": [("tweet_id", 1)],
        "name": "tweet_id_unique",
        "unique": True
    },
    {
        "keys": [("author.username", 1)],
        "name": "author_username"
    },
    {
        "keys": [("tweet_created_at", -1)],
        "name": "tweet_created_at_desc"
    },
    {
        "keys": [("keywords", 1)],
        "name": "tweet_keywords_idx"
    },
    {
        "keys": [("relevance_score", -1)],
        "name": "relevance_score_desc"
    }
]

PRICE_HISTORY_INDEXES = [
    {
        "keys": [("cryptocurrency", 1), ("timestamp", -1)],
        "name": "crypto_timestamp_compound",
        "background": True
    },
    {
        "keys": [("timestamp", 1)],
        "name": "price_history_ttl",
        "expireAfterSeconds": 2592000,  # 30 days
        "background": True
    }
]


logger = logging.getLogger(__name__)

# Type variables for better type hints
T = TypeVar('T')
P = TypeVar('P')
R = TypeVar('R')

# Collection names
COLLECTION_ARTICLES = "articles"
COLLECTION_SOURCES = "sources"
COLLECTION_TRENDS = "trends"
COLLECTION_ALERTS = "alerts"
COLLECTION_PRICE_HISTORY = "price_history"
COLLECTION_TWEETS = "tweets"

# Database name
DB_NAME = "crypto_news"

def async_retry(retries: int = 3, delay: float = 1.0):
    """Decorator for retrying async functions with exponential backoff."""
    def decorator(func: Callable[..., Awaitable[R]]) -> Callable[..., Awaitable[R]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> R:
            last_exception = None
            for attempt in range(retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < retries - 1:
                        wait_time = delay * (2 ** attempt)  # Exponential backoff
                        logger.warning(
                            f"Attempt {attempt + 1}/{retries} failed. Retrying in {wait_time:.2f}s. Error: {str(e)}"
                        )
                        await asyncio.sleep(wait_time)
            raise last_exception or Exception("Unknown error occurred in async_retry")
        return wrapper
    return decorator


class MongoManager:
    """
    MongoDB connection manager that provides both synchronous and asynchronous clients
    with connection pooling, retry logic, and index management.
    
    This class uses lazy initialization and is thread-safe.
    """
    _instance = None
    _instance_lock = threading.Lock()  # For thread-safe singleton creation
    _async_lock = asyncio.Lock()      # For async operations
    _initialized = False
    _indexes_created = False
    
    def __new__(cls: Type['MongoManager']) -> 'MongoManager':
        """Thread-safe singleton pattern."""
        if cls._instance is None:
            with cls._instance_lock:  # Use threading.Lock for singleton creation
                if cls._instance is None:
                    cls._instance = super(MongoManager, cls).__new__(cls)
                    # Initialize instance variables
                    cls._instance.settings = None
                    cls._instance._async_client = None
                    cls._instance._sync_client = None
                    cls._instance._initialized = False
                    logger.info("MongoDB Manager instance created")
        return cls._instance
    
    def __init__(self):
        """Initialize the MongoDB connection manager."""
        pass
        
    def _ensure_settings(self):
        # Always fetch fresh settings to support test overrides and runtime config
        self.settings = get_settings()

    async def initialize(self, force_reconnect: bool = False) -> bool:
        """Initialize the MongoDB connection asynchronously.
        
        This method must be called before any database operations are performed.
        It's recommended to call this during application startup.
        
        Args:
            force_reconnect: If True, force reconnection even if already initialized.
            
        Returns:
            bool: True if initialization was successful, False otherwise.
        """
        async with self._async_lock:
            if self._initialized and not force_reconnect:
                return True
            
            try:
                self._ensure_settings()
                if not self.settings.MONGODB_URI:
                    logger.error("MongoDB URI is not configured.")
                    return False

                logger.info(f"Initializing async MongoDB connection to {self._get_masked_uri()}")
                
                self._async_client = AsyncIOMotorClient(
                    self.settings.MONGODB_URI,
                    maxPoolSize=self.settings.MONGODB_MAX_POOL_SIZE,
                    minPoolSize=self.settings.MONGODB_MIN_POOL_SIZE,
                    tlsCAFile=certifi.where(),
                )
                
                await self._async_client.admin.command('ping')
                
                self._initialized = True
                logger.info("Async MongoDB connection initialized successfully.")
                return True

            except Exception as e:
                logger.error(f"Failed to initialize async MongoDB connection: {e}")
                self._initialized = False
                return False

    async def get_async_client(self) -> AsyncIOMotorClient:
        """Get the async MongoDB client.
        
        Returns:
            AsyncIOMotorClient: The MongoDB async client instance.
            
        Raises:
            RuntimeError: If the client cannot be initialized.
        """
        if not self._initialized or self._async_client is None:
            raise RuntimeError(
                "Async client is not initialized. Call `initialize()` first."
            )
        return self._async_client
    
    @property
    def sync_client(self) -> MongoClient:
        """Get a synchronous MongoDB client with connection pooling."""
        if self._sync_client is None:
            with self._instance_lock:
                if self._sync_client is None:
                    self._ensure_settings()
                    if not self.settings.MONGODB_URI:
                        raise ValueError("MongoDB URI is not configured")
                    
                    logger.info(f"Creating new sync MongoDB client for URI: {self._get_masked_uri()}")
                    self._sync_client = MongoClient(
                        self.settings.MONGODB_URI,
                        maxPoolSize=self.settings.MONGODB_MAX_POOL_SIZE,
                        minPoolSize=self.settings.MONGODB_MIN_POOL_SIZE,
                        waitQueueTimeoutMS=10000,
                        waitQueueMultiple=10,
                        connect=False,
                        appname="crypto-news-aggregator",
                        tlsCAFile=certifi.where(),
                    )
                    logger.info("Created new synchronous MongoDB client")
        return self._sync_client
    
    def _get_masked_uri(self) -> str:
        """Get a masked version of the MongoDB URI for logging."""
        if not self.settings.MONGODB_URI:
            return ""
        parts = self.settings.MONGODB_URI.split("//")
        if len(parts) > 1:
            return f"{parts[0]}//****:****@{'@'.join(parts[1:])}"
        return self.settings.MONGODB_URI

    def get_database(self, db_name: Optional[str] = None) -> Database:
        """Get a synchronous database instance."""
        db_name = db_name or DB_NAME
        return self.sync_client[db_name]
    
    async def get_async_database(self, db_name: Optional[str] = None) -> AsyncIOMotorDatabase:
        """Get an asynchronous database instance with logging."""
        db_name = db_name or DB_NAME
        logger.debug("[MongoManager] Getting async database: %s", db_name)
        try:
            db = self._async_client[db_name]
            logger.debug("[MongoManager] Successfully got database: %s", db_name)
            return db
        except Exception as e:
            logger.error("[MongoManager] Error getting database %s: %s", db_name, e, exc_info=True)
            raise
    
    def get_collection(self, collection_name: str, db_name: Optional[str] = None) -> Collection:
        """Get a synchronous collection instance."""
        return self.get_database(db_name)[collection_name]
    
    async def get_async_collection(
        self, collection_name: str, db_name: Optional[str] = None
    ) -> AsyncIOMotorCollection:
        """Get an asynchronous collection instance with logging."""
        logger.debug("[MongoManager] Getting async collection: %s", collection_name)
        try:
            db = await self.get_async_database(db_name)
            collection = db[collection_name]
            logger.debug("[MongoManager] Successfully got collection: %s", collection_name)
            return collection
        except Exception as e:
            logger.error("[MongoManager] Error getting collection %s: %s", collection_name, e, exc_info=True)
            raise
    
    async def initialize_indexes(self, force_recreate: bool = False):
        """Create indexes for all collections if they don't exist."""
        if self._indexes_created and not force_recreate:
            return
            
        logger.info("Initializing MongoDB indexes...")
        
        # Create article indexes
        articles_col = await self.get_async_collection(COLLECTION_ARTICLES)
        
        # Create alerts collection indexes
        alerts_col = await self.get_async_collection(COLLECTION_ALERTS)
        
        # Create price history collection indexes
        price_history_col = await self.get_async_collection(COLLECTION_PRICE_HISTORY)
        
        # Drop existing indexes if force_recreate is True
        if force_recreate:
            await articles_col.drop_indexes()
            await alerts_col.drop_indexes()
            await price_history_col.drop_indexes()
            await self.get_async_collection(COLLECTION_TWEETS).drop_indexes()
        
        # Create indexes for articles collection
        for index_info in ARTICLE_INDEXES:
            index_options = index_info.copy()
            keys = index_options.pop("keys")
            if not await self._has_index(articles_col, index_options.get("name")):
                await articles_col.create_index(keys, **index_options)
        
        # Create indexes for alerts collection
        for index_info in ALERT_INDEXES:
            index_options = index_info.copy()
            keys = index_options.pop("keys")
            if not await self._has_index(alerts_col, index_options.get("name")):
                await alerts_col.create_index(keys, **index_options)
        
        # Create indexes for price history collection
        price_history_col = await self.get_async_collection(COLLECTION_PRICE_HISTORY)
        for index_info in PRICE_HISTORY_INDEXES:
            index_options = index_info.copy()
            keys = index_options.pop("keys")
            if not await self._has_index(price_history_col, index_options.get("name")):
                await price_history_col.create_index(keys, **index_options)

        # Create indexes for tweets collection
        tweets_col = await self.get_async_collection(COLLECTION_TWEETS)
        for index_info in TWEET_INDEXES:
            index_options = index_info.copy()
            keys = index_options.pop("keys")
            if not await self._has_index(tweets_col, index_options.get("name")):
                await tweets_col.create_index(keys, **index_options)
        
        logger.info("MongoDB indexes initialized successfully")
        self._indexes_created = True
    
    async def _has_index(self, collection: AsyncIOMotorCollection, index_name: str) -> bool:
        """Check if an index with the given name exists."""
        if not index_name:
            return False
            
        cursor = collection.list_indexes()
        async for index in cursor:
            if index["name"] == index_name:
                return True
        return False
    
    @asynccontextmanager
    async def get_session(self):
        """Async context manager for MongoDB transactions."""
        async with await self._async_client.start_session() as session:
            async with await session.start_transaction():
                try:
                    yield session
                    await session.commit_transaction()
                except Exception as e:
                    await session.abort_transaction()
                    logger.error(f"MongoDB transaction failed: {str(e)}")
                    raise
    
    @async_retry(retries=3, delay=1.0)
    async def find_one_with_retry(
        self, 
        collection_name: str,
        filter_dict: Dict[str, Any],
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Find one document with retry logic."""
        collection = await self.get_async_collection(collection_name)
        return await collection.find_one(filter_dict, **kwargs)
    
    @async_retry(retries=3, delay=1.0)
    async def insert_one_with_retry(
        self, 
        collection_name: str,
        document: Dict[str, Any],
        **kwargs
    ) -> Any:
        """Insert one document with retry logic."""
        collection = await self.get_async_collection(collection_name)
        result = await collection.insert_one(document, **kwargs)
        return result.inserted_id
    
    async def ping(self) -> bool:
        """Ping the MongoDB server to check connection.
        
        Returns:
            bool: True if the ping was successful, False otherwise.
        """
        if not self._initialized:
            logger.warning("MongoDB client not initialized, attempting to initialize...")
            return await self.initialize()
            
        try:
            client = await self.get_async_client()
            if client is None:
                logger.error("MongoDB client is None")
                return False
                
            await client.admin.command('ping')
            logger.info("MongoDB ping successful.")
            return True
            
        except Exception as e:
            logger.error(f"MongoDB ping failed: {str(e)}")
            logger.debug("Ping failure details:", exc_info=True)
            # Attempt to reinitialize the connection
            if self._initialized:  # Only try to reconnect if we were previously connected
                logger.info("Attempting to reconnect to MongoDB...")
                return await self.initialize(force_reconnect=True)
            return False
    
    async def aclose(self):
        """Asynchronously close all MongoDB connections."""
        if self._async_client:
            try:
                logger.debug("Closing MongoDB async client...")
                self._async_client.close()
                # Give the client a moment to close connections
                await asyncio.sleep(0.1)
                logger.info("Closed MongoDB async client")
            except Exception as e:
                logger.error(f"Error closing MongoDB async client: {e}")
            finally:
                self._async_client = None
                
    async def close(self):
        """Close the MongoDB connection.
        
        This method should be called when the application is shutting down
        or when you want to explicitly close the connection.
        """
        logger.info("Closing MongoDB connections...")
        
        # Close async client if it exists
        if hasattr(self, '_async_client') and self._async_client:
            try:
                self._async_client.close()
                logger.info("Closed async MongoDB connection")
            except Exception as e:
                logger.error(f"Error closing async MongoDB connection: {e}")
            finally:
                self._async_client = None
        
        # Close sync client if it exists
        if hasattr(self, '_sync_client') and self._sync_client:
            try:
                self._sync_client.close()
                logger.info("Closed sync MongoDB connection")
            except Exception as e:
                logger.error(f"Error closing sync MongoDB connection: {e}")
            finally:
                self._sync_client = None
                
        self._initialized = False

    def __del__(self):
        """Ensure connections are closed when the manager is destroyed."""
        # Try to close sync client if it exists
        if hasattr(self, '_sync_client') and self._sync_client:
            try:
                self._sync_client.close()
            except Exception as e:
                logger.warning(f"Error closing sync client in __del__: {e}")
        
        # Try to close async client if it exists
        if hasattr(self, '_async_client') and self._async_client:
            try:
                self._async_client.close()
            except Exception as e:
                logger.warning(f"Error closing async client in __del__: {e}")

# Initialize the global MongoDB manager instance
mongo_manager = MongoManager()

async def initialize_mongodb() -> bool:
    """Initialize the MongoDB connection and indexes.
    
    This function must be called explicitly during application startup.
    
    Returns:
        bool: True if initialization was successful, False otherwise.
    """
    try:
        # Initialize the MongoDB connection
        success = await mongo_manager.initialize()
        if not success:
            logger.error("Failed to initialize MongoDB connection")
            return False
            
        # Initialize indexes
        await ensure_indexes()
        
        return True
        
    except Exception as e:
        logger.error(f"Error initializing MongoDB: {e}")
        return False

# Helper functions for dependency injection
async def get_mongodb() -> AsyncIOMotorDatabase:
    """Dependency to get the async MongoDB database instance."""
    db = await mongo_manager.get_async_database()
    return db

async def get_collection(collection_name: str) -> AsyncIOMotorCollection:
    """Dependency to get an async MongoDB collection."""
    return await mongo_manager.get_async_collection(collection_name)

def get_sync_database() -> Database:
    """Dependency to get the sync MongoDB database instance."""
    return mongo_manager.get_database()

async def ensure_indexes():
    """Ensure MongoDB indexes are created on application startup."""
    await mongo_manager.initialize_indexes()

# Add event handler to ensure indexes are created on application startup
import atexit
import asyncio
from contextlib import asynccontextmanager

# Global flag to track if we're in a FastAPI lifespan context
_in_fastapi_lifespan = False

async def _on_startup():
    """Initialize MongoDB indexes on application startup."""
    try:
        await ensure_indexes()
        logger.info("MongoDB indexes verified/created successfully")
    except Exception as e:
        logger.error(f"Failed to initialize MongoDB indexes: {str(e)}")
        raise

# Cleanup on exit
async def _on_shutdown():
    """Clean up MongoDB connections on application shutdown."""
    try:
        if mongo_manager._async_client is not None:
            await mongo_manager.aclose()
            # Use print instead of logger during shutdown to avoid logging after logger shutdown
            print("MongoDB connections closed successfully")
        else:
            print("No async MongoDB client to close")
    except Exception as e:
        # Use print instead of logger during shutdown
        print(f"Error during MongoDB shutdown: {e}")
        raise

def get_lifespan():
    """
    Get a FastAPI lifespan context manager for MongoDB connection management.
    
    Usage in FastAPI:
    app = FastAPI(lifespan=get_lifespan())
    """
    from contextlib import asynccontextmanager
    
    @asynccontextmanager
    async def lifespan(app):
        global _in_fastapi_lifespan
        _in_fastapi_lifespan = True
        
        # Initialize indexes on startup
        await _on_startup()
        
        # Yield control to the application
        yield
        
        # Clean up on shutdown
        await _on_shutdown()
        _in_fastapi_lifespan = False
    
    return lifespan

