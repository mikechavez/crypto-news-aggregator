"""Email-related Pydantic models."""
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict, Any

from bson import ObjectId
from pydantic import BaseModel, Field, ConfigDict

from ..db.mongodb import PyObjectId


class EmailEventType(str, Enum):
    """Types of email events that can be tracked."""
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    BOUNCED = "bounced"
    COMPLAINED = "complained"
    UNSUBSCRIBED = "unsubscribed"


class EmailEvent(BaseModel):
    """Model for tracking individual email events."""
    event_type: EmailEventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    details: Dict[str, Any] = Field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    location: Optional[Dict[str, Any]] = None


class EmailTracking(BaseModel):
    """Model for tracking email delivery and interactions."""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    message_id: str  # Unique identifier for the email
    user_id: PyObjectId  # Reference to the user
    recipient_email: str
    template_name: str
    subject: str
    sent_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    events: List[EmailEvent] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )
