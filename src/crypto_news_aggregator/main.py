"""Main FastAPI application module."""
import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.v1 import router as api_router
from .tasks.sync_tasks import sync_scheduler
from .tasks.price_monitor import price_monitor
from .core.config import get_settings
from .core.auth import get_api_key, API_KEY_NAME

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
    
    # Start the price monitor as a background task
    logger.info("Starting price monitor...")
    # Create the task and assign it to the monitor instance
    price_monitor.task = asyncio.create_task(price_monitor.start())
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    
    # Stop the price monitor if it's running
    if price_monitor.is_running:
        logger.info("Stopping price monitor...")
        await price_monitor.stop()

    # Stop the sync scheduler if it's running
    if settings.ENABLE_DB_SYNC and sync_scheduler._task and not sync_scheduler._task.done():
        logger.info("Stopping database synchronization task...")
        await sync_scheduler.stop()
    
    logger.info("Application shutdown complete")

# Create FastAPI application
app = FastAPI(
    title="Crypto News Aggregator API",
    description="API for aggregating and analyzing cryptocurrency news",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    dependencies=None  # We'll add dependencies to specific routers instead
)

# CORS middleware configuration
origins = ["*"]  # In production, replace with specific origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[API_KEY_NAME],
)

# Add exception handler for 401 Unauthorized
@app.exception_handler(status.HTTP_401_UNAUTHORIZED)
async def unauthorized_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": "Missing or invalid API key"},
        headers={"WWW-Authenticate": "API-Key"},
    )

# Add exception handler for 403 Forbidden
@app.exception_handler(status.HTTP_403_FORBIDDEN)
async def forbidden_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"detail": "Invalid API key"},
        headers={"WWW-Authenticate": "API-Key"},
    )

# Include API routers
app.include_router(api_router)

# Health check endpoint is now in api/v1/health.py

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("crypto_news_aggregator.main:app", host="0.0.0.0", port=8000, reload=True)
