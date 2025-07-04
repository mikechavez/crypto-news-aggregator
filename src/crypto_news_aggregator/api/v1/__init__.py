"""API v1 routes."""
from fastapi import APIRouter, Depends
from crypto_news_aggregator.core.auth import get_api_key

# Create a new router for v1 endpoints
router = APIRouter(prefix="/api/v1")

# Import all the v1 routes
from . import articles, sources, health, tasks
from .endpoints import price

# Public routes (no authentication required)
router.include_router(health.router, tags=["health"])

# Protected routes (authentication required)
protected_router = APIRouter(dependencies=[Depends(get_api_key)])
protected_router.include_router(articles.router, prefix="/articles", tags=["articles"])
protected_router.include_router(sources.router, prefix="/sources", tags=["sources"])
protected_router.include_router(tasks.router, prefix="", tags=["tasks"])
protected_router.include_router(endpoints.price.router, prefix="/price", tags=["price"])

# Include the protected router
router.include_router(protected_router)
