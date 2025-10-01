"""Authentication and authorization utilities."""

import logging
from fastapi import HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader
from typing import List, Optional
import os

logger = logging.getLogger(__name__)

# API Key Header
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


def get_api_keys() -> List[str]:
    """Get the list of valid API keys from environment variables or config.

    This function is called at runtime to ensure environment variables are loaded.
    """
    from ..core.config import get_settings

    settings = get_settings()
    # First try to get from environment variable
    api_keys_raw = os.getenv("API_KEYS", "")
    api_keys = [key.strip() for key in api_keys_raw.split(",") if key.strip()]

    # If no API keys from env, use the single API_KEY from config
    if not api_keys:
        if settings.API_KEY:
            api_keys = [settings.API_KEY]
        else:
            logger.warning(
                "No API keys found in environment variables or config. API authentication will fail for all requests."
            )
    else:
        logger.debug(f"Loaded {len(api_keys)} API keys from environment")

    return api_keys


async def get_api_key(api_key_header: str = Security(api_key_header)) -> str:
    """
    Validate the API key from the request header.

    Args:
        api_key_header: The API key from the X-API-Key header

    Returns:
        The validated API key

    Raises:
        HTTPException: If the API key is invalid or missing
    """
    if not api_key_header:
        logger.warning("API key is missing from request headers")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is missing",
            headers={"WWW-Authenticate": "API-Key"},
        )

    # Get current API keys
    valid_api_keys = get_api_keys()

    # Log the received API key (redacted for security in production)
    logger.debug(
        f"Validating API key: {api_key_header[:3]}...{api_key_header[-3:] if len(api_key_header) > 6 else '***'}"
    )

    if api_key_header not in valid_api_keys:
        logger.warning(
            f"Invalid API key provided. Valid keys: {[k[:3] + '...' + k[-3:] if len(k) > 6 else '***' for k in valid_api_keys]}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "API-Key"},
        )

    logger.debug("API key validation successful")

    return api_key_header
