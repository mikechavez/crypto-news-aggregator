"""User-related Pydantic models."""
from datetime import datetime
from typing import Optional, List, Dict
from enum import Enum
from pydantic import BaseModel, EmailStr, Field, HttpUrl, validator
from bson import ObjectId


class UserSubscriptionPreferences(BaseModel):
    """User's email subscription preferences."""
    price_alerts: bool = True
    market_updates: bool = True
    newsletter: bool = True
    marketing: bool = False


class EmailVerificationStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    BOUNCED = "bounced"


class UserTrackingSettings(BaseModel):
    """User's email tracking settings."""
    track_opens: bool = True
    track_clicks: bool = True
    track_geo: bool = False


class UserBase(BaseModel):
    """Base user model with common fields."""
    username: str = Field(..., min_length=3, max_length=50, pattern=r'^[a-zA-Z0-9_]+$',
                         description="Username must be 3-50 characters long and can only contain letters, numbers, and underscores")
    email: EmailStr
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    is_active: bool = True
    is_superuser: bool = False
    email_verified: bool = False
    email_verification_status: EmailVerificationStatus = EmailVerificationStatus.PENDING
    email_verification_token: Optional[str] = None
    email_verification_sent_at: Optional[datetime] = None
    unsubscribed: bool = False
    unsubscribe_token: Optional[str] = None
    subscription_preferences: UserSubscriptionPreferences = Field(
        default_factory=UserSubscriptionPreferences
    )
    tracking_settings: UserTrackingSettings = Field(
        default_factory=UserTrackingSettings
    )
    last_login_at: Optional[datetime] = None
    last_login_ip: Optional[str] = None
    
    @validator('username')
    def username_to_lower(cls, v):
        """Convert username to lowercase for case-insensitive uniqueness."""
        return v.lower()
    login_count: int = 0
    timezone: Optional[str] = "UTC"
    locale: Optional[str] = "en-US"


class UserCreate(BaseModel):
    """Model for creating a new user."""
    username: str = Field(..., min_length=3, max_length=50, pattern=r'^[a-zA-Z0-9_]+$',
                         description="Username must be 3-50 characters long and can only contain letters, numbers, and underscores")
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100,
                         description="Password must be at least 8 characters long")
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    timezone: Optional[str] = "UTC"
    locale: Optional[str] = "en-US"
    
    @validator('username')
    def username_to_lower(cls, v):
        """Convert username to lowercase for case-insensitive uniqueness."""
        return v.lower()


class UserInDB(UserBase):
    """User model for database operations."""
    id: str = Field(..., alias="_id")
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        """Pydantic config."""
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        
    @validator('id', pre=True)
    def validate_id(cls, v):
        if isinstance(v, ObjectId):
            return str(v)
        return v


class UserUpdate(BaseModel):
    """Model for updating user profile."""
    username: Optional[str] = Field(
        None, 
        min_length=3, 
        max_length=50, 
        pattern=r'^[a-zA-Z0-9_]+$',
        description="Username must be 3-50 characters long and can only contain letters, numbers, and underscores"
    )
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    timezone: Optional[str] = None
    locale: Optional[str] = None
    subscription_preferences: Optional[UserSubscriptionPreferences] = None
    tracking_settings: Optional[UserTrackingSettings] = None
    
    @validator('username')
    def username_to_lower(cls, v):
        """Convert username to lowercase for case-insensitive uniqueness."""
        return v.lower() if v else v


class User(UserBase):
    """User model for API responses."""
    id: str = Field(..., alias="_id")
    created_at: datetime
    updated_at: datetime
    
    class Config:
        """Pydantic config."""
        allow_population_by_field_name = True
        json_encoders = {ObjectId: str}


class UserResponse(BaseModel):
    """User response model with public profile information."""
    id: str = Field(..., alias="_id")
    username: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool
    email_verified: bool
    subscription_preferences: UserSubscriptionPreferences
    created_at: datetime
    
    class Config:
        """Pydantic config."""
        allow_population_by_field_name = True
        json_encoders = {ObjectId: str}


class EmailVerificationRequest(BaseModel):
    """Model for email verification request."""
    token: str


class UnsubscribeRequest(BaseModel):
    """Model for unsubscribe request."""
    token: str
    email_type: Optional[str] = None  # 'all' or specific type like 'price_alerts'
