"""Alert-related Pydantic models."""
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, ClassVar
from pydantic import BaseModel, Field, field_validator, ConfigDict


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


class AlertInDB(AlertBase):
    """Alert model for database operations."""
    id: str = Field(..., alias="_id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_triggered: Optional[datetime] = None
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )


class Alert(AlertBase):
    """Alert model for API responses."""
    id: str = Field(..., alias="_id")
    created_at: datetime
    last_triggered: Optional[datetime] = None
    
    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            datetime: lambda v: v.isoformat()
        },
        from_attributes=True
    )
