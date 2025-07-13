"""Pydantic models for PostgreSQL User data."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserBaseSQL(BaseModel):
    """Base Pydantic model for a user, matching the SQL schema."""
    email: EmailStr = Field(..., example="user@example.com")
    is_active: bool = True
    is_superuser: bool = False
    first_name: Optional[str] = Field(None, example="John")
    last_name: Optional[str] = Field(None, example="Doe")


class UserCreateSQL(UserBaseSQL):
    """Pydantic model for creating a user in SQL."""
    username: str = Field(..., example="johndoe")
    password: str = Field(..., min_length=8, example="aSecurePassword123!")


class UserUpdateSQL(UserBaseSQL):
    """Pydantic model for updating a user in SQL."""
    username: Optional[str] = None
    password: Optional[str] = None


class UserInDBBase(UserBaseSQL):
    """Base model for user data stored in the DB."""
    id: int = Field(..., example=1)
    username: str = Field(..., example="johndoe")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserSQL(UserInDBBase):
    """Pydantic model representing a user in SQL, for API responses."""
    pass


class UserInDB(UserInDBBase):
    """Pydantic model for user data in the database, including hashed password."""
    hashed_password: str
