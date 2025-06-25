import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import AsyncGenerator, Dict, Any, Callable, Generator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
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
    FORCE_SQLITE: bool = True
    DATABASE_URL: str = "sqlite+aiosqlite:///:memory:"

# Override the get_settings function to return our test settings
def get_test_settings():
    return TestSettings()

# Get test settings instance
settings = get_test_settings()

# Configure test database
TEST_DATABASE_URL = settings.DATABASE_URL

# Now import the rest of the application
from src.crypto_news_aggregator.db.base import Base
from src.crypto_news_aggregator.db.session import get_session, get_engine, get_sessionmaker

# Clear any existing tables
Base.metadata.clear()

# Import models after clearing metadata
from src.crypto_news_aggregator.db import models

# Import the FastAPI app after models to ensure tables are defined
from src.crypto_news_aggregator.main import app

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

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers",
        "asyncio: mark test as async so it can use async/await"
    )