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
from functools import lru_cache, wraps
import logging
import asyncio
from contextlib import asynccontextmanager
from bson import ObjectId
from pydantic import BaseModel, Field


class PyObjectId(ObjectId):
    """Custom type for MongoDB ObjectId that works with Pydantic v2."""
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string", format="objectid")


# Add PyObjectId to the module's __all__ for better import handling
__all__ = ["PyObjectId"]

from ..core.config import get_settings
from .mongodb_models import ARTICLE_INDEXES, ALERT_INDEXES

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
                    cls._instance.settings = get_settings()
                    cls._instance._async_client = None
                    cls._instance._sync_client = None  # Initialize sync client
                    cls._instance._initialized = False
                    logger.info("MongoDB Manager instance created")
        return cls._instance
    
    def __init__(self):
        """Initialize the MongoDB connection manager."""
        # All initialization is handled in __new__
        pass
        
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
                logger.debug("MongoDB already initialized")
                return True
                
            logger.info("Initializing MongoDB connection...")
            
            # Close existing connection if reinitializing
            if self._async_client is not None:
                await self.close()
            
            # Ensure we have a valid MongoDB URI
            if not self.settings.MONGODB_URI:
                self.settings.MONGODB_URI = "mongodb://localhost:27017"
                logger.warning("MongoDB URI not set, using default: mongodb://localhost:27017")
            
            try:
                # Create a new async client with connection pooling
                self._async_client = AsyncIOMotorClient(
                    self.settings.MONGODB_URI,
                    maxPoolSize=10,  # Adjust based on your needs
                    minPoolSize=1,
                    connectTimeoutMS=5000,  # 5 seconds
                    serverSelectionTimeoutMS=5000,
                    socketTimeoutMS=30000,  # 30 seconds
                )
                
                # Test the connection
                await self._async_client.admin.command('ping')
                self._initialized = True
                logger.info("✅ MongoDB connection established successfully")
                return True
                
            except Exception as e:
                self._async_client = None
                self._initialized = False
                logger.error(f"❌ Failed to initialize MongoDB: {str(e)}")
                logger.debug("Stack trace: %s", str(e))
                return False

    async def get_async_client(self) -> AsyncIOMotorClient:
        """Get the async MongoDB client.
        
        Returns:
            AsyncIOMotorClient: The MongoDB async client instance.
            
        Raises:
            RuntimeError: If the client cannot be initialized.
        """
        if not self._initialized:
            async with self._async_lock:
                if not self._initialized:  # Double-check after acquiring lock
                    logger.warning("MongoDB not initialized. Initializing now...")
                    if not await self.initialize():
                        raise RuntimeError("Failed to initialize MongoDB client")
        if self._async_client is None:
            raise RuntimeError("MongoDB client is not available")
            
        return self._async_client
    
    @property
    def sync_client(self) -> MongoClient:
        """Get a synchronous MongoDB client with connection pooling."""
        if not hasattr(self, '_sync_client') or self._sync_client is None:
            if not self.settings.MONGODB_URI:
                raise ValueError("MongoDB URI is not configured")
                
            logger.info(f"Creating new sync MongoDB client with URI: {self._get_masked_uri()}")
            self._sync_client = MongoClient(
                self.settings.MONGODB_URI,
                serverSelectionTimeoutMS=5000,  # 5 second timeout
                connectTimeoutMS=30000,         # 30 second connection timeout
                socketTimeoutMS=30000,          # 30 second socket timeout
                maxPoolSize=100,                # Maximum number of connections
                minPoolSize=10,                 # Minimum number of connections
                retryWrites=True,               # Enable retryable writes
                retryReads=True,                # Enable retryable reads
                maxIdleTimeMS=60000,            # Close idle connections after 60s
                waitQueueTimeoutMS=10000,        # Max wait time for a connection
                waitQueueMultiple=10,            # Max number of queued connection requests
                connect=False,                   # Don't connect immediately - let it connect on first operation
                appname="crypto-news-aggregator" # Identify the application
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
        
        # Create indexes for articles collection
        for index in ARTICLE_INDEXES:
            keys = index["keys"]
            index_name = "_".join([f"{k[0]}_{k[1]}" for k in keys])
            
            # Handle TTL indexes
            if "expireAfterSeconds" in index:
                if not await self._has_index(articles_col, index_name):
                    await articles_col.create_index(
                        keys,
                        name=index_name,
                        expireAfterSeconds=index["expireAfterSeconds"]
                    )
            # Handle regular indexes
            else:
                if not await self._has_index(articles_col, index_name):
                    await articles_col.create_index(
                        keys,
                        name=index_name,
                        background=True
                    )
        
        # Create indexes for alerts collection
        for index in ALERT_INDEXES:
            if isinstance(index, dict):
                # Handle single field index
                field = list(index.keys())[0]
                direction = index[field]
                index_name = f"{field}_{direction}"
                keys = [(field, direction)]
            else:
                # Handle compound index or special index
                if isinstance(index[0], str):
                    # Special index like "text"
                    index_name = f"{index[0]}_1"
                    keys = [(index[0], 1)]
                else:
                    # Compound index
                    keys = index
                    index_name = "_".join([f"{k[0]}_{k[1]}" for k in keys])
            
            # Handle TTL indexes
            if isinstance(index, dict) and "expireAfterSeconds" in index:
                if not await self._has_index(alerts_col, index_name):
                    await alerts_col.create_index(
                        keys,
                        name=index_name,
                        expireAfterSeconds=index["expireAfterSeconds"]
                    )
            # Handle regular indexes
            else:
                if not await self._has_index(alerts_col, index_name):
                    await alerts_col.create_index(
                        keys,
                        name=index_name,
                        background=True
                    )
        
        # Create indexes for price history collection
        for index in PRICE_HISTORY_INDEXES:
            if isinstance(index[0], tuple):
                # Regular compound index
                keys = index
                index_name = "_".join([f"{k[0]}_{k[1]}" for k in keys])
                
                # Check if this is a TTL index
                is_ttl = any(isinstance(k, dict) and "expireAfterSeconds" in k for k in keys)
                
                if not await self._has_index(price_history_col, index_name):
                    if is_ttl:
                        # Extract TTL config and filter out non-key parts
                        ttl_config = next(k for k in keys if isinstance(k, dict))
                        clean_keys = [k for k in keys if not isinstance(k, dict)]
                        await price_history_col.create_index(
                            clean_keys,
                            name=index_name,
                            expireAfterSeconds=ttl_config["expireAfterSeconds"]
                        )
                    else:
                        await price_history_col.create_index(
                            keys,
                            name=index_name,
                            background=True
                        )
        
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
                await self._async_client.wait_closed()
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
                # Create a new event loop if one doesn't exist
                loop = None
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                # Run the close in the event loop
                if loop.is_running():
                    # If loop is running, schedule the close
                    asyncio.create_task(self._async_client.close())
                else:
                    # Otherwise run it directly
                    loop.run_until_complete(self._async_client.close())
                    
            except Exception as e:
                logger.warning(f"Error in __del__: {e}")

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

def cleanup():
    """Safely clean up resources on application exit."""
    try:
        # Get or create an event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Schedule the cleanup to run when the loop is idle
                asyncio.ensure_future(_cleanup_async(), loop=loop)
                return
        except RuntimeError:
            # No running event loop, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Run the cleanup in the current loop
        loop.run_until_complete(_cleanup_async())
        
        # Close the loop if we created it
        if loop.is_running():
            loop.close()
            
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")

# Register the cleanup function
atexit.register(cleanup)

async def _cleanup_async():
    """Asynchronously clean up resources on application exit."""
    try:
        # Clean up MongoDB connections
        await _on_shutdown()
        logger.info("MongoDB cleanup completed successfully")
    except Exception as e:
        logger.error(f"Error during async cleanup: {e}")
