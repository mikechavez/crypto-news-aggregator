"""Article-related API endpoints - re-exports from endpoints.articles."""

# Import the router from the actual implementation
from .endpoints.articles import router

__all__ = ["router"]
