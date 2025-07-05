"""User-related Pydantic models."""
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Base user model with common fields."""
    email: EmailStr
    is_active: bool = True
    is_superuser: bool = False


class UserCreate(UserBase):
    """Model for creating a new user."""
    password: str


class UserInDB(UserBase):
    """User model for database operations."""
    id: str = Field(..., alias="_id")
    hashed_password: str
    
    class Config:
        """Pydantic config."""
        allow_population_by_field_name = True
        arbitrary_types_allowed = True


class User(UserBase):
    """User model for API responses."""
    id: str = Field(..., alias="_id")
    
    class Config:
        """Pydantic config."""
        allow_population_by_field_name = True
