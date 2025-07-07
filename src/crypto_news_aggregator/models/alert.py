"""Alert-related Pydantic models."""
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, ClassVar, Any, Dict
from bson import ObjectId
from pydantic import BaseModel, Field, field_validator, ConfigDict, GetCoreSchemaHandler
from pydantic_core import core_schema


class PyObjectId(str):
    """Custom type for MongoDB ObjectId."""
    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source_type: Any, _handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.chain_schema(
            [
                core_schema.str_schema(),
                core_schema.no_info_plain_validator_function(cls.validate),
            ]
        )

    @classmethod
    def validate(cls, v: Any) -> str:
        """Validate and convert input to string representation of ObjectId."""
        if isinstance(v, ObjectId):
            return str(v)
        if isinstance(v, str) and ObjectId.is_valid(v):
            return v
        raise ValueError("Invalid ObjectId")


class AlertCondition(str, Enum):
    """Possible conditions for price alerts."""
    ABOVE = "above"
    BELOW = "below"
    PERCENT_UP = "percent_up"
    PERCENT_DOWN = "percent_down"


class AlertBase(BaseModel):
    """Base alert model with common fields."""
    user_id: str = Field(..., description="ID of the user who created the alert")
    crypto_id: str = Field(..., description="Cryptocurrency symbol (e.g., 'bitcoin')")
    condition: AlertCondition = Field(..., description="Alert condition type")
    threshold: float = Field(..., description="Price or percentage threshold for the alert")
    is_active: bool = Field(True, description="Whether the alert is active")
    cooldown_minutes: int = Field(60, description="Minutes to wait before sending another alert for the same condition")


class AlertCreate(AlertBase):
    """Model for creating a new alert."""
    pass


class AlertUpdate(BaseModel):
    """Model for updating an existing alert."""
    condition: Optional[AlertCondition] = None
    threshold: Optional[float] = None
    is_active: Optional[bool] = None
    cooldown_minutes: Optional[int] = None
    last_triggered_price: Optional[float] = Field(
        None, 
        description="The price at which the alert was last triggered"
    )

    @field_validator('threshold')
    @classmethod
    def validate_threshold(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError("Threshold must be a positive number")
        return v

    @field_validator('cooldown_minutes')
    @classmethod
    def validate_cooldown(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError("Cooldown minutes cannot be negative")
        return v


class AlertStatus(str, Enum):
    """Status of an alert."""
    ACTIVE = "active"
    PAUSED = "paused"
    DELETED = "deleted"


class AlertInDB(AlertBase):
    """Alert model for database operations."""
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    
    @field_validator('id', mode='before')
    @classmethod
    def validate_id(cls, v):
        """Convert ObjectId to string if needed."""
        if isinstance(v, ObjectId):
            return str(v)
        if isinstance(v, str) and ObjectId.is_valid(v):
            return v
        raise ValueError("Invalid ObjectId format")
    user_email: str = Field(..., description="Email address to send alerts to")
    user_name: Optional[str] = Field(None, description="Name of the user receiving alerts")
    crypto_name: str = Field("Bitcoin", description="Name of the cryptocurrency")
    crypto_symbol: str = Field("BTC", description="Symbol of the cryptocurrency")
    threshold_percent: float = Field(..., description="Percentage change threshold for the alert")
    last_triggered: Optional[datetime] = Field(None, description="When the alert was last triggered")
    last_triggered_price: Optional[float] = Field(None, description="Price when the alert was last triggered")
    status: AlertStatus = Field(AlertStatus.ACTIVE, description="Current status of the alert")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
            AlertStatus: lambda v: v.value,
            ObjectId: str,
        },
        json_schema_extra={
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "user_id": "user_123",
                "user_email": "user@example.com",
                "user_name": "John Doe",
                "crypto_id": "bitcoin",
                "crypto_name": "Bitcoin",
                "crypto_symbol": "BTC",
                "condition": "percent_up",
                "threshold": 1.0,
                "threshold_percent": 1.0,
                "is_active": True,
                "cooldown_minutes": 60,
                "status": "active",
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-01T00:00:00Z"
            }
        }
    )


class Alert(AlertInDB):
    """Alert model for API responses."""
    
    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
            AlertStatus: lambda v: v.value
        },
        from_attributes=True
    )
