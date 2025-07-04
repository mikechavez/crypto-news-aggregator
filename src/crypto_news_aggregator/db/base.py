"""
SQLAlchemy base model definitions.

This module provides the base class for all SQLAlchemy models using SQLAlchemy 2.0 style.
"""
from typing import Any, Dict
from sqlalchemy.orm import DeclarativeBase, declared_attr
from sqlalchemy import event


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.
    
    This provides the base for all database models and includes common functionality.
    """
    
    @declared_attr.directive
    def __tablename__(cls) -> str:
        """Generate __tablename__ automatically from class name."""
        return f"{cls.__name__.lower()}s"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary."""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


# Export Base explicitly
__all__ = ['Base']