"""Pydantic models for price alerts."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, validator
from enum import Enum


class AlertDirection(str, Enum):
    """Possible directions for price alerts."""
    UP = "up"
    DOWN = "down"
    BOTH = "both"


class AlertBase(BaseModel):
    """Base schema for price alerts."""
    symbol: str = Field("BTC", description="Cryptocurrency symbol (e.g., BTC, ETH)")
    threshold_percentage: float = Field(..., gt=0, le=1000, description="Price change percentage that triggers the alert")
    direction: AlertDirection = Field(
        AlertDirection.BOTH,
        description="Direction of price movement to alert on"
    )
    active: bool = Field(True, description="Whether the alert is active")

    @validator('symbol')
    def symbol_must_be_uppercase(cls, v):
        """Convert symbol to uppercase."""
        return v.upper()

    @validator('threshold_percentage')
    def round_threshold(cls, v):
        """Round threshold to 2 decimal places."""
        return round(v, 2)


class AlertCreate(AlertBase):
    """Schema for creating a new alert."""
    pass


class AlertUpdate(BaseModel):
    """Schema for updating an existing alert."""
    threshold_percentage: Optional[float] = Field(
        None, gt=0, le=1000, description="New price change percentage"
    )
    direction: Optional[AlertDirection] = Field(
        None, description="New direction for the alert"
    )
    active: Optional[bool] = Field(None, description="Whether the alert is active")

    class Config:
        """Pydantic config."""
        extra = "forbid"


class AlertInDB(AlertBase):
    """Schema for alert data in the database."""
    id: int
    user_id: int
    last_triggered: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config."""
        from_attributes = True


class Alert(AlertInDB):
    """Schema for alert responses."""
    pass


class AlertResponse(BaseModel):
    """Response model for alert operations."""
    success: bool
    message: str
    alert: Optional[Alert] = None


class AlertListResponse(BaseModel):
    """Response model for listing alerts."""
    success: bool
    count: int
    alerts: list[Alert]
