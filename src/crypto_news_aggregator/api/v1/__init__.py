"""API v1 routes."""
from fastapi import APIRouter
from .. import router as root_router  # Import the root router with task endpoints
from . import articles, sources, health, tasks

# Create a new router for v1 endpoints
router = APIRouter(prefix="/api/v1")

# Include all the v1 routes
router.include_router(health.router, tags=["health"])
router.include_router(articles.router, prefix="/articles", tags=["articles"])
router.include_router(sources.router, prefix="/sources", tags=["sources"])
router.include_router(tasks.router, tags=["tasks"])

# Include the task endpoints from the root router
# These are the task endpoints defined in api/__init__.py
router.include_router(root_router, prefix="", tags=["tasks"])
