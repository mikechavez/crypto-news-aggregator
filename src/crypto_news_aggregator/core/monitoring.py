"""
Performance monitoring middleware for FastAPI application.
"""
import time
import logging
from typing import Callable, Dict, Any
from fastapi import Request, Response

# Try to import BaseHTTPMiddleware, fallback to a custom implementation if not available
try:
    from fastapi.middleware.base import BaseHTTPMiddleware
except ImportError:
    # Fallback for FastAPI versions that don't have BaseHTTPMiddleware
    class BaseHTTPMiddleware:
        """Fallback middleware base class."""
        def __init__(self, app):
            self.app = app

        async def __call__(self, scope, receive, send):
            if scope["type"] != "http":
                await self.app(scope, receive, send)
                return

            # Custom middleware logic would go here
            await self.app(scope, receive, send)

logger = logging.getLogger(__name__)

class PerformanceMonitoringMiddleware:
    """ASGI middleware for monitoring API performance and errors."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.time()

        # Store the original send function
        original_send = send

        async def custom_send(message):
            if message["type"] == "http.response.start":
                process_time = time.time() - start_time
                # Log successful response
                logger.info(
                    f"API_REQUEST_COMPLETED: {scope.get('method', 'UNKNOWN')} {scope.get('path', 'UNKNOWN')} "
                    f"{message.get('status', 200)} {process_time*1000:.2f}ms"
                )

                # Add performance headers
                headers = dict(message.get("headers", []))
                headers[b"x-process-time"] = str(process_time).encode()
                message["headers"] = list(headers.items())

            await original_send(message)

        try:
            await self.app(scope, receive, custom_send)
        except Exception as e:
            process_time = time.time() - start_time
            # Log error with category
            error_category = self._categorize_error(e)
            logger.error(
                f"API_REQUEST_ERROR: {scope.get('method', 'UNKNOWN')} {scope.get('path', 'UNKNOWN')} "
                f"{error_category} {type(e).__name__}: {str(e)} ({process_time*1000:.2f}ms)"
            )
            raise

    def _categorize_error(self, error: Exception) -> str:
        """Categorize errors for monitoring."""
        error_msg = str(error).lower()

        # Authentication errors (check first for specific patterns)
        if any(keyword in error_msg for keyword in ['auth', 'token', 'unauthorized', 'forbidden', 'invalid', 'key']):
            return 'authentication_error'
        # LLM/AI errors (check before generic API errors)
        elif any(keyword in error_msg for keyword in ['llm', 'ai', 'openai', 'model', 'generation']):
            return 'llm_error'
        # Database errors
        elif 'database' in error_msg or 'mongodb' in error_msg:
            return 'database_error'
        # External API errors
        elif 'coingecko' in error_msg or 'api' in error_msg:
            return 'external_api_error'
        else:
            return 'infrastructure_error'

class DatabaseErrorMonitor:
    """Monitor database operations and errors."""

    @staticmethod
    def log_database_operation(operation: str, collection: str, success: bool, duration_ms: float, error: Exception = None):
        """Log database operation metrics."""
        if success:
            logger.info(
                f"DATABASE_OPERATION_SUCCESS: {operation} on {collection} took {duration_ms:.2f}ms"
            )
        else:
            logger.error(
                f"DATABASE_OPERATION_ERROR: {operation} on {collection} failed after {duration_ms:.2f}ms - {type(error).__name__}: {str(error)}"
            )

class LLMErrorMonitor:
    """Monitor LLM operations and errors."""

    @staticmethod
    def log_llm_operation(provider: str, operation: str, success: bool, duration_ms: float, error: Exception = None, token_count: int = None):
        """Log LLM operation metrics."""
        extra_data = {
            "provider": provider,
            "operation": operation,
            "success": success,
            "duration_ms": round(duration_ms, 2)
        }

        if token_count is not None:
            extra_data["token_count"] = token_count

        if success:
            logger.info(f"LLM_OPERATION_SUCCESS", extra=extra_data)
        else:
            extra_data["error_type"] = type(error).__name__
            extra_data["error_message"] = str(error)
            logger.error(f"LLM_OPERATION_ERROR", extra=extra_data)

class PerformanceMetrics:
    """Collect and log performance metrics."""

    @staticmethod
    def log_api_performance(endpoint: str, method: str, duration_ms: float, status_code: int, cache_hit: bool = False):
        """Log API performance metrics."""
        logger.info(
            f"API_PERFORMANCE: {method} {endpoint} {status_code} {duration_ms:.2f}ms {'CACHE_HIT' if cache_hit else 'FRESH'}"
        )

    @staticmethod
    def log_external_api_call(service: str, endpoint: str, success: bool, duration_ms: float, error: Exception = None):
        """Log external API call metrics."""
        if success:
            logger.info(
                f"EXTERNAL_API_SUCCESS: {service} {endpoint} {duration_ms:.2f}ms"
            )
        else:
            logger.error(
                f"EXTERNAL_API_ERROR: {service} {endpoint} {type(error).__name__}: {str(error)} ({duration_ms:.2f}ms)"
            )

def setup_performance_monitoring(app):
    """Add performance monitoring middleware to the FastAPI app."""
    # For ASGI apps, we need to wrap the app with our middleware
    app.user_middleware = [PerformanceMonitoringMiddleware(app)]
    logger.info("Performance monitoring middleware added to application")
