"""Package for data models."""

# Import models here to make them available when importing from the package
from .user import User, UserInDB, UserCreate  # noqa: F401
from .alert import (  # noqa: F401
    Alert,
    AlertInDB,
    AlertCreate,
    AlertUpdate,
    AlertCondition
)
from .article import ArticleInDB, ArticleCreate  # noqa: F401
