"""API v1 routes."""
from fastapi import APIRouter
from . import articles, sources, health, tasks

router = APIRouter(prefix="/api/v1")
router.include_router(health.router, tags=["health"])
router.include_router(articles.router, prefix="/articles", tags=["articles"])
router.include_router(sources.router, prefix="/sources", tags=["sources"])
router.include_router(tasks.router)
