"""Main FastAPI application module."""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

def setup_logging():
    """Configure logging for the application."""
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log_file = os.path.join(log_dir, "app.log")

    # File handler
    file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=3)
    file_handler.setFormatter(log_formatter)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Ensure Uvicorn logs are captured
    for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
        uvicorn_logger = logging.getLogger(logger_name)
        uvicorn_logger.propagate = True
        uvicorn_logger.handlers = [file_handler, console_handler]

    logger = logging.getLogger(__name__)
    logger.info("--- Logging configured successfully ---")
    return logger

logger = setup_logging()

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.v1 import router as api_router
from .api import openai_compatibility as openai_api
from .tasks.sync_tasks import sync_scheduler
from .tasks.price_monitor import get_price_monitor
from .core.config import get_settings
from .core.auth import get_api_key, API_KEY_NAME
from .db.mongodb import initialize_mongodb, mongo_manager

logger.info("Attempting to load application settings...")
try:
    settings = get_settings()
    logger.info("Application settings loaded successfully.")
except Exception as e:
    logger.critical(f"CRITICAL: Failed to load settings: {e}", exc_info=True)
    # Exit if settings fail to load, as the app cannot run.
    sys.exit(1)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown events."""
    logger.info("--- Application Lifespan Startup --- ")
    try:
        logger.info("Initializing MongoDB connection...")
        mongo_ok = await initialize_mongodb()
        if mongo_ok:
            logger.info("MongoDB initialization successful.")
        else:
            logger.error("MongoDB initialization failed. The service will run but DB features may be degraded.")

        if settings.TESTING:
            logger.info("TESTING mode detected: Skipping background tasks startup.")
        else:
            if settings.ENABLE_DB_SYNC:
                logger.info("Starting database synchronization task...")
                await sync_scheduler.start()
                logger.info("Database synchronization task started.")
            
            price_monitor = get_price_monitor()
            logger.info("Starting price monitor...")
            price_monitor.task = asyncio.create_task(price_monitor.start())
            logger.info("Price monitor task created.")

        logger.info("--- Application startup tasks completed successfully ---")
    except Exception as e:
        logger.critical(f"CRITICAL: Application startup failed within lifespan: {e}", exc_info=True)
        # Re-raising the exception to ensure FastAPI's error handling catches it
        raise

    yield

    logger.info("Shutting down application...")
    try:
        price_monitor = get_price_monitor()
        if price_monitor.is_running:
            logger.info("Stopping price monitor...")
            await price_monitor.stop()

        settings = get_settings()
        if settings.ENABLE_DB_SYNC and sync_scheduler._task and not sync_scheduler._task.done():
            logger.info("Stopping database synchronization task...")
            await sync_scheduler.stop()
        # Close MongoDB connections gracefully
        logger.info("Closing MongoDB connections...")
        await mongo_manager.aclose()
        logger.info("Application shutdown tasks completed successfully.")
    except Exception as e:
        logger.error(f"Application shutdown failed: {e}", exc_info=True)
    finally:
        logger.info("Application shutdown complete.")

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

app.include_router(openai_api.router, prefix="/v1/chat", tags=["OpenAI Compatibility"])

# Health check endpoint is now in api/v1/health.py

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
