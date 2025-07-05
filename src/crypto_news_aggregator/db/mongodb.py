"""
MongoDB database connection and utilities.
"""
from typing import Optional, Dict, Any, List, TypeVar, Type, Union, TypeVar, Generic, Callable, Awaitable, Any, Coroutine
from pymongo import MongoClient, IndexModel, TEXT, ASCENDING, DESCENDING
from pymongo.database import Database
from pymongo.collection import Collection
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from functools import lru_cache, wraps
import logging
import asyncio
from contextlib import asynccontextmanager

from ..core.config import get_settings
from .mongodb_models import ARTICLE_INDEXES

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
    """
    _instance = None
    _sync_client: Optional[MongoClient] = None
    _async_client: Optional[AsyncIOMotorClient] = None
    _initialized = False
    _indexes_created = False
    
    def __new__(cls: Type['MongoManager']) -> 'MongoManager':
        """Singleton pattern to ensure only one instance exists."""
        if cls._instance is None:
            cls._instance = super(MongoManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the MongoDB connection manager."""
        if not self._initialized:
            self.settings = get_settings()
            # Ensure we have a valid MongoDB URI
            if not self.settings.MONGODB_URI:
                self.settings.MONGODB_URI = "mongodb://localhost:27017"
                logger.warning("MongoDB URI not set, using default: mongodb://localhost:27017")
            self._initialized = True
    
    @property
    def sync_client(self) -> MongoClient:
        """Get a synchronous MongoDB client with connection pooling."""
        if self._sync_client is None:
            if not self.settings.MONGODB_URI:
                raise ValueError("MongoDB URI is not configured")
            logger.info(f"Creating new sync MongoDB client with URI: {self._get_masked_uri()}")
            self._sync_client = MongoClient(
                self.settings.MONGODB_URI,
                serverSelectionTimeoutMS=5000,  # 5 second timeout
                connectTimeoutMS=30000,        # 30 second connection timeout
                socketTimeoutMS=30000,          # 30 second socket timeout
                maxPoolSize=100,                # Maximum number of connections
                minPoolSize=10,                 # Minimum number of connections
                retryWrites=True,              # Enable retryable writes
                retryReads=True,               # Enable retryable reads
                maxIdleTimeMS=60000,           # Close idle connections after 60s
                waitQueueTimeoutMS=10000,       # Max wait time for a connection
                waitQueueMultiple=10,           # Max number of queued connection requests
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

    @property
    def async_client(self) -> AsyncIOMotorClient:
        """Get an asynchronous MongoDB client with connection pooling."""
        if self._async_client is None:
            if not self.settings.MONGODB_URI:
                raise ValueError("MongoDB URI is not configured")
            logger.info(f"Creating new async MongoDB client with URI: {self._get_masked_uri()}")
            self._async_client = AsyncIOMotorClient(
                self.settings.MONGODB_URI,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=30000,
                socketTimeoutMS=30000,
                maxPoolSize=100,
                minPoolSize=10,
                retryWrites=True,
                retryReads=True,
                maxIdleTimeMS=60000,
                waitQueueTimeoutMS=10000,
                waitQueueMultiple=10,
                appname="crypto-news-aggregator-async"
            )
        return self._async_client
    
    def get_database(self, db_name: Optional[str] = None) -> Database:
        """Get a synchronous database instance."""
        db_name = db_name or DB_NAME
        return self.sync_client[db_name]
    
    async def get_async_database(self, db_name: Optional[str] = None) -> AsyncIOMotorDatabase:
        """Get an asynchronous database instance."""
        db_name = db_name or DB_NAME
        return self.async_client[db_name]
    
    def get_collection(self, collection_name: str, db_name: Optional[str] = None) -> Collection:
        """Get a synchronous collection instance."""
        return self.get_database(db_name)[collection_name]
    
    async def get_async_collection(
        self, collection_name: str, db_name: Optional[str] = None
    ) -> AsyncIOMotorCollection:
        """Get an asynchronous collection instance."""
        db = await self.get_async_database(db_name)
        return db[collection_name]
    
    async def initialize_indexes(self, force_recreate: bool = False):
        """Create indexes for all collections if they don't exist."""
        if self._indexes_created and not force_recreate:
            return
            
        logger.info("Initializing MongoDB indexes...")
        
        # Create article indexes
        articles_col = await self.get_async_collection(COLLECTION_ARTICLES)
        
        # Create alerts collection indexes
        alerts_col = await self.get_async_collection(COLLECTION_ALERTS)
        
        # Drop existing indexes if force_recreate is True
        if force_recreate:
            await articles_col.drop_indexes()
            await alerts_col.drop_indexes()
        
        # Create article indexes
        for index in ARTICLE_INDEXES:
            keys = index["keys"]
            index_name = index.get("name")
            unique = index.get("unique", False)
            
            # Handle text indexes specially
            if any(isinstance(k, tuple) and k[1] == "text" for k in keys):
                if not await self._has_index(articles_col, index_name or "_text_"):
                    await articles_col.create_index(
                        [k for k in keys if isinstance(k, tuple) and k[1] == "text"],
                        name=index_name,
                        default_language=index.get("default_language", "english"),
                        weights=index.get("weights", {})
                    )
            # Handle regular indexes
            else:
                if not await self._has_index(articles_col, index_name):
                    await articles_col.create_index(
                        keys,
                        name=index_name,
                        unique=unique,
                        background=True
                    )
        
        # Create alert indexes
        for index in ALERT_INDEXES:
            keys = index["keys"]
            index_name = index["name"]
            
            # Handle TTL index
            if "expireAfterSeconds" in index:
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
        async with await self.async_client.start_session() as session:
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
        """Ping the MongoDB server to check connectivity."""
        try:
            await self.async_client.admin.command('ping')
            logger.info("Successfully connected to MongoDB")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            return False
    
    async def aclose(self):
        """Asynchronously close all MongoDB connections."""
        # Store references to clients to avoid race conditions
        sync_client = self._sync_client
        async_client = self._async_client
        
        # Clear instance variables early to prevent double-close
        self._sync_client = None
        self._async_client = None
        self._initialized = False
        self._indexes_created = False
        
        # Close sync client if it exists
        if sync_client is not None:
            try:
                sync_client.close()
                logger.debug("Successfully closed sync MongoDB client")
            except Exception as e:
                logger.warning(f"Error closing sync MongoDB client: {e}", exc_info=True)
        
        # Close async client if it exists and is not already closed
        if async_client is not None:
            try:
                # Check if the client is already closed or closing
                if hasattr(async_client, '_closed') and async_client._closed:
                    logger.debug("Async MongoDB client already closed")
                    return
                    
                # Attempt to close the client
                await async_client.close()
                logger.debug("Successfully closed async MongoDB client")
            except (TypeError, RuntimeError) as e:
                # Handle cases where the client is already closed or event loop is closed
                if "can't be used in 'await' expression" in str(e) or "Event loop is closed" in str(e):
                    logger.debug("Async client already closed or event loop is closed")
                else:
                    logger.warning(f"Error closing async MongoDB client: {e}", exc_info=True)
            except Exception as e:
                logger.warning(f"Unexpected error closing async MongoDB client: {e}", exc_info=True)
        
        logger.debug("MongoDB manager shutdown complete")
        
    def close(self):
        """Synchronously close all MongoDB connections."""
        if self._sync_client:
            self._sync_client.close()
            self._sync_client = None
            
        if self._async_client:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If we're in an event loop, schedule the close
                    asyncio.create_task(self.aclose())
                else:
                    # Otherwise, run it synchronously
                    loop.run_until_complete(self.aclose())
            except Exception as e:
                logger.warning(f"Error in close(): {e}")
                # Fallback to synchronous close if event loop is not available
                if self._async_client:
                    self._async_client = None
    
    def __del__(self):
        """Ensure connections are closed when the manager is destroyed."""
        self.close()

# Singleton instance - initialized on first use
_mongo_manager = None

def get_mongo_manager():
    """Get the MongoDB manager instance with lazy initialization."""
    global _mongo_manager
    if _mongo_manager is None:
        _mongo_manager = MongoManager()
    return _mongo_manager

# For backward compatibility
mongo_manager = get_mongo_manager()

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

# For non-FastAPI applications, use the following:
if __name__ != "__main__" and not _in_fastapi_lifespan:
    try:
        # Try to get the running event loop
        loop = asyncio.get_running_loop()
        # If we're here, there's a running event loop
        loop.create_task(_on_startup())
    except RuntimeError:
        # No running event loop, create a new one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_on_startup())
        
        # Register cleanup for non-FastAPI applications
        def cleanup():
            """Safely clean up resources on application exit."""
            try:
                # Check if there's anything to clean up
                if not hasattr(mongo_manager, '_async_client') or mongo_manager._async_client is None:
                    print("No MongoDB client to clean up")
                    return
                    
                # Try to get the event loop
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError as e:
                    print(f"No event loop available for cleanup: {e}")
                    return
                
                # Create a shutdown task
                shutdown_task = _on_shutdown()
                
                if loop.is_running():
                    # If loop is running, schedule the shutdown
                    task = loop.create_task(shutdown_task)
                    
                    # Add a callback to handle task completion
                    def handle_done(fut):
                        try:
                            fut.result()
                            print("Shutdown completed successfully")
                        except Exception as e:
                            print(f"Error in shutdown task: {e}")
                    
                    task.add_done_callback(handle_done)
                else:
                    # If no running loop, create a new one and run until complete
                    try:
                        loop.run_until_complete(shutdown_task)
                    except RuntimeError as e:
                        print(f"Error running shutdown: {e}")
                        
            except Exception as e:
                print(f"Unexpected error during cleanup: {e}")
            finally:
                # Ensure we don't leave dangling references
                if hasattr(mongo_manager, '_async_client'):
                    mongo_manager._async_client = None
        
        atexit.register(cleanup)
