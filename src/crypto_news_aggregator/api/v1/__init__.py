"""API v1 routes."""
from fastapi import APIRouter, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer

from src.crypto_news_aggregator.core import security
from src.crypto_news_aggregator.core.config import settings
from src.crypto_news_aggregator.models.user import User as UserModel

# Create a new router for v1 endpoints
router = APIRouter(prefix=settings.API_V1_STR)

# Import all the v1 routes
from . import articles, sources, health, tasks
from .endpoints import price, emails, auth

# Import test endpoints (only in debug mode)
if settings.DEBUG or settings.TESTING:
    from .endpoints import test_alerts

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    auto_error=False
)

# Public routes (no authentication required)
router.include_router(health.router, tags=["health"])
router.include_router(auth.router, prefix="/auth", tags=["authentication"])

# Protected routes (require authentication)
protected_router = APIRouter()
protected_router.include_router(articles.router, prefix="/articles", tags=["articles"])
protected_router.include_router(sources.router, prefix="/sources", tags=["sources"])
protected_router.include_router(tasks.router, prefix="", tags=["tasks"])
protected_router.include_router(price.router, prefix="/price", tags=["price"])

# Include test endpoints only in debug mode
if settings.DEBUG or settings.TESTING:
    protected_router.include_router(test_alerts.router, prefix="/test", tags=["test"])

# Email tracking endpoints (partially public - some endpoints don't require auth)
router.include_router(emails.router, prefix="/emails", tags=["emails"])

# Include the protected router with dependencies
router.include_router(
    protected_router,
    dependencies=[Depends(security.get_current_active_user)]
)

