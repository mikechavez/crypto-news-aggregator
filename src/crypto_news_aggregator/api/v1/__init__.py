"""API v1 routes."""
from fastapi import APIRouter, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer

from ...core import security
from ...core.config import get_settings
from ...models.user import User as UserModel

# Create a new router for v1 endpoints
def get_router():
    settings = get_settings()
    return APIRouter(prefix=settings.API_V1_STR)

router = get_router()

# Import all the v1 routes
from . import articles
from . import sources
from . import health
from . import tasks

from .endpoints import price
from .endpoints import emails
from .endpoints import auth

# Import test endpoints only when explicitly enabled
def _enable_test_endpoints() -> bool:
    try:
        return bool(get_settings().model_dump().get("ENABLE_TEST_ENDPOINTS", False))
    except Exception:
        return False

if _enable_test_endpoints():
    from .endpoints import test_alerts


# Public routes (no authentication required)
router.include_router(health.router, tags=["health"])
router.include_router(auth.router, prefix="/auth", tags=["authentication"])

# API key protected routes (no JWT required)
# The tasks router itself applies API key security via Security(get_api_key)
router.include_router(tasks.router, prefix="", tags=["tasks"])

# Protected routes (require authentication)
protected_router = APIRouter()
protected_router.include_router(articles.router, prefix="/articles", tags=["articles"]) 
protected_router.include_router(sources.router, prefix="/sources", tags=["sources"])
protected_router.include_router(price.router, prefix="/price", tags=["price"])

# Include test endpoints only when explicitly enabled
if _enable_test_endpoints():
    protected_router.include_router(test_alerts.router, prefix="/test", tags=["test"])

# Email tracking endpoints (partially public - some endpoints don't require auth)
router.include_router(emails.router, prefix="/emails", tags=["emails"])

# Include the protected router with dependencies
router.include_router(
    protected_router,
    dependencies=[Depends(security.get_current_active_user)]
)
