"""Core application dependencies."""

from functools import lru_cache
from fastapi.security import OAuth2PasswordBearer
from .config import get_settings


@lru_cache()
def get_oauth2_scheme():
    """FastAPI dependency to get the OAuth2 password bearer scheme.

    This is defined as a dependency to ensure that settings are loaded
    correctly and to avoid module-level instantiation, which can cause
    issues in some environments.
    """
    settings = get_settings()
    return OAuth2PasswordBearer(
        tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False
    )
