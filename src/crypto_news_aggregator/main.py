"""Main FastAPI application module."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.v1 import router as api_router
from .tasks.sync_tasks import sync_scheduler
from .core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown events."""
    # Startup
    logger.info("Starting application...")
    
    # Start the sync scheduler if enabled
    if settings.ENABLE_DB_SYNC:
        logger.info("Starting database synchronization task...")
        await sync_scheduler.start()
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    
    # Stop the sync scheduler if it's running
    if settings.ENABLE_DB_SYNC and sync_scheduler._task and not sync_scheduler._task.done():
        logger.info("Stopping database synchronization task...")
        await sync_scheduler.stop()
    
    logger.info("Application shutdown complete")

app = FastAPI(
    title="Crypto News Aggregator API",
    description="API for aggregating and analyzing cryptocurrency news",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(api_router)

# Health check endpoint is now in api/v1/health.py

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("crypto_news_aggregator.main:app", host="0.0.0.0", port=8000, reload=True)
