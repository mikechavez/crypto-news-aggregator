"""Pytest configuration and fixtures for testing the Crypto News Aggregator."""
import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import AsyncGenerator, Dict, Any, Callable, Generator, Optional

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import settings first to configure the environment
from src.crypto_news_aggregator.core.config import Settings

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create a test settings class that inherits from Settings
class TestSettings(Settings):
    # Core settings
    TESTING: bool = True
    PROJECT_NAME: str = "Crypto News Aggregator Test"
    VERSION: str = "0.1.0"
    DEBUG: bool = True
    
    # Database settings
    FORCE_SQLITE: bool = True
    DATABASE_URL: str = "sqlite+aiosqlite:///:memory:"
    
    # MongoDB settings
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_NAME: str = "test_news_aggregator"
    
    # News API settings
    NEWS_API_KEY: str = "test_api_key"
    NEWSAPI_RATE_LIMIT: int = 0  # No rate limiting in tests
    
    # Redis settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    # Celery settings
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # Real-time news API settings
    REALTIME_NEWSAPI_URL: str = "http://test-server:3000"
    
    # Upstash Redis settings
    UPSTASH_REDIS_REST_URL: str = "https://test-upstash-redis.example.com"
    UPSTASH_REDIS_TOKEN: str = "test-upstash-token"
    
    # Email/SMTP settings
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_SENDER: str = ""
    
    # Cache settings
    CACHE_EXPIRE: int = 300  # 5 minutes for tests
    
    def __init__(self, **data):
        # Set default values if not provided
        defaults = {
            "MONGODB_URI": "mongodb://localhost:27017",
            "MONGODB_NAME": "test_news_aggregator",
            "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
            "CELERY_BROKER_URL": "redis://localhost:6379/0",
            "CELERY_RESULT_BACKEND": "redis://localhost:6379/0"
        }
        
        # Update with any provided values, but don't override with None
        for key, value in defaults.items():
            if key not in data and getattr(self, key, None) is None:
                data[key] = value
                
        super().__init__(**data)

# Override the get_settings function to return our test settings
def get_test_settings():
    return TestSettings()

# Get test settings instance
settings = get_test_settings()

# Configure test databases
TEST_DATABASE_URL = settings.DATABASE_URL
TEST_MONGODB_URI = settings.MONGODB_URI
TEST_MONGODB_DB = settings.MONGODB_NAME

# Ensure the settings are properly set for testing
os.environ["MONGODB_URI"] = TEST_MONGODB_URI
os.environ["MONGODB_NAME"] = TEST_MONGODB_DB

# Now import the rest of the application
from src.crypto_news_aggregator.db.base import Base
from src.crypto_news_aggregator.db.session import get_session, get_engine, get_sessionmaker
from src.crypto_news_aggregator.services.article_service import ArticleService, article_service

# Clear any existing tables
Base.metadata.clear()

# Import models after clearing metadata
from src.crypto_news_aggregator.db import models

# Import the FastAPI app after models to ensure tables are defined
from src.crypto_news_aggregator.main import app

# MongoDB client for testing
@pytest_asyncio.fixture(scope="session")
async def mongo_client() -> AsyncGenerator[AsyncIOMotorClient, None]:
    """Create a MongoDB client for testing."""
    # Ensure the MongoDB URI is set
    mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    logger.info(f"Connecting to MongoDB at {mongo_uri}")
    
    # Create the client
    client = AsyncIOMotorClient(mongo_uri)
    
    try:
        # Test the connection
        await client.admin.command('ping')
        logger.info("✅ Successfully connected to MongoDB")
        
        # Get the database
        db = client[TEST_MONGODB_DB]
        
        # Clean up any existing data
        await db.drop_collection("test_collection")
        
        yield client
    except Exception as e:
        logger.error(f"❌ Failed to connect to MongoDB: {e}")
        raise
    finally:
        # Clean up
        try:
            await client.drop_database(TEST_MONGODB_DB)
            client.close()
            logger.info("✅ Closed MongoDB connection")
        except Exception as e:
            logger.error(f"❌ Error during MongoDB cleanup: {e}")

@pytest_asyncio.fixture(scope="session")
async def mongo_db(mongo_client: AsyncIOMotorClient) -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    """Get the test database."""
    db = mongo_client[TEST_MONGODB_DB]
    yield db
    # Cleanup is handled by mongo_client fixture

@pytest.fixture(autouse=True)
def override_article_service(mongo_db: AsyncIOMotorDatabase):
    """Override the article service to use the test database."""
    from src.crypto_news_aggregator.services.article_service import article_service
    
    # Store the original collection name
    original_collection = article_service.collection_name
    
    # Update the collection name to use the test database
    article_service.collection_name = mongo_db.name + "." + article_service.collection_name
    
    yield
    
    # Restore the original collection name
    article_service.collection_name = original_collection

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session")
async def db_engine():
    """Create and configure a test database engine."""
    # Use a file-based SQLite database for testing to avoid in-memory DB issues
    TEST_DB_URL = "sqlite+aiosqlite:///./test.db"
    
    # Clean up any existing test database
    if os.path.exists("./test.db"):
        os.remove("./test.db")
    
    # Create engine with echo=True for debugging
    engine = create_async_engine(
        TEST_DB_URL,
        echo=True,
        future=True
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    # Verify tables were created
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        tables = [row[0] for row in result.all()]
        logger.info(f"Tables in database: {tables}")
    
    yield engine
    
    # Clean up
    await engine.dispose()
    if os.path.exists("./test.db"):
        os.remove("./test.db")

@pytest_asyncio.fixture
async def db_session(db_engine):
    """Create a new database session for testing."""
    connection = await db_engine.connect()
    transaction = await connection.begin()
    
    # Create a session with the connection
    session = AsyncSession(bind=connection, expire_on_commit=False)
    
    # Begin a nested transaction (using SAVEPOINT)
    await session.begin_nested()
    
    # Add finalizer to rollback and close the session after the test
    @pytest.hookimpl(hookwrapper=True)
    async def finalize():
        await session.rollback()
        await session.close()
        await transaction.rollback()
        await connection.close()
    
    try:
        yield session
    finally:
        await finalize()

@pytest.fixture
def override_get_db(db_session: AsyncSession):
    """Override the get_db dependency for testing."""
    async def _get_db():
        try:
            yield db_session
        finally:
            pass  # Don't close the session here, let the fixture handle it
    
    return _get_db

@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create a test client that includes the database session."""
    # Create a new test client for each test
    with TestClient(app) as test_client:
        # Setup test database session
        async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
            async with async_sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=create_async_engine(settings.DATABASE_URL)
            )() as session:
                try:
                    yield session
                except Exception:
                    await session.rollback()
                    raise
                finally:
                    await session.close()
        
        # Override the get_session dependency
        app.dependency_overrides[get_session] = override_get_session
        
        try:
            yield test_client
        finally:
            # Clean up
            app.dependency_overrides = {}

@pytest.fixture
def mock_newsapi() -> Dict[str, Any]:
    """Return a mock NewsAPI response."""
    return {
        "status": "ok",
        "totalResults": 1,
        "articles": [
            {
                "source": {"id": "test-source", "name": "Test Source"},
                "author": "Test Author",
                "title": "Test Article",
                "description": "Test description",
                "url": "https://example.com/test-article",
                "urlToImage": "https://example.com/image.jpg",
                "publishedAt": "2025-01-01T12:00:00Z",
                "content": "Test content"
            }
        ]
    }

@pytest.fixture
def mock_article_data() -> Dict[str, Any]:
    """Return mock article data."""
    return {
        "source": {"id": "test-source", "name": "Test Source"},
        "author": "Test Author",
        "title": "Test Article",
        "description": "Test description",
        "url": "https://example.com/test-article",
        "urlToImage": "https://example.com/image.jpg",
        "publishedAt": "2025-01-01T12:00:00Z",
        "content": "Test content"
    }

# Configure pytest to use asyncio
pytest_plugins = ('pytest_asyncio',)

@pytest.fixture(autouse=True)
def mock_celery_app(monkeypatch):
    """Mock the Celery app to avoid using a real backend in tests."""
    from unittest.mock import MagicMock
    
    # Create a mock Celery app
    mock_app = MagicMock()
    
    # Mock the AsyncResult class
    class MockAsyncResult:
        def __init__(self, task_id, **kwargs):
            self.task_id = task_id
            self._status = kwargs.get('status', 'PENDING')
            self._result = kwargs.get('result', None)
            self._ready = self._status != 'PENDING' and self._status != 'STARTED'
            
            # Mock methods
            self.ready = MagicMock(return_value=self._ready)
            self.successful = MagicMock(return_value=self._status == 'SUCCESS')
            self.failed = MagicMock(return_value=self._status == 'FAILURE')
            self.get = MagicMock(return_value=self._result)
        
        @property
        def status(self):
            return self._status
            
        @status.setter
        def status(self, value):
            self._status = value
            self._ready = value not in ['PENDING', 'STARTED']
            self.ready.return_value = self._ready
            
        @property
        def result(self):
            return self._result
            
        @result.setter
        def result(self, value):
            self._result = value
            if value is not None:
                self._ready = True
                self.ready.return_value = True
    
    # Patch the Celery app and AsyncResult
    monkeypatch.setattr('crypto_news_aggregator.tasks.app', mock_app)
    monkeypatch.setattr('crypto_news_aggregator.api.v1.tasks.AsyncResult', MockAsyncResult)
    
    return mock_app

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers",
        "asyncio: mark test as async so it can use async/await"
    )