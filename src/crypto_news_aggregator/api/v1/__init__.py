"""API v1 routes."""
from fastapi import APIRouter
from . import articles, sources, health, tasks

# Create a new router for v1 endpoints
router = APIRouter(prefix="/api/v1")

# Include all the v1 routes
router.include_router(health.router, tags=["health"])
router.include_router(articles.router, prefix="/articles", tags=["articles"])
router.include_router(sources.router, prefix="/sources", tags=["sources"])
router.include_router(tasks.router, prefix="", tags=["tasks"])
